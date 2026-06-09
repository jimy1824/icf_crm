import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.financials.models import (
    CalculatorResult,
    FinancialAccount,
    FinancialGoal,
    FinancialProfile,
    GoalMilestone,
    InsurancePolicy,
)
from apps.financials.services import (
    CalculatorService,
    FinancialProfileService,
    GoalService,
)
from apps.leads.models import Lead, KanbanCard
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Acme Advisors')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='advisor@acme.com', password='pass1234!',
        first_name='Jane', last_name='Advisor',
        role=CustomUser.ROLE_ADVISOR, tenant=tenant,
    )


@pytest.fixture
def lead_obj(tenant, advisor):
    return Lead.objects.create(
        tenant=tenant, first_name='Bob', last_name='Client',
        email='bob@test.com', source=Lead.SOURCE_MANUAL,
        pipeline_stage=Lead.STAGE_CLOSED_WON, status=Lead.STATUS_CLIENT,
    )


@pytest.fixture
def profile(tenant, lead_obj, advisor):
    return FinancialProfileService.get_or_create_profile(
        tenant=tenant, lead=lead_obj, actor=advisor
    )


@pytest.fixture
def goal(tenant, lead_obj, advisor):
    return GoalService.create_goal(
        tenant=tenant, lead=lead_obj, actor=advisor,
        goal_type=FinancialGoal.TYPE_RETIREMENT,
        target_amount=Decimal('1000000'),
        target_currency='USD',
        target_date=datetime.date(2050, 1, 1),
    )


# ---------------------------------------------------------------------------
# FinancialProfileService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFinancialProfileService:

    def test_get_or_create_profile_idempotent(self, tenant, lead_obj, advisor):
        """Calling twice returns the same profile (no duplicate)."""
        p1 = FinancialProfileService.get_or_create_profile(
            tenant=tenant, lead=lead_obj, actor=advisor
        )
        p2 = FinancialProfileService.get_or_create_profile(
            tenant=tenant, lead=lead_obj, actor=advisor
        )
        assert p1.pk == p2.pk
        assert FinancialProfile.objects.filter(tenant=tenant, lead=lead_obj).count() == 1

    def test_create_writes_audit(self, tenant, lead_obj, advisor):
        """BRU-33: creating a profile writes an audit entry."""
        from apps.audit.models import AuditEvent
        FinancialProfileService.get_or_create_profile(
            tenant=tenant, lead=lead_obj, actor=advisor
        )
        assert AuditEvent.objects.filter(
            action='financial_profile.created', entity_type='FinancialProfile'
        ).exists()

    def test_update_profile_income(self, profile, advisor):
        """update_profile writes income + currency + date."""
        updated = FinancialProfileService.update_profile(
            profile=profile, actor=advisor,
            annual_income=Decimal('120000'),
            income_currency='USD',
            income_as_of=datetime.date.today(),
        )
        assert updated.annual_income == Decimal('120000')
        assert updated.income_currency == 'USD'

    def test_update_profile_invalid_field_raises(self, profile, advisor):
        """Non-updatable fields must raise ValidationError."""
        with pytest.raises(ValidationError):
            FinancialProfileService.update_profile(
                profile=profile, actor=advisor,
                total_assets=Decimal('999'),  # not allowed via update
            )

    def test_add_account_recomputes_total_assets(self, profile, advisor):
        """BRU-27: adding an account recomputes total_assets on the profile."""
        FinancialProfileService.add_account(
            profile=profile, actor=advisor,
            account_type=FinancialAccount.TYPE_IRA,
            value=Decimal('200000'),
            currency='USD',
            as_of_date=datetime.date.today(),
        )
        profile.refresh_from_db()
        assert profile.total_assets == Decimal('200000')

    def test_add_second_account_accumulates(self, profile, advisor):
        FinancialProfileService.add_account(
            profile=profile, actor=advisor,
            account_type=FinancialAccount.TYPE_BROKERAGE,
            value=Decimal('100000'), currency='USD',
            as_of_date=datetime.date.today(),
        )
        FinancialProfileService.add_account(
            profile=profile, actor=advisor,
            account_type=FinancialAccount.TYPE_BANK,
            value=Decimal('50000'), currency='USD',
            as_of_date=datetime.date.today(),
        )
        profile.refresh_from_db()
        assert profile.total_assets == Decimal('150000')

    def test_remove_account_recomputes(self, profile, advisor):
        account = FinancialProfileService.add_account(
            profile=profile, actor=advisor,
            account_type=FinancialAccount.TYPE_IRA,
            value=Decimal('100000'), currency='USD',
            as_of_date=datetime.date.today(),
        )
        FinancialProfileService.remove_account(account=account, actor=advisor)
        profile.refresh_from_db()
        assert profile.total_assets == Decimal('0')

    def test_add_insurance_creates_policy(self, profile, advisor):
        policy = FinancialProfileService.add_insurance(
            profile=profile, actor=advisor,
            policy_type=InsurancePolicy.TYPE_LIFE,
            coverage_amount=Decimal('500000'),
            currency='USD',
            as_of_date=datetime.date.today(),
        )
        assert InsurancePolicy.objects.filter(profile=profile).count() == 1
        assert policy.policy_type == InsurancePolicy.TYPE_LIFE

    def test_net_worth_derived_never_stored(self, profile, advisor):
        """BRU-27: net_worth is a computed property, not a DB column."""
        FinancialProfileService.add_account(
            profile=profile, actor=advisor,
            account_type=FinancialAccount.TYPE_BROKERAGE,
            value=Decimal('300000'), currency='USD',
            as_of_date=datetime.date.today(),
        )
        profile.refresh_from_db()
        assert 'net_worth' not in [f.name for f in FinancialProfile._meta.get_fields()]
        assert profile.net_worth == profile.total_assets - profile.total_liabilities

    def test_bru_01_profile_scoped_to_tenant(self, advisor):
        """BRU-01: profiles from another tenant are not accessible via for_tenant."""
        t2 = Tenant.objects.create(firm_name='Other Firm')
        lead2 = Lead.objects.create(
            tenant=t2, first_name='X', last_name='Y',
            email='x@other.com', source=Lead.SOURCE_MANUAL,
            status=Lead.STATUS_CLIENT,
        )
        p2 = FinancialProfile.objects.create(tenant=t2, lead=lead2)
        qs = FinancialProfile.objects.for_tenant(advisor.tenant)
        assert p2 not in qs


# ---------------------------------------------------------------------------
# GoalService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGoalService:

    def test_create_goal(self, goal, tenant, lead_obj):
        assert goal.pk is not None
        assert goal.goal_type == FinancialGoal.TYPE_RETIREMENT
        assert FinancialGoal.objects.filter(tenant=tenant, lead=lead_obj).count() == 1

    def test_create_goal_writes_audit(self, tenant, lead_obj, advisor):
        from apps.audit.models import AuditEvent
        GoalService.create_goal(
            tenant=tenant, lead=lead_obj, actor=advisor,
            goal_type=FinancialGoal.TYPE_HOME_PURCHASE,
            target_amount=Decimal('400000'), target_currency='USD',
            target_date=datetime.date(2030, 1, 1),
        )
        assert AuditEvent.objects.filter(
            action='financial_goal.created', entity_type='FinancialGoal'
        ).exists()

    def test_update_goal(self, goal, advisor):
        GoalService.update_goal(
            goal=goal, actor=advisor, target_amount=Decimal('1500000')
        )
        goal.refresh_from_db()
        assert goal.target_amount == Decimal('1500000')

    def test_update_goal_invalid_field_raises(self, goal, advisor):
        with pytest.raises(ValidationError):
            GoalService.update_goal(goal=goal, actor=advisor, goal_type='retirement')

    def test_delete_goal(self, goal, advisor):
        goal_pk = goal.pk
        GoalService.delete_goal(goal=goal, actor=advisor)
        assert not FinancialGoal.objects.filter(pk=goal_pk).exists()

    def test_progress_recompute_on_update(self, goal, advisor):
        """BRU-29: progress_pct updates when current_value changes."""
        GoalService.update_goal(
            goal=goal, actor=advisor, current_value=Decimal('500000')
        )
        goal.refresh_from_db()
        assert goal.progress_pct == Decimal('50.00')

    def test_progress_capped_at_100(self, goal, advisor):
        GoalService.update_goal(
            goal=goal, actor=advisor, current_value=Decimal('2000000')
        )
        goal.refresh_from_db()
        assert goal.progress_pct == Decimal('100.00')

    def test_add_milestone(self, goal, advisor):
        milestone = GoalService.add_milestone(
            goal=goal, actor=advisor,
            title='Halfway',
            target_amount=Decimal('500000'),
            target_date=datetime.date(2035, 1, 1),
        )
        assert GoalMilestone.objects.filter(goal=goal).count() == 1
        assert milestone.is_achieved is False

    def test_mark_milestone_achieved(self, goal, advisor):
        milestone = GoalService.add_milestone(
            goal=goal, actor=advisor,
            title='Q1 target',
            target_amount=Decimal('100000'),
            target_date=datetime.date(2026, 6, 30),
        )
        milestone = GoalService.mark_milestone_achieved(milestone=milestone, actor=advisor)
        assert milestone.is_achieved is True
        assert milestone.achieved_at is not None

    def test_bru_29_off_track_detection(self, tenant, lead_obj, advisor):
        """BRU-29: a goal with zero progress on an overdue timeline is off-track."""
        past_target = datetime.date(2025, 1, 1)  # already passed
        goal = GoalService.create_goal(
            tenant=tenant, lead=lead_obj, actor=advisor,
            goal_type=FinancialGoal.TYPE_WEALTH,
            target_amount=Decimal('100000'), target_currency='USD',
            target_date=past_target,
        )
        GoalService.recompute_goal_progress(goal=goal)
        goal.refresh_from_db()
        # With 0 progress on a fully elapsed timeline, must be off-track
        assert goal.is_off_track is True


# ---------------------------------------------------------------------------
# CalculatorService (FM-21)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCalculatorService:

    def test_retirement_calculator(self, tenant, advisor):
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_RETIREMENT,
            inputs={
                'current_age': 35, 'retirement_age': 65,
                'current_savings': 50000, 'annual_contribution': 10000,
                'annual_return_pct': 7,
            },
        )
        assert result.pk is not None
        assert 'projected_savings' in result.outputs
        assert float(result.outputs['projected_savings']) > 0

    def test_investment_growth_calculator(self, tenant, advisor):
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_INVESTMENT_GROWTH,
            inputs={'principal': 10000, 'annual_return_pct': 8, 'years': 10},
        )
        assert 'future_value' in result.outputs
        assert float(result.outputs['future_value']) > 10000

    def test_loan_calculator(self, tenant, advisor):
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_LOAN,
            inputs={'principal': 300000, 'annual_rate_pct': 4.5, 'term_months': 360},
        )
        assert 'monthly_payment' in result.outputs
        assert float(result.outputs['monthly_payment']) > 0

    def test_college_savings_calculator(self, tenant, advisor):
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_COLLEGE,
            inputs={'years_until_college': 8, 'annual_cost': 40000, 'years_in_college': 4},
        )
        assert 'estimated_total_cost' in result.outputs

    def test_net_worth_calculator(self, tenant, advisor):
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_NET_WORTH,
            inputs={'total_assets': 500000, 'total_liabilities': 200000},
        )
        assert result.outputs['net_worth'] == '300000'

    def test_insurance_needs_calculator(self, tenant, advisor):
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_INSURANCE,
            inputs={'annual_income': 100000, 'years_of_support': 15, 'existing_coverage': 500000},
        )
        assert 'coverage_gap' in result.outputs

    def test_risk_assessment_calculator(self, tenant, advisor):
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_RISK,
            inputs={'questionnaire_score': 80, 'max_score': 100},
        )
        assert result.outputs['risk_profile'] == 'aggressive'

    def test_bru_34_disclaimer_in_output(self, tenant, advisor):
        """BRU-34: every calculator result must include the advisory disclaimer."""
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_NET_WORTH,
            inputs={'total_assets': 0, 'total_liabilities': 0},
        )
        assert 'disclaimer' in result.outputs
        assert 'estimate' in result.outputs['disclaimer'].lower()

    def test_bru_39_inputs_stored(self, tenant, advisor):
        """BRU-39: full input set must be persisted on the result."""
        inputs = {'principal': 100000, 'annual_return_pct': 6, 'years': 20}
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_INVESTMENT_GROWTH,
            inputs=inputs,
        )
        saved = CalculatorResult.objects.get(pk=result.pk)
        assert saved.inputs == inputs

    def test_bru_39_as_of_date_set(self, tenant, advisor):
        """BRU-39: as_of_date must be today's date."""
        from datetime import date
        result = CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_INVESTMENT_GROWTH,
            inputs={'principal': 1000, 'annual_return_pct': 5, 'years': 5},
        )
        assert result.as_of_date == date.today()

    def test_invalid_calculator_type_raises(self, tenant, advisor):
        with pytest.raises(ValidationError):
            CalculatorService.run(
                tenant=tenant, run_by=advisor,
                calculator_type='not_a_real_calculator',
                inputs={},
            )

    def test_bru_01_result_scoped_to_tenant(self, advisor):
        """BRU-01: calculator results scoped to their tenant."""
        t2 = Tenant.objects.create(firm_name='Other')
        advisor2 = CustomUser.objects.create_user(
            email='a2@other.com', password='pass1234!',
            first_name='A', last_name='B',
            role=CustomUser.ROLE_ADVISOR, tenant=t2,
        )
        CalculatorService.run(
            tenant=t2, run_by=advisor2,
            calculator_type=CalculatorResult.CALC_NET_WORTH,
            inputs={'total_assets': 0, 'total_liabilities': 0},
        )
        qs = CalculatorResult.objects.for_tenant(advisor.tenant)
        assert not qs.exists()
