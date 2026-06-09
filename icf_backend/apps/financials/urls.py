from django.urls import path

from .views import (
    CalculatorViewSet,
    FinancialGoalViewSet,
    FinancialProfileViewSet,
    OffTrackGoalListView,
)

urlpatterns = [
    # FM-15: Financial Profile — nested under /leads/{lead_pk}/
    path(
        "leads/<int:lead_pk>/financial-profile/",
        FinancialProfileViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="financial-profile",
    ),
    path(
        "leads/<int:lead_pk>/financial-profile/accounts/",
        FinancialProfileViewSet.as_view({"get": "list_accounts"}),
        name="financial-profile-accounts",
    ),
    path(
        "leads/<int:lead_pk>/financial-profile/accounts/add/",
        FinancialProfileViewSet.as_view({"post": "add_account"}),
        name="financial-profile-account-add",
    ),
    path(
        "leads/<int:lead_pk>/financial-profile/accounts/<int:account_pk>/",
        FinancialProfileViewSet.as_view({"delete": "remove_account"}),
        name="financial-profile-account-detail",
    ),
    path(
        "leads/<int:lead_pk>/financial-profile/insurance/",
        FinancialProfileViewSet.as_view({"get": "list_insurance"}),
        name="financial-profile-insurance",
    ),
    path(
        "leads/<int:lead_pk>/financial-profile/insurance/add/",
        FinancialProfileViewSet.as_view({"post": "add_insurance"}),
        name="financial-profile-insurance-add",
    ),
    path(
        "leads/<int:lead_pk>/financial-profile/insurance/<int:policy_pk>/",
        FinancialProfileViewSet.as_view({"delete": "remove_insurance"}),
        name="financial-profile-insurance-detail",
    ),

    # FM-16: Goals — nested under /leads/{lead_pk}/
    path(
        "leads/<int:lead_pk>/goals/",
        FinancialGoalViewSet.as_view({"get": "list", "post": "create"}),
        name="financial-goal-list",
    ),
    path(
        "leads/<int:lead_pk>/goals/<int:pk>/",
        FinancialGoalViewSet.as_view({
            "get": "retrieve",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="financial-goal-detail",
    ),
    path(
        "leads/<int:lead_pk>/goals/<int:pk>/milestones/",
        FinancialGoalViewSet.as_view({"get": "milestones", "post": "milestones"}),
        name="financial-goal-milestones",
    ),
    path(
        "leads/<int:lead_pk>/goals/<int:pk>/milestones/<int:milestone_pk>/achieve/",
        FinancialGoalViewSet.as_view({"post": "achieve_milestone"}),
        name="financial-goal-milestone-achieve",
    ),

    # Off-track goals list (advisor dashboard)
    path(
        "goals/off-track/",
        OffTrackGoalListView.as_view({"get": "list"}),
        name="financial-goals-off-track",
    ),

    # FM-21: Calculators
    path(
        "calculators/",
        CalculatorViewSet.as_view({"get": "list", "post": "create"}),
        name="calculator-list",
    ),
]
