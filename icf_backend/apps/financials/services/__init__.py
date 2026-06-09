from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.common.edge_cases import assert_as_of_not_regressed, assert_currency_consistent
from apps.common.events import event_bus
from apps.financials.models import (
    CalculatorResult,
    FinancialAccount,
    FinancialGoal,
    FinancialProfile,
    GoalMilestone,
    InsurancePolicy,
)


class FinancialProfileService:

    @staticmethod
    @transaction.atomic
    def get_or_create_profile(*, tenant, lead, actor=None) -> FinancialProfile:
        profile, created = FinancialProfile.objects.get_or_create(
            tenant=tenant, lead=lead,
        )
        if created and actor:
            AuditService.log(
                actor=actor, tenant=tenant,
                action='financial_profile.created',
                entity_type='FinancialProfile', entity_id=profile.pk,
                after_state={'lead_id': lead.pk},
            )
        return profile

    @staticmethod
    @transaction.atomic
    def update_profile(*, profile, actor, **fields) -> FinancialProfile:
        allowed = {
            'annual_income', 'income_currency', 'income_as_of',
            'annual_expenses', 'expenses_currency', 'expenses_as_of',
            'risk_tolerance',
        }
        invalid = set(fields) - allowed
        if invalid:
            raise ValidationError(f"Non-updatable fields: {invalid}")

        # E-5 / BRU-26: prevent silent currency changes and backward as-of dates
        if 'income_currency' in fields:
            assert_currency_consistent(
                profile.income_currency, fields['income_currency'], 'annual_income',
            )
        if 'expenses_currency' in fields:
            assert_currency_consistent(
                profile.expenses_currency, fields['expenses_currency'], 'annual_expenses',
            )
        if 'income_as_of' in fields:
            assert_as_of_not_regressed(
                profile.income_as_of, fields['income_as_of'], 'annual_income',
            )
        if 'expenses_as_of' in fields:
            assert_as_of_not_regressed(
                profile.expenses_as_of, fields['expenses_as_of'], 'annual_expenses',
            )

        before = _profile_snapshot(profile)
        for field, value in fields.items():
            setattr(profile, field, value)
        profile.save()

        AuditService.log(
            actor=actor, tenant=profile.tenant,
            action='financial_profile.updated',
            entity_type='FinancialProfile', entity_id=profile.pk,
            before_state=before, after_state=_profile_snapshot(profile),
        )
        return profile

    @staticmethod
    @transaction.atomic
    def add_account(
        *, profile, actor, account_type, value, currency, as_of_date, **kwargs
    ) -> FinancialAccount:
        account = FinancialAccount.objects.create(
            tenant=profile.tenant, profile=profile,
            account_type=account_type, value=value,
            currency=currency, as_of_date=as_of_date,
            **kwargs,
        )
        _recompute_asset_totals(profile)
        AuditService.log(
            actor=actor, tenant=profile.tenant,
            action='financial_account.created',
            entity_type='FinancialAccount', entity_id=account.pk,
            after_state={
                'account_type': account_type,
                'value': str(value),
                'currency': currency,
            },
        )
        event_bus.emit(
            'financial_profile.changed',
            tenant_id=profile.tenant_id,
            profile_id=profile.pk,
            lead_id=profile.lead_id,
        )
        return account

    @staticmethod
    @transaction.atomic
    def update_account(*, account, actor, **fields) -> FinancialAccount:
        allowed = {
            'value', 'currency', 'as_of_date',
            'institution', 'account_name', 'source', 'source_timestamp',
        }
        invalid = set(fields) - allowed
        if invalid:
            raise ValidationError(f"Non-updatable fields: {invalid}")

        # E-5 / BRU-26: prevent silent currency change and backward as-of on individual accounts
        if 'currency' in fields:
            assert_currency_consistent(
                account.currency, fields['currency'], f'account {account.pk}',
            )
        if 'as_of_date' in fields:
            assert_as_of_not_regressed(
                account.as_of_date, fields['as_of_date'], f'account {account.pk}',
            )

        before = {
            'value': str(account.value),
            'currency': account.currency,
            'as_of_date': str(account.as_of_date),
        }
        for field, value in fields.items():
            setattr(account, field, value)
        account.save()
        _recompute_asset_totals(account.profile)

        AuditService.log(
            actor=actor, tenant=account.tenant,
            action='financial_account.updated',
            entity_type='FinancialAccount', entity_id=account.pk,
            before_state=before,
            after_state={'value': str(account.value), 'currency': account.currency},
        )
        event_bus.emit(
            'financial_profile.changed',
            tenant_id=account.tenant_id,
            profile_id=account.profile_id,
            lead_id=account.profile.lead_id,
        )
        return account

    @staticmethod
    @transaction.atomic
    def remove_account(*, account, actor) -> None:
        profile = account.profile
        AuditService.log(
            actor=actor, tenant=account.tenant,
            action='financial_account.deleted',
            entity_type='FinancialAccount', entity_id=account.pk,
            before_state={'value': str(account.value), 'currency': account.currency},
        )
        account.delete()
        _recompute_asset_totals(profile)
        event_bus.emit(
            'financial_profile.changed',
            tenant_id=profile.tenant_id,
            profile_id=profile.pk,
            lead_id=profile.lead_id,
        )

    @staticmethod
    @transaction.atomic
    def add_insurance(*, profile, actor, **kwargs) -> InsurancePolicy:
        policy = InsurancePolicy.objects.create(
            tenant=profile.tenant, profile=profile, **kwargs
        )
        AuditService.log(
            actor=actor, tenant=profile.tenant,
            action='insurance_policy.created',
            entity_type='InsurancePolicy', entity_id=policy.pk,
            after_state={'policy_type': policy.policy_type},
        )
        return policy

    @staticmethod
    @transaction.atomic
    def remove_insurance(*, policy, actor) -> None:
        AuditService.log(
            actor=actor, tenant=policy.tenant,
            action='insurance_policy.deleted',
            entity_type='InsurancePolicy', entity_id=policy.pk,
            before_state={'policy_type': policy.policy_type},
        )
        policy.delete()


class GoalService:

    @staticmethod
    @transaction.atomic
    def create_goal(
        *, tenant, lead, actor,
        goal_type, target_amount, target_currency,
        target_date, title='', notes='', inputs_snapshot=None,
    ) -> FinancialGoal:
        goal = FinancialGoal.objects.create(
            tenant=tenant, lead=lead,
            goal_type=goal_type, title=title,
            target_amount=target_amount, target_currency=target_currency,
            target_date=target_date, notes=notes,
            inputs_snapshot=inputs_snapshot,
        )
        AuditService.log(
            actor=actor, tenant=tenant,
            action='financial_goal.created',
            entity_type='FinancialGoal', entity_id=goal.pk,
            after_state={
                'goal_type': goal_type,
                'target_amount': str(target_amount),
                'target_currency': target_currency,
            },
        )
        return goal

    @staticmethod
    @transaction.atomic
    def update_goal(*, goal, actor, **fields) -> FinancialGoal:
        allowed = {
            'title', 'target_amount', 'target_currency',
            'target_date', 'current_value', 'notes', 'inputs_snapshot',
        }
        invalid = set(fields) - allowed
        if invalid:
            raise ValidationError(f"Non-updatable fields: {invalid}")

        before = _goal_snapshot(goal)
        for field, value in fields.items():
            setattr(goal, field, value)
        _recompute_goal_progress(goal)
        goal.save()

        AuditService.log(
            actor=actor, tenant=goal.tenant,
            action='financial_goal.updated',
            entity_type='FinancialGoal', entity_id=goal.pk,
            before_state=before, after_state=_goal_snapshot(goal),
        )
        return goal

    @staticmethod
    @transaction.atomic
    def delete_goal(*, goal, actor) -> None:
        AuditService.log(
            actor=actor, tenant=goal.tenant,
            action='financial_goal.deleted',
            entity_type='FinancialGoal', entity_id=goal.pk,
            before_state=_goal_snapshot(goal),
        )
        goal.delete()

    @staticmethod
    @transaction.atomic
    def add_milestone(
        *, goal, actor, title, target_amount, target_date
    ) -> GoalMilestone:
        milestone = GoalMilestone.objects.create(
            goal=goal, title=title,
            target_amount=target_amount, target_date=target_date,
        )
        AuditService.log(
            actor=actor, tenant=goal.tenant,
            action='goal_milestone.created',
            entity_type='GoalMilestone', entity_id=milestone.pk,
            after_state={'title': title, 'target_amount': str(target_amount)},
        )
        return milestone

    @staticmethod
    @transaction.atomic
    def mark_milestone_achieved(*, milestone, actor) -> GoalMilestone:
        milestone.is_achieved = True
        milestone.achieved_at = timezone.now()
        milestone.save()
        AuditService.log(
            actor=actor, tenant=milestone.goal.tenant,
            action='goal_milestone.achieved',
            entity_type='GoalMilestone', entity_id=milestone.pk,
            after_state={'achieved_at': str(milestone.achieved_at)},
        )
        return milestone

    @staticmethod
    @transaction.atomic
    def recompute_goal_progress(*, goal: FinancialGoal) -> FinancialGoal:
        """BRU-29: called by Celery task on financial_profile.changed event."""
        _recompute_goal_progress(goal)
        goal.save(update_fields=['progress_pct', 'is_off_track'])
        if goal.is_off_track:
            event_bus.emit(
                'goal.off_track',
                tenant_id=goal.tenant_id,
                goal_id=goal.pk,
                lead_id=goal.lead_id,
            )
        return goal


class CalculatorService:

    CALC_RETIREMENT = CalculatorResult.CALC_RETIREMENT
    CALC_INVESTMENT_GROWTH = CalculatorResult.CALC_INVESTMENT_GROWTH
    CALC_NET_WORTH = CalculatorResult.CALC_NET_WORTH
    CALC_LOAN = CalculatorResult.CALC_LOAN
    CALC_COLLEGE = CalculatorResult.CALC_COLLEGE
    CALC_INSURANCE = CalculatorResult.CALC_INSURANCE
    CALC_RISK = CalculatorResult.CALC_RISK

    @staticmethod
    @transaction.atomic
    def run(*, tenant, run_by, calculator_type, inputs, lead=None) -> CalculatorResult:
        """BRU-34: compute result, store inputs (BRU-39), return with disclaimer."""
        if calculator_type not in dict(CalculatorResult.CALC_CHOICES):
            raise ValidationError(f"Unknown calculator_type: {calculator_type}")

        engine = _CALCULATORS.get(calculator_type)
        if not engine:
            raise ValidationError(f"No engine for: {calculator_type}")

        outputs = engine(inputs)
        outputs['disclaimer'] = CalculatorResult.ESTIMATE_DISCLAIMER  # BRU-34

        result = CalculatorResult.objects.create(
            tenant=tenant, run_by=run_by, lead=lead,
            calculator_type=calculator_type,
            inputs=inputs, outputs=outputs,
            as_of_date=date.today(),
        )
        AuditService.log(
            actor=run_by, tenant=tenant,
            action='calculator.run',
            entity_type='CalculatorResult', entity_id=result.pk,
            after_state={'calculator_type': calculator_type},
        )
        return result


# ---------------------------------------------------------------------------
# Calculator engines (pure functions — no DB access)
# ---------------------------------------------------------------------------

def _calc_retirement(inputs: dict) -> dict:
    current_age = inputs.get('current_age', 30)
    retirement_age = inputs.get('retirement_age', 65)
    current_savings = Decimal(str(inputs.get('current_savings', 0)))
    annual_contribution = Decimal(str(inputs.get('annual_contribution', 0)))
    rate = Decimal(str(inputs.get('annual_return_pct', 6))) / 100
    years = retirement_age - current_age
    fv = current_savings * (1 + rate) ** years
    if rate > 0:
        fv += annual_contribution * (((1 + rate) ** years - 1) / rate)
    return {
        'projected_savings': str(round(fv, 2)),
        'years_to_retirement': years,
    }


def _calc_investment_growth(inputs: dict) -> dict:
    principal = Decimal(str(inputs.get('principal', 0)))
    annual_return = Decimal(str(inputs.get('annual_return_pct', 7))) / 100
    years = int(inputs.get('years', 10))
    fv = principal * (1 + annual_return) ** years
    return {'future_value': str(round(fv, 2)), 'years': years}


def _calc_net_worth(inputs: dict) -> dict:
    total_assets = Decimal(str(inputs.get('total_assets', 0)))
    total_liabilities = Decimal(str(inputs.get('total_liabilities', 0)))
    return {'net_worth': str(total_assets - total_liabilities)}


def _calc_loan(inputs: dict) -> dict:
    principal = Decimal(str(inputs.get('principal', 0)))
    annual_rate = Decimal(str(inputs.get('annual_rate_pct', 5))) / 100 / 12
    months = int(inputs.get('term_months', 360))
    if annual_rate == 0:
        monthly = principal / months if months else Decimal('0')
    else:
        monthly = principal * annual_rate / (1 - (1 + annual_rate) ** (-months))
    return {
        'monthly_payment': str(round(monthly, 2)),
        'total_paid': str(round(monthly * months, 2)),
        'total_interest': str(round(monthly * months - principal, 2)),
    }


def _calc_college(inputs: dict) -> dict:
    years_until_college = int(inputs.get('years_until_college', 10))
    annual_cost = Decimal(str(inputs.get('annual_cost', 30000)))
    inflation = Decimal(str(inputs.get('inflation_pct', 3))) / 100
    return_rate = Decimal(str(inputs.get('annual_return_pct', 6))) / 100
    years_in_college = int(inputs.get('years_in_college', 4))
    total_cost = sum(
        annual_cost * (1 + inflation) ** (years_until_college + i)
        for i in range(years_in_college)
    )
    required_savings = total_cost / (1 + return_rate) ** years_until_college
    return {
        'estimated_total_cost': str(round(total_cost, 2)),
        'required_savings_today': str(round(required_savings, 2)),
    }


def _calc_insurance_needs(inputs: dict) -> dict:
    annual_income = Decimal(str(inputs.get('annual_income', 0)))
    years_of_support = int(inputs.get('years_of_support', 10))
    existing_coverage = Decimal(str(inputs.get('existing_coverage', 0)))
    income_multiple = annual_income * years_of_support
    gap = max(income_multiple - existing_coverage, Decimal('0'))
    return {
        'recommended_coverage': str(round(income_multiple, 2)),
        'coverage_gap': str(round(gap, 2)),
    }


def _calc_risk_assessment(inputs: dict) -> dict:
    score = int(inputs.get('questionnaire_score', 0))
    max_score = int(inputs.get('max_score', 100))
    pct = (score / max_score * 100) if max_score else 0
    if pct >= 75:
        profile = 'aggressive'
    elif pct >= 50:
        profile = 'moderately_aggressive'
    elif pct >= 25:
        profile = 'moderate'
    else:
        profile = 'conservative'
    return {'risk_profile': profile, 'score_pct': round(pct, 1)}


_CALCULATORS = {
    CalculatorResult.CALC_RETIREMENT: _calc_retirement,
    CalculatorResult.CALC_INVESTMENT_GROWTH: _calc_investment_growth,
    CalculatorResult.CALC_NET_WORTH: _calc_net_worth,
    CalculatorResult.CALC_LOAN: _calc_loan,
    CalculatorResult.CALC_COLLEGE: _calc_college,
    CalculatorResult.CALC_INSURANCE: _calc_insurance_needs,
    CalculatorResult.CALC_RISK: _calc_risk_assessment,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _profile_snapshot(profile: FinancialProfile) -> dict:
    return {
        'annual_income': str(profile.annual_income or ''),
        'income_currency': profile.income_currency,
        'annual_expenses': str(profile.annual_expenses or ''),
        'risk_tolerance': profile.risk_tolerance,
    }


def _goal_snapshot(goal: FinancialGoal) -> dict:
    return {
        'target_amount': str(goal.target_amount),
        'target_currency': goal.target_currency,
        'current_value': str(goal.current_value),
        'progress_pct': str(goal.progress_pct),
        'is_off_track': goal.is_off_track,
    }


def _recompute_asset_totals(profile: FinancialProfile) -> None:
    from django.db.models import Sum
    total = profile.accounts.aggregate(total=Sum('value'))['total'] or Decimal('0')
    profile.total_assets = total
    profile.assets_as_of = date.today()
    profile.save(update_fields=['total_assets', 'assets_as_of'])


def _recompute_goal_progress(goal: FinancialGoal) -> None:
    if goal.target_amount and goal.target_amount > 0:
        pct = (goal.current_value / goal.target_amount) * 100
        goal.progress_pct = min(pct, Decimal('100'))
    else:
        goal.progress_pct = Decimal('0')
    # BRU-29: off-track when progress is below 80% of the time-proportional linear threshold
    today = date.today()
    created_date = goal.created_at.date() if goal.pk and goal.created_at else today
    total_days = (goal.target_date - created_date).days
    elapsed_days = (today - created_date).days

    if total_days <= 0:
        # Target date already passed — off-track unless fully achieved
        goal.is_off_track = goal.progress_pct < Decimal('100')
    elif elapsed_days > 0:
        expected_pct = Decimal(str(min(elapsed_days / total_days, 1))) * 100
        goal.is_off_track = goal.progress_pct < expected_pct * Decimal('0.8')
    else:
        goal.is_off_track = False
