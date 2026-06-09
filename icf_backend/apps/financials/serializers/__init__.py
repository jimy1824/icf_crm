from rest_framework import serializers

from apps.financials.models import (
    CalculatorResult,
    FinancialAccount,
    FinancialGoal,
    FinancialProfile,
    GoalMilestone,
    InsurancePolicy,
)


class FinancialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialAccount
        fields = [
            'id', 'account_type', 'institution', 'account_name',
            'value', 'currency', 'as_of_date',
            'source', 'source_timestamp',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FinancialAccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialAccount
        fields = [
            'account_type', 'institution', 'account_name',
            'value', 'currency', 'as_of_date',
            'source', 'source_timestamp',
        ]

    def validate_currency(self, value):
        if len(value) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter ISO code.")
        return value.upper()


class InsurancePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = InsurancePolicy
        fields = [
            'id', 'policy_type', 'provider',
            'coverage_amount', 'currency', 'as_of_date',
            'premium_annual', 'expires_on', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InsurancePolicyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsurancePolicy
        fields = [
            'policy_type', 'provider',
            'coverage_amount', 'currency', 'as_of_date',
            'premium_annual', 'expires_on', 'notes',
        ]

    def validate_currency(self, value):
        if len(value) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter ISO code.")
        return value.upper()


class FinancialProfileSerializer(serializers.ModelSerializer):
    net_worth = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    accounts = FinancialAccountSerializer(many=True, read_only=True)
    insurance_policies = InsurancePolicySerializer(many=True, read_only=True)

    class Meta:
        model = FinancialProfile
        fields = [
            'id',
            'annual_income', 'income_currency', 'income_as_of',
            'annual_expenses', 'expenses_currency', 'expenses_as_of',
            'total_assets', 'assets_currency', 'assets_as_of',
            'total_liabilities', 'liabilities_currency', 'liabilities_as_of',
            'net_worth',
            'risk_tolerance',
            'accounts', 'insurance_policies',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'net_worth', 'total_assets', 'assets_as_of',
            'total_liabilities', 'liabilities_as_of', 'updated_at',
        ]


class FinancialProfileUpdateSerializer(serializers.Serializer):
    annual_income = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    income_currency = serializers.CharField(max_length=3, required=False)
    income_as_of = serializers.DateField(required=False)
    annual_expenses = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    expenses_currency = serializers.CharField(max_length=3, required=False)
    expenses_as_of = serializers.DateField(required=False)
    risk_tolerance = serializers.ChoiceField(
        choices=FinancialProfile.RISK_CHOICES, required=False
    )


class GoalMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalMilestone
        fields = [
            'id', 'title', 'target_amount', 'target_date',
            'is_achieved', 'achieved_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_achieved', 'achieved_at', 'created_at', 'updated_at']


class GoalMilestoneCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalMilestone
        fields = ['title', 'target_amount', 'target_date']


class FinancialGoalSerializer(serializers.ModelSerializer):
    milestones = GoalMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = FinancialGoal
        fields = [
            'id', 'goal_type', 'title',
            'target_amount', 'target_currency', 'target_date',
            'current_value', 'progress_pct', 'is_off_track',
            'notes', 'inputs_snapshot', 'milestones',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'progress_pct', 'is_off_track',
            'created_at', 'updated_at',
        ]


class FinancialGoalCreateSerializer(serializers.Serializer):
    goal_type = serializers.ChoiceField(choices=FinancialGoal.TYPE_CHOICES)
    title = serializers.CharField(max_length=200, required=False, default='')
    target_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    target_currency = serializers.CharField(max_length=3, default='USD')
    target_date = serializers.DateField()
    notes = serializers.CharField(required=False, default='')
    inputs_snapshot = serializers.JSONField(required=False, default=None)

    def validate_target_currency(self, value):
        if len(value) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter ISO code.")
        return value.upper()


class FinancialGoalUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    target_amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    target_currency = serializers.CharField(max_length=3, required=False)
    target_date = serializers.DateField(required=False)
    current_value = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    notes = serializers.CharField(required=False)
    inputs_snapshot = serializers.JSONField(required=False)


class CalculatorRunSerializer(serializers.Serializer):
    """Input serializer for any calculator — validates the type and stores inputs (BRU-39)."""
    calculator_type = serializers.ChoiceField(choices=CalculatorResult.CALC_CHOICES)
    inputs = serializers.JSONField()
    client_id = serializers.IntegerField(required=False, default=None)


class CalculatorResultSerializer(serializers.ModelSerializer):
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = CalculatorResult
        fields = [
            'id', 'calculator_type', 'inputs', 'outputs',
            'as_of_date', 'disclaimer', 'created_at',
        ]
        read_only_fields = ['id', 'as_of_date', 'created_at']

    def get_disclaimer(self, obj) -> str:
        # BRU-34: disclaimer always present in serialized output
        return CalculatorResult.ESTIMATE_DISCLAIMER
