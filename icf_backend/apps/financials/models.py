from decimal import Decimal
from django.conf import settings
from django.db import models
from apps.common.models import BaseModel, TenantBaseModel


# ---------------------------------------------------------------------------
# Financial Profile (FM-15)
# ---------------------------------------------------------------------------

class FinancialProfile(TenantBaseModel):
    """
    One-to-one with Lead. All monetary fields carry currency + as_of_date (BRU-26).
    Net worth is NEVER stored — always derived via the .net_worth property (BRU-27).
    Only meaningful when lead.status='client', but the FK is to Lead directly.
    """

    RISK_CONSERVATIVE = 'conservative'
    RISK_MODERATE = 'moderate'
    RISK_MOD_AGGRESSIVE = 'moderately_aggressive'
    RISK_AGGRESSIVE = 'aggressive'
    RISK_CHOICES = [
        (RISK_CONSERVATIVE, 'Conservative'),
        (RISK_MODERATE, 'Moderate'),
        (RISK_MOD_AGGRESSIVE, 'Moderately Aggressive'),
        (RISK_AGGRESSIVE, 'Aggressive'),
    ]

    lead = models.OneToOneField(
        'leads.Lead', on_delete=models.CASCADE, related_name='financial_profile'
    )

    # --- Income (BRU-26) ---
    annual_income = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    income_currency = models.CharField(max_length=3, default='USD')
    income_as_of = models.DateField(null=True, blank=True)

    # --- Expenses (BRU-26) ---
    annual_expenses = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    expenses_currency = models.CharField(max_length=3, default='USD')
    expenses_as_of = models.DateField(null=True, blank=True)

    # --- Assets aggregate (BRU-26) ---
    total_assets = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    assets_currency = models.CharField(max_length=3, default='USD')
    assets_as_of = models.DateField(null=True, blank=True)

    # --- Liabilities aggregate (BRU-26) ---
    total_liabilities = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    liabilities_currency = models.CharField(max_length=3, default='USD')
    liabilities_as_of = models.DateField(null=True, blank=True)

    # --- Risk profile ---
    risk_tolerance = models.CharField(max_length=30, choices=RISK_CHOICES, blank=True)

    @property
    def net_worth(self) -> Decimal:
        # BRU-27: derived = assets − liabilities. Never stored independently.
        return self.total_assets - self.total_liabilities

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'lead']),
        ]

    def __str__(self):
        return f"Financial Profile — {self.lead}"


class FinancialAccount(TenantBaseModel):
    """
    Individual account (brokerage, IRA, 401k, bank, real estate).
    Value + currency + as_of_date required (BRU-26).
    Source + source_timestamp required when externally ingested (BRU-40).
    """

    TYPE_BROKERAGE = 'brokerage'
    TYPE_IRA = 'ira'
    TYPE_401K = '401k'
    TYPE_BANK = 'bank'
    TYPE_REAL_ESTATE = 'real_estate'
    TYPE_RETIREMENT = 'retirement'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_BROKERAGE, 'Brokerage'),
        (TYPE_IRA, 'IRA'),
        (TYPE_401K, '401(k)'),
        (TYPE_BANK, 'Bank Account'),
        (TYPE_REAL_ESTATE, 'Real Estate'),
        (TYPE_RETIREMENT, 'Retirement'),
        (TYPE_OTHER, 'Other'),
    ]

    profile = models.ForeignKey(
        FinancialProfile, on_delete=models.CASCADE, related_name='accounts'
    )
    account_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    institution = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    value = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')       # BRU-26
    as_of_date = models.DateField()                                 # BRU-26
    source = models.CharField(max_length=200, blank=True)           # BRU-40
    source_timestamp = models.DateTimeField(null=True, blank=True)  # BRU-40

    class Meta:
        ordering = ['-as_of_date']
        indexes = [
            models.Index(fields=['profile', 'account_type']),
        ]

    def __str__(self):
        return f"{self.get_account_type_display()} — {self.institution or 'N/A'} ({self.currency} {self.value})"


class InsurancePolicy(TenantBaseModel):
    """FM-15: insurance policies linked to a financial profile."""

    TYPE_LIFE = 'life'
    TYPE_DISABILITY = 'disability'
    TYPE_LTC = 'long_term_care'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_LIFE, 'Life'),
        (TYPE_DISABILITY, 'Disability'),
        (TYPE_LTC, 'Long-Term Care'),
        (TYPE_OTHER, 'Other'),
    ]

    profile = models.ForeignKey(
        FinancialProfile, on_delete=models.CASCADE, related_name='insurance_policies'
    )
    policy_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    provider = models.CharField(max_length=200, blank=True)
    coverage_amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')   # BRU-26
    as_of_date = models.DateField()                             # BRU-26
    premium_annual = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['policy_type']

    def __str__(self):
        return f"{self.get_policy_type_display()} — {self.provider or 'N/A'}"


# ---------------------------------------------------------------------------
# Financial Goals (FM-16)
# ---------------------------------------------------------------------------

class FinancialGoal(TenantBaseModel):
    """
    BRU-29: progress_pct recomputed on linked financial change.
    BRU-26: target_amount carries currency.
    is_off_track raises advisor notification (FM-14).
    Linked to Lead (the single entity — not a separate Client model).
    """

    TYPE_RETIREMENT = 'retirement'
    TYPE_HOME_PURCHASE = 'home_purchase'
    TYPE_EDUCATION = 'education'
    TYPE_WEALTH = 'wealth_accumulation'
    TYPE_ESTATE = 'estate_planning'
    TYPE_RETURN = 'return_target'
    TYPE_CHOICES = [
        (TYPE_RETIREMENT, 'Retirement'),
        (TYPE_HOME_PURCHASE, 'Home Purchase'),
        (TYPE_EDUCATION, 'Education'),
        (TYPE_WEALTH, 'Wealth Accumulation'),
        (TYPE_ESTATE, 'Estate Planning'),
        (TYPE_RETURN, 'Return Target'),
    ]

    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE, related_name='goals'
    )
    goal_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200, blank=True)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    target_currency = models.CharField(max_length=3, default='USD')  # BRU-26
    target_date = models.DateField()
    current_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    is_off_track = models.BooleanField(default=False)           # BRU-29
    inputs_snapshot = models.JSONField(null=True, blank=True)   # BRU-39: reproducibility
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['target_date']
        indexes = [
            models.Index(fields=['tenant', 'lead', 'is_off_track']),
        ]

    def __str__(self):
        return f"{self.get_goal_type_display()} — {self.lead} (target: {self.target_currency} {self.target_amount})"


class GoalMilestone(BaseModel):
    """FM-16: milestones within a goal for progress tracking."""

    goal = models.ForeignKey(FinancialGoal, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    target_date = models.DateField()
    is_achieved = models.BooleanField(default=False)
    achieved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['target_date']

    def __str__(self):
        return f"{self.title} ({'achieved' if self.is_achieved else 'pending'})"


# ---------------------------------------------------------------------------
# Financial Calculators (FM-21)
# ---------------------------------------------------------------------------

class CalculatorResult(TenantBaseModel):
    """
    BRU-34: outputs are advisory estimates, not advice — labelled as such.
    BRU-39: inputs + as_of_date stored for reproducibility.
    """

    CALC_RETIREMENT = 'retirement'
    CALC_INVESTMENT_GROWTH = 'investment_growth'
    CALC_NET_WORTH = 'net_worth'
    CALC_LOAN = 'loan_amortization'
    CALC_COLLEGE = 'college_savings'
    CALC_INSURANCE = 'insurance_needs'
    CALC_RISK = 'risk_assessment'
    CALC_CHOICES = [
        (CALC_RETIREMENT, 'Retirement Calculator'),
        (CALC_INVESTMENT_GROWTH, 'Investment Growth'),
        (CALC_NET_WORTH, 'Net Worth'),
        (CALC_LOAN, 'Loan / Amortization'),
        (CALC_COLLEGE, 'College Savings'),
        (CALC_INSURANCE, 'Insurance Needs Analysis'),
        (CALC_RISK, 'Risk Assessment'),
    ]

    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE,
        null=True, blank=True, related_name='calculator_results',
    )
    run_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='calculator_results',
    )
    calculator_type = models.CharField(max_length=30, choices=CALC_CHOICES)
    inputs = models.JSONField()              # BRU-39: full input set stored
    outputs = models.JSONField()             # advisory estimate result
    as_of_date = models.DateField()         # BRU-39: when calculation was run
    ESTIMATE_DISCLAIMER = (
        "This is an advisory estimate only and does not constitute financial advice or a guarantee."
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'lead', 'calculator_type']),
        ]

    def __str__(self):
        return f"{self.get_calculator_type_display()} — {self.as_of_date}"
