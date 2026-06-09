from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.leads.models import Lead
from apps.common.mixins import TenantScopedViewMixin
from apps.common.permissions import IsAdvisorOrAbove, IsComplianceOfficer, IsTenantMember
from apps.financials.models import (
    CalculatorResult,
    FinancialAccount,
    FinancialGoal,
    FinancialProfile,
    GoalMilestone,
    InsurancePolicy,
)
from apps.financials.selectors import (
    get_accounts_for_profile,
    get_calculator_history,
    get_financial_profile,
    get_goals_for_lead,
    get_insurance_for_profile,
    get_milestones_for_goal,
    get_off_track_goals,
)
from apps.financials.serializers import (
    CalculatorResultSerializer,
    CalculatorRunSerializer,
    FinancialAccountCreateSerializer,
    FinancialAccountSerializer,
    FinancialGoalCreateSerializer,
    FinancialGoalSerializer,
    FinancialGoalUpdateSerializer,
    FinancialProfileSerializer,
    FinancialProfileUpdateSerializer,
    GoalMilestoneCreateSerializer,
    GoalMilestoneSerializer,
    InsurancePolicyCreateSerializer,
    InsurancePolicySerializer,
)
from apps.financials.services import (
    CalculatorService,
    FinancialProfileService,
    GoalService,
)


class FinancialProfileViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """
    FM-15: financial profile per lead (lead IS the client entity).
    /leads/{lead_pk}/financial-profile/
    """
    permission_classes = [IsAdvisorOrAbove]

    def _get_lead(self, request, lead_pk):
        try:
            return Lead.objects.get(pk=lead_pk, tenant=request.tenant)
        except Lead.DoesNotExist:
            raise NotFound("Lead not found.")

    def retrieve(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        profile = get_financial_profile(tenant=request.tenant, lead=lead)
        if profile is None:
            return Response({'detail': 'No financial profile yet.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(FinancialProfileSerializer(profile).data)

    def partial_update(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        profile = FinancialProfileService.get_or_create_profile(
            tenant=request.tenant, lead=lead, actor=request.user
        )
        serializer = FinancialProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = FinancialProfileService.update_profile(
            profile=profile, actor=request.user, **serializer.validated_data
        )
        return Response(FinancialProfileSerializer(profile).data)

    # --- Accounts sub-resource ---

    @action(detail=False, methods=['get'], url_path='accounts')
    def list_accounts(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        profile = get_financial_profile(tenant=request.tenant, lead=lead)
        if profile is None:
            return Response([])
        qs = get_accounts_for_profile(profile=profile)
        return Response(FinancialAccountSerializer(qs, many=True).data)

    @action(detail=False, methods=['post'], url_path='accounts/add')
    def add_account(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        profile = FinancialProfileService.get_or_create_profile(
            tenant=request.tenant, lead=lead, actor=request.user
        )
        serializer = FinancialAccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = FinancialProfileService.add_account(
            profile=profile, actor=request.user, **serializer.validated_data
        )
        return Response(FinancialAccountSerializer(account).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='accounts/(?P<account_pk>[0-9]+)')
    def remove_account(self, request, lead_pk=None, account_pk=None):
        lead = self._get_lead(request, lead_pk)
        profile = get_financial_profile(tenant=request.tenant, lead=lead)
        if profile is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        account = FinancialAccount.objects.get(pk=account_pk, profile=profile)
        FinancialProfileService.remove_account(account=account, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- Insurance sub-resource ---

    @action(detail=False, methods=['get'], url_path='insurance')
    def list_insurance(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        profile = get_financial_profile(tenant=request.tenant, lead=lead)
        if profile is None:
            return Response([])
        qs = get_insurance_for_profile(profile=profile)
        return Response(InsurancePolicySerializer(qs, many=True).data)

    @action(detail=False, methods=['post'], url_path='insurance/add')
    def add_insurance(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        profile = FinancialProfileService.get_or_create_profile(
            tenant=request.tenant, lead=lead, actor=request.user
        )
        serializer = InsurancePolicyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = FinancialProfileService.add_insurance(
            profile=profile, actor=request.user, **serializer.validated_data
        )
        return Response(InsurancePolicySerializer(policy).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='insurance/(?P<policy_pk>[0-9]+)')
    def remove_insurance(self, request, lead_pk=None, policy_pk=None):
        lead = self._get_lead(request, lead_pk)
        profile = get_financial_profile(tenant=request.tenant, lead=lead)
        if profile is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        policy = InsurancePolicy.objects.get(pk=policy_pk, profile=profile)
        FinancialProfileService.remove_insurance(policy=policy, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FinancialGoalViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """
    FM-16: financial goals per lead (lead IS the client entity).
    /leads/{lead_pk}/goals/
    """
    permission_classes = [IsAdvisorOrAbove]

    def _get_lead(self, request, lead_pk):
        try:
            return Lead.objects.get(pk=lead_pk, tenant=request.tenant)
        except Lead.DoesNotExist:
            raise NotFound("Lead not found.")

    def _get_goal(self, request, lead_pk, goal_pk):
        lead = self._get_lead(request, lead_pk)
        return FinancialGoal.objects.get(
            pk=goal_pk, tenant=request.tenant, lead=lead
        )

    def list(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        qs = get_goals_for_lead(tenant=request.tenant, lead=lead)
        return Response(FinancialGoalSerializer(qs, many=True).data)

    def create(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        serializer = FinancialGoalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        goal = GoalService.create_goal(
            tenant=request.tenant, lead=lead,
            actor=request.user, **serializer.validated_data,
        )
        return Response(FinancialGoalSerializer(goal).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, lead_pk=None, pk=None):
        goal = self._get_goal(request, lead_pk, pk)
        return Response(FinancialGoalSerializer(goal).data)

    def partial_update(self, request, lead_pk=None, pk=None):
        goal = self._get_goal(request, lead_pk, pk)
        serializer = FinancialGoalUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        goal = GoalService.update_goal(
            goal=goal, actor=request.user, **serializer.validated_data
        )
        return Response(FinancialGoalSerializer(goal).data)

    def destroy(self, request, lead_pk=None, pk=None):
        goal = self._get_goal(request, lead_pk, pk)
        GoalService.delete_goal(goal=goal, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='milestones')
    def milestones(self, request, lead_pk=None, pk=None):
        goal = self._get_goal(request, lead_pk, pk)
        if request.method == 'GET':
            qs = get_milestones_for_goal(goal=goal)
            return Response(GoalMilestoneSerializer(qs, many=True).data)
        serializer = GoalMilestoneCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        milestone = GoalService.add_milestone(
            goal=goal, actor=request.user, **serializer.validated_data
        )
        return Response(GoalMilestoneSerializer(milestone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='milestones/(?P<milestone_pk>[0-9]+)/achieve')
    def achieve_milestone(self, request, lead_pk=None, pk=None, milestone_pk=None):
        goal = self._get_goal(request, lead_pk, pk)
        milestone = GoalMilestone.objects.get(pk=milestone_pk, goal=goal)
        milestone = GoalService.mark_milestone_achieved(milestone=milestone, actor=request.user)
        return Response(GoalMilestoneSerializer(milestone).data)


class OffTrackGoalListView(TenantScopedViewMixin, viewsets.ViewSet):
    """FM-16: list all off-track goals for the tenant."""
    permission_classes = [IsAdvisorOrAbove]

    def list(self, request):
        qs = get_off_track_goals(tenant=request.tenant)
        return Response(FinancialGoalSerializer(qs, many=True).data)


class CalculatorViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """
    FM-21: 7 financial calculators.
    BRU-34: disclaimer always in output.
    BRU-39: inputs stored with as_of_date.
    """
    permission_classes = [IsTenantMember]

    def create(self, request):
        """POST /calculators/ — run any calculator."""
        serializer = CalculatorRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lead = None
        if data.get('lead_id'):
            lead = Lead.objects.filter(tenant=request.tenant).get(pk=data['lead_id'])

        result = CalculatorService.run(
            tenant=request.tenant,
            run_by=request.user,
            calculator_type=data['calculator_type'],
            inputs=data['inputs'],
            lead=lead,
        )
        return Response(CalculatorResultSerializer(result).data, status=status.HTTP_201_CREATED)

    def list(self, request):
        calculator_type = request.query_params.get('type')
        lead_id = request.query_params.get('lead_id')
        lead = None
        if lead_id:
            lead = Lead.objects.filter(tenant=request.tenant).get(pk=lead_id)
        qs = get_calculator_history(
            tenant=request.tenant,
            lead=lead,
            calculator_type=calculator_type,
        )
        return Response(CalculatorResultSerializer(qs, many=True).data)
