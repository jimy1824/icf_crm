from apps.financials.models import (
    CalculatorResult,
    FinancialAccount,
    FinancialGoal,
    FinancialProfile,
    GoalMilestone,
    InsurancePolicy,
)


def get_financial_profile(*, tenant, lead) -> FinancialProfile | None:
    return FinancialProfile.objects.filter(tenant=tenant, lead=lead).first()


def get_accounts_for_profile(*, profile: FinancialProfile):
    return FinancialAccount.objects.filter(profile=profile).order_by('-as_of_date')


def get_insurance_for_profile(*, profile: FinancialProfile):
    return InsurancePolicy.objects.filter(profile=profile).order_by('policy_type')


def get_goals_for_lead(*, tenant, lead):
    return FinancialGoal.objects.filter(tenant=tenant, lead=lead).order_by('target_date')


def get_off_track_goals(*, tenant):
    return FinancialGoal.objects.filter(tenant=tenant, is_off_track=True).select_related('lead')


def get_milestones_for_goal(*, goal: FinancialGoal):
    return GoalMilestone.objects.filter(goal=goal).order_by('target_date')


def get_calculator_history(*, tenant, lead=None, calculator_type=None):
    qs = CalculatorResult.objects.filter(tenant=tenant)
    if lead:
        qs = qs.filter(lead=lead)
    if calculator_type:
        qs = qs.filter(calculator_type=calculator_type)
    return qs.order_by('-created_at')
