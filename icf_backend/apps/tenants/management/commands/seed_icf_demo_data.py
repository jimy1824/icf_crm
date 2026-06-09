"""
Management command: seed_icf_demo_data

Populates the database with realistic, interconnected demo data covering:
  - 3 tenants (companies)
  - 3 subscription plans
  - 1 platform Super Admin
  - 3 tenant admins, 3 team leads, 9 advisors (3 per tenant)
  - 5 territories per tenant (15 total)
  - AdvisorTerritory assignments (each advisor → 1-2 territories)
  - 30 leads distributed across tenants / territories / advisors
  - 30 KanbanCards (auto-created with leads)
  - 5 campaigns per tenant (15 total) with 3 steps each
  - Campaign–territory M2M links
  - TenantTimeZone configs (office hours)
  - AdvisorTimeZone overrides
  - 3 billing records per tenant
  - 6 notifications (2 per tenant)
  - 1 TenantBranding per tenant
  - Client records for converted leads
  - FinancialProfiles for clients
  - FinancialGoals for clients
  - Communication records (outbound sent + inbound replies) for last 30 days
  - Meeting records (past + upcoming)
  - CampaignExecutionTimeline entries (today + next 7 days + past executions)

Safe to re-run: skips objects that already exist (idempotent).
Use --reset to wipe and recreate everything.

Usage:
    python manage.py seed_icf_demo_data
    python manage.py seed_icf_demo_data --reset
"""

import datetime
import logging

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as django_tz

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static seed data
# ---------------------------------------------------------------------------

PLANS = [
    {
        "name": "Starter",
        "max_leads": 200,
        "max_users": 5,
        "max_storage_gb": 10,
        "max_campaigns": 3,
        "features": {"email": True, "sms": False, "analytics": False},
    },
    {
        "name": "Professional",
        "max_leads": 1000,
        "max_users": 20,
        "max_storage_gb": 50,
        "max_campaigns": 15,
        "features": {"email": True, "sms": True, "analytics": True},
    },
    {
        "name": "Enterprise",
        "max_leads": 0,
        "max_users": 0,
        "max_storage_gb": 500,
        "max_campaigns": 0,
        "features": {"email": True, "sms": True, "analytics": True, "api_access": True, "white_label": True},
    },
]

TENANTS = [
    {
        "firm_name": "ICF Finance Houston",
        "legal_name": "ICF Finance Houston LLC",
        "company_email": "admin@icfhouston.com",
        "phone": "+1-713-555-0100",
        "website": "https://icfhouston.com",
        "logo_url": "https://placehold.co/200x80?text=ICF+Houston",
        "address_line1": "1001 Main St",
        "city": "Houston",
        "state": "TX",
        "country": "US",
        "postal_code": "77002",
        "region": "South",
        "timezone": "America/Chicago",
        "subdomain": "icf-houston",
        "plan_name": "Professional",
        "billing_cycle": "monthly",
        "branding": {"primary_color": "#1A56DB", "secondary_color": "#6B7280"},
    },
    {
        "firm_name": "ICF Wealth Advisors",
        "legal_name": "ICF Wealth Advisors Inc.",
        "company_email": "admin@icfwealth.com",
        "phone": "+1-212-555-0200",
        "website": "https://icfwealth.com",
        "logo_url": "https://placehold.co/200x80?text=ICF+Wealth",
        "address_line1": "425 Park Ave",
        "city": "New York",
        "state": "NY",
        "country": "US",
        "postal_code": "10022",
        "region": "Northeast",
        "timezone": "America/New_York",
        "subdomain": "icf-wealth",
        "plan_name": "Enterprise",
        "billing_cycle": "yearly",
        "branding": {"primary_color": "#0F4C81", "secondary_color": "#F4A261"},
    },
    {
        "firm_name": "ICF Global CRM Demo",
        "legal_name": "ICF Global CRM Demo Corp.",
        "company_email": "admin@icfdemo.com",
        "phone": "+1-415-555-0300",
        "website": "https://icfdemo.com",
        "logo_url": "https://placehold.co/200x80?text=ICF+Demo",
        "address_line1": "100 Market St",
        "city": "San Francisco",
        "state": "CA",
        "country": "US",
        "postal_code": "94105",
        "region": "West",
        "timezone": "America/Los_Angeles",
        "subdomain": "icf-demo",
        "plan_name": "Starter",
        "billing_cycle": "monthly",
        "branding": {"primary_color": "#7C3AED", "secondary_color": "#10B981"},
    },
]

# Territories: 5 per tenant
TERRITORIES = {
    "ICF Finance Houston": [
        {"name": "West Houston", "description": "West side of Houston metro"},
        {"name": "East Houston", "description": "East Houston industrial and residential"},
        {"name": "Houston Downtown", "description": "Central business district"},
        {"name": "The Woodlands", "description": "North suburbs — The Woodlands and Spring"},
        {"name": "Sugar Land", "description": "Southwest suburbs — Sugar Land, Missouri City"},
    ],
    "ICF Wealth Advisors": [
        {"name": "Manhattan Midtown", "description": "Midtown Manhattan high-net-worth clients"},
        {"name": "Manhattan Downtown", "description": "Financial district and Lower Manhattan"},
        {"name": "Brooklyn Heights", "description": "Brooklyn residential wealth corridor"},
        {"name": "Long Island", "description": "Nassau and Suffolk county clients"},
        {"name": "New Jersey Metro", "description": "NJ commuter belt — Bergen, Essex counties"},
    ],
    "ICF Global CRM Demo": [
        {"name": "San Francisco Core", "description": "SoMa, FiDi, Nob Hill"},
        {"name": "Silicon Valley North", "description": "San Jose, Sunnyvale, Cupertino"},
        {"name": "East Bay", "description": "Oakland, Berkeley, Walnut Creek"},
        {"name": "Marin County", "description": "Marin County affluent territory"},
        {"name": "Peninsula", "description": "Palo Alto, Menlo Park, Burlingame"},
    ],
}

# Users: list of (role, first, last, email_prefix, tz_override)
# 1 tenant_admin, 1 team_lead, 3 advisors per tenant
USERS = {
    "ICF Finance Houston": [
        ("tenant_admin", "Sarah", "Mitchell", "sarah.mitchell", None),
        ("team_lead", "James", "Patterson", "james.patterson", "America/Chicago"),
        ("advisor", "Maria", "Torres", "maria.torres", "America/Chicago"),
        ("advisor", "Kevin", "Nguyen", "kevin.nguyen", "America/Chicago"),
        ("advisor", "Rachel", "Kim", "rachel.kim", "America/Denver"),
    ],
    "ICF Wealth Advisors": [
        ("tenant_admin", "David", "Chen", "david.chen", None),
        ("team_lead", "Jennifer", "Walsh", "jennifer.walsh", "America/New_York"),
        ("advisor", "Marcus", "Johnson", "marcus.johnson", "America/New_York"),
        ("advisor", "Priya", "Sharma", "priya.sharma", "America/New_York"),
        ("advisor", "Thomas", "O'Brien", "thomas.obrien", "America/Chicago"),
    ],
    "ICF Global CRM Demo": [
        ("tenant_admin", "Lisa", "Zhang", "lisa.zhang", None),
        ("team_lead", "Michael", "Rodriguez", "michael.rodriguez", "America/Los_Angeles"),
        ("advisor", "Emily", "Patel", "emily.patel", "America/Los_Angeles"),
        ("advisor", "Carlos", "Mendez", "carlos.mendez", "America/Los_Angeles"),
        ("advisor", "Aisha", "Williams", "aisha.williams", "America/Phoenix"),
    ],
}

# Campaigns: 5 per tenant
CAMPAIGNS_TEMPLATE = [
    {
        "name": "New Lead Welcome Series",
        "status": "active",
        "steps": [
            {"step_number": 1, "channel": "email", "delay_value": 0, "delay_unit": "hours",
             "subject": "Welcome — we'd love to help you reach your financial goals",
             "content_template": "Hi {{first_name}},\n\nThank you for your interest in {{firm_name}}. We specialise in helping clients like you build lasting financial security.\n\nOur team is ready to schedule a complimentary 30-minute consultation at your convenience.\n\nWarm regards,\n{{advisor_name}}"},
            {"step_number": 2, "channel": "sms", "delay_value": 1, "delay_unit": "days",
             "subject": "",
             "content_template": "Hi {{first_name}}, this is {{advisor_name}} from {{firm_name}}. Did you receive my email? Reply YES to schedule a call. Reply STOP to opt out."},
            {"step_number": 3, "channel": "email", "delay_value": 4, "delay_unit": "days",
             "subject": "3 financial planning mistakes most people make (and how to avoid them)",
             "content_template": "Hi {{first_name}},\n\nI wanted to share a quick insight that's helped many of our clients:\n\n1. Underestimating retirement income needs\n2. Over-concentration in a single asset class\n3. No written financial plan\n\nLet's talk about where you stand. Reply to this email or call us directly.\n\n{{advisor_name}}\n{{firm_name}}"},
        ],
    },
    {
        "name": "High-Net-Worth Prospecting",
        "status": "active",
        "steps": [
            {"step_number": 1, "channel": "email", "delay_value": 2, "delay_unit": "hours",
             "subject": "Exclusive invitation: Private wealth review",
             "content_template": "Dear {{first_name}},\n\nYou've been identified as someone who may benefit from our private wealth management services. Our advisors serve clients with investable assets of $500,000+.\n\nI'd welcome a brief conversation.\n\n{{advisor_name}}, CFP\n{{firm_name}}"},
            {"step_number": 2, "channel": "email", "delay_value": 5, "delay_unit": "days",
             "subject": "Following up — portfolio review opportunity",
             "content_template": "Hi {{first_name}},\n\nI sent you a note last week about our private wealth review programme. I wanted to follow up personally.\n\nWould Thursday at 10am or Friday at 2pm work for a 20-minute call?\n\n{{advisor_name}}"},
            {"step_number": 3, "channel": "sms", "delay_value": 8, "delay_unit": "days",
             "subject": "",
             "content_template": "Hi {{first_name}}, {{advisor_name}} here from {{firm_name}}. Still available for that portfolio conversation? Text back a good time. Reply STOP to opt out."},
        ],
    },
    {
        "name": "Retirement Planning Nurture",
        "status": "active",
        "steps": [
            {"step_number": 1, "channel": "email", "delay_value": 1, "delay_unit": "hours",
             "subject": "Are you on track for retirement? Find out in 5 minutes.",
             "content_template": "Hi {{first_name}},\n\nWith retirement ages shifting and market uncertainty, many professionals are unsure if they're on track.\n\nWe offer a complimentary Retirement Readiness Review — a no-obligation, 30-minute session where we'll assess your current trajectory.\n\nReply YES and I'll send you a calendar link.\n\n{{advisor_name}}\n{{firm_name}}"},
            {"step_number": 2, "channel": "sms", "delay_value": 3, "delay_unit": "days",
             "subject": "",
             "content_template": "Hi {{first_name}}, it's {{advisor_name}}. Wanted to check — did you get a chance to read my email about your retirement plan? Reply YES for more info. STOP to opt out."},
            {"step_number": 3, "channel": "email", "delay_value": 7, "delay_unit": "days",
             "subject": "5 questions to ask your financial advisor about retirement",
             "content_template": "Hi {{first_name}},\n\nHere are 5 questions every pre-retiree should ask:\n\n1. What's my projected income replacement rate?\n2. How is my portfolio positioned for sequence-of-returns risk?\n3. Have we planned for healthcare costs?\n4. What's our strategy for Social Security timing?\n5. Do I have an estate plan?\n\nLet's walk through these together — reply to schedule.\n\n{{advisor_name}}"},
        ],
    },
    {
        "name": "Re-engagement 60-Day",
        "status": "active",
        "steps": [
            {"step_number": 1, "channel": "email", "delay_value": 0, "delay_unit": "hours",
             "subject": "We miss you — what changed?",
             "content_template": "Hi {{first_name}},\n\nIt's been a while since we connected. Financial circumstances evolve, and I wanted to reach out personally to see how things are going.\n\nIs there anything I can help with? Reply to this email — I read every response.\n\n{{advisor_name}}\n{{firm_name}}"},
            {"step_number": 2, "channel": "sms", "delay_value": 4, "delay_unit": "days",
             "subject": "",
             "content_template": "Hi {{first_name}}, {{advisor_name}} from {{firm_name}}. Just a quick check-in. Anything I can help you with financially? Reply STOP to opt out."},
            {"step_number": 3, "channel": "email", "delay_value": 14, "delay_unit": "days",
             "subject": "Last chance to claim your complimentary review",
             "content_template": "Hi {{first_name}},\n\nI don't want to take up more of your time, but I did want to extend one final offer: a complimentary Financial Health Check, no strings attached.\n\nIf now isn't the right time, no worries at all — I'll close the loop here.\n\nAll the best,\n{{advisor_name}}"},
        ],
    },
    {
        "name": "Post-Conversion Onboarding",
        "status": "active",
        "steps": [
            {"step_number": 1, "channel": "email", "delay_value": 0, "delay_unit": "hours",
             "subject": "Welcome aboard — next steps for your financial plan",
             "content_template": "Hi {{first_name}},\n\nWelcome to {{firm_name}}! We're thrilled to have you as a client.\n\nHere's what happens next:\n\n1. You'll receive our onboarding questionnaire within 24 hours\n2. We'll schedule your first planning session within the week\n3. You'll get access to our client portal\n\nAny questions, reply here.\n\n{{advisor_name}}"},
            {"step_number": 2, "channel": "email", "delay_value": 2, "delay_unit": "days",
             "subject": "Your onboarding checklist",
             "content_template": "Hi {{first_name}},\n\nQuick reminder — please complete the onboarding questionnaire so we can personalise your financial plan.\n\nIt takes about 10 minutes and covers:\n- Current income and expenses\n- Existing investments\n- Short and long-term goals\n\nLink: https://portal.{{subdomain}}.icf.com/onboarding\n\n{{advisor_name}}"},
            {"step_number": 3, "channel": "sms", "delay_value": 5, "delay_unit": "days",
             "subject": "",
             "content_template": "Hi {{first_name}}, {{advisor_name}} here. Don't forget to complete your onboarding form so we can build your plan! Link sent to your email. Reply STOP to opt out."},
        ],
    },
]

# 10 leads per tenant (30 total)
LEADS_DATA = {
    "ICF Finance Houston": [
        ("Robert", "Hawkins", "robert.hawkins@example.com", "+1-713-555-1001", "web_form", "new", "new_leads", "West Houston", "America/Chicago"),
        ("Angela", "Morrison", "angela.morrison@example.com", "+1-713-555-1002", "manual", "contacted", "contacted", "East Houston", "America/Chicago"),
        ("Derek", "Sullivan", "derek.sullivan@example.com", "+1-832-555-1003", "api_import", "qualified", "qualified", "Houston Downtown", "America/Chicago"),
        ("Carmen", "Reyes", "carmen.reyes@example.com", "+1-713-555-1004", "web_form", "new", "new_leads", "The Woodlands", "America/Chicago"),
        ("Patrick", "O'Connor", "patrick.oconnor@example.com", "+1-281-555-1005", "manual", "contacted", "in_discussion", "Sugar Land", "America/Chicago"),
        ("Stephanie", "Nguyen", "stephanie.nguyen@example.com", "+1-713-555-1006", "email_trigger", "new", "new_leads", "West Houston", "America/Chicago"),
        ("Brian", "Wallace", "brian.wallace@example.com", "+1-832-555-1007", "web_form", "qualified", "proposal_sent", "East Houston", "America/Chicago"),
        ("Michelle", "Park", "michelle.park@example.com", "+1-713-555-1008", "manual", "client", "closed_won", "Houston Downtown", "America/Chicago"),
        ("Jason", "Brooks", "jason.brooks@example.com", "+1-281-555-1009", "api_import", "new", "new_leads", "The Woodlands", "America/Chicago"),
        ("Amanda", "Fleming", "amanda.fleming@example.com", "+1-713-555-1010", "web_form", "contacted", "contacted", "Sugar Land", "America/Chicago"),
    ],
    "ICF Wealth Advisors": [
        ("William", "Harrington", "william.harrington@example.com", "+1-212-555-2001", "web_form", "qualified", "in_discussion", "Manhattan Midtown", "America/New_York"),
        ("Sophie", "Laurent", "sophie.laurent@example.com", "+1-212-555-2002", "manual", "new", "new_leads", "Manhattan Downtown", "America/New_York"),
        ("Elliot", "Greenfield", "elliot.greenfield@example.com", "+1-718-555-2003", "api_import", "contacted", "contacted", "Brooklyn Heights", "America/New_York"),
        ("Diana", "Forsythe", "diana.forsythe@example.com", "+1-516-555-2004", "web_form", "qualified", "proposal_sent", "Long Island", "America/New_York"),
        ("Nathan", "Brodsky", "nathan.brodsky@example.com", "+1-201-555-2005", "email_trigger", "new", "new_leads", "New Jersey Metro", "America/New_York"),
        ("Olivia", "Steinberg", "olivia.steinberg@example.com", "+1-212-555-2006", "manual", "client", "closed_won", "Manhattan Midtown", "America/New_York"),
        ("Harrison", "Cole", "harrison.cole@example.com", "+1-212-555-2007", "web_form", "contacted", "in_discussion", "Manhattan Downtown", "America/New_York"),
        ("Natalie", "Russo", "natalie.russo@example.com", "+1-718-555-2008", "api_import", "new", "new_leads", "Brooklyn Heights", "America/New_York"),
        ("Scott", "McKenna", "scott.mckenna@example.com", "+1-516-555-2009", "manual", "qualified", "qualified", "Long Island", "America/New_York"),
        ("Grace", "Yamamoto", "grace.yamamoto@example.com", "+1-201-555-2010", "web_form", "new", "new_leads", "New Jersey Metro", "America/New_York"),
    ],
    "ICF Global CRM Demo": [
        ("Tyler", "Bradford", "tyler.bradford@example.com", "+1-415-555-3001", "web_form", "new", "new_leads", "San Francisco Core", "America/Los_Angeles"),
        ("Samantha", "Ortega", "samantha.ortega@example.com", "+1-408-555-3002", "manual", "contacted", "contacted", "Silicon Valley North", "America/Los_Angeles"),
        ("Daniel", "Okonkwo", "daniel.okonkwo@example.com", "+1-510-555-3003", "api_import", "qualified", "in_discussion", "East Bay", "America/Los_Angeles"),
        ("Hannah", "McAllister", "hannah.mcallister@example.com", "+1-415-555-3004", "web_form", "new", "new_leads", "Marin County", "America/Los_Angeles"),
        ("Lucas", "Brennan", "lucas.brennan@example.com", "+1-650-555-3005", "email_trigger", "contacted", "proposal_sent", "Peninsula", "America/Los_Angeles"),
        ("Zoe", "Fitzgerald", "zoe.fitzgerald@example.com", "+1-415-555-3006", "manual", "new", "new_leads", "San Francisco Core", "America/Los_Angeles"),
        ("Aaron", "Nakamura", "aaron.nakamura@example.com", "+1-408-555-3007", "web_form", "qualified", "qualified", "Silicon Valley North", "America/Los_Angeles"),
        ("Isabella", "Cruz", "isabella.cruz@example.com", "+1-510-555-3008", "api_import", "client", "closed_won", "East Bay", "America/Los_Angeles"),
        ("Ethan", "Weston", "ethan.weston@example.com", "+1-415-555-3009", "manual", "new", "new_leads", "Marin County", "America/Los_Angeles"),
        ("Chloe", "Adeyemi", "chloe.adeyemi@example.com", "+1-650-555-3010", "web_form", "contacted", "contacted", "Peninsula", "America/Los_Angeles"),
    ],
}


class Command(BaseCommand):
    help = "Seed the database with realistic demo data for ICF CRM."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing seed data before re-creating it.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()
        with transaction.atomic():
            self._seed()
        self.stdout.write(self.style.SUCCESS("✓ ICF demo data seeded successfully."))

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def _reset(self):
        from apps.tenants.models import Tenant
        from apps.campaigns.models import CampaignEnrollment
        from apps.users.models import CustomUser

        seed_firms = [t["firm_name"] for t in TENANTS]
        seed_tenants = Tenant.objects.filter(firm_name__in=seed_firms)

        # Delete in dependency order to avoid protected FK errors:
        # 1. Enrollments (check constraint references lead)
        CampaignEnrollment.objects.filter(tenant__in=seed_tenants).delete()
        # 2. Now cascade-delete the tenants (leads, comms, timelines, etc.)
        count, _ = seed_tenants.delete()
        self.stdout.write(f"  Deleted {count} existing seed tenant records (cascade).")
        CustomUser.objects.filter(email="superadmin@icf-platform.com").delete()

    # ------------------------------------------------------------------
    # Main seed
    # ------------------------------------------------------------------

    def _seed(self):
        plans = self._seed_plans()
        self._seed_super_admin()
        for t_data in TENANTS:
            self._seed_tenant(t_data, plans)

    # ------------------------------------------------------------------
    # Plans
    # ------------------------------------------------------------------

    def _seed_plans(self):
        from apps.tenants.models import SubscriptionPlan
        plans = {}
        for p in PLANS:
            obj, created = SubscriptionPlan.objects.get_or_create(
                name=p["name"],
                defaults={
                    "max_leads": p["max_leads"],
                    "max_users": p["max_users"],
                    "max_storage_gb": p["max_storage_gb"],
                    "max_campaigns": p["max_campaigns"],
                    "features": p["features"],
                },
            )
            plans[p["name"]] = obj
            self.stdout.write(f"  {'Created' if created else 'Found'} plan: {obj.name}")
        return plans

    # ------------------------------------------------------------------
    # Platform super admin
    # ------------------------------------------------------------------

    def _seed_super_admin(self):
        from apps.users.models import CustomUser
        obj, created = CustomUser.objects.get_or_create(
            email="superadmin@icf-platform.com",
            defaults={
                "first_name": "Platform",
                "last_name": "Admin",
                "role": CustomUser.ROLE_SUPER_ADMIN,
                "user_type": CustomUser.TYPE_PLATFORM_STAFF,
                "is_staff": True,
                "is_superuser": True,
                "password": make_password("Admin1234!"),
                "tenant": None,
            },
        )
        if created:
            self.stdout.write("  Created platform super admin: superadmin@icf-platform.com / Admin1234!")

    # ------------------------------------------------------------------
    # One full tenant
    # ------------------------------------------------------------------

    def _seed_tenant(self, t_data, plans):
        tenant = self._create_tenant(t_data, plans)
        territories = self._create_territories(tenant, t_data["firm_name"])
        users = self._create_users(tenant, t_data["firm_name"])
        self._assign_advisor_territories(users["advisors"] + [users["team_lead"]], territories, tenant)
        self._create_timezone_config(tenant, t_data["timezone"], users["advisors"])
        campaigns = self._create_campaigns(tenant, territories, users["team_lead"])
        leads = self._create_leads(tenant, t_data["firm_name"], territories, users["advisors"], campaigns)
        clients = self._create_clients(tenant, leads)
        self._create_financial_profiles(tenant, clients)
        self._create_financial_goals(tenant, clients)
        self._create_communications(tenant, leads, users["advisors"] + [users["team_lead"]])
        self._create_meetings(tenant, leads, clients, users["advisors"])
        self._create_timeline_entries(tenant, leads, campaigns)
        self._create_billing(tenant)
        self._create_notifications(tenant, users["advisors"])
        self._create_branding(tenant, t_data.get("branding", {}))

    # ------------------------------------------------------------------
    # Tenant + subscription
    # ------------------------------------------------------------------

    def _create_tenant(self, t_data, plans):
        from apps.tenants.models import Tenant, TenantSubscription
        tenant, created = Tenant.objects.get_or_create(
            firm_name=t_data["firm_name"],
            defaults={
                "legal_name": t_data["legal_name"],
                "company_email": t_data["company_email"],
                "phone": t_data["phone"],
                "website": t_data["website"],
                "logo_url": t_data["logo_url"],
                "address_line1": t_data["address_line1"],
                "city": t_data["city"],
                "state": t_data["state"],
                "country": t_data["country"],
                "postal_code": t_data["postal_code"],
                "region": t_data["region"],
                "timezone": t_data["timezone"],
                "subdomain": t_data["subdomain"],
                "status": "active",
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Found'} tenant: {tenant.firm_name}")

        plan = plans[t_data["plan_name"]]
        today = datetime.date.today()
        TenantSubscription.objects.get_or_create(
            tenant=tenant,
            defaults={
                "plan": plan,
                "status": "active",
                "billing_cycle": t_data["billing_cycle"],
                "starts_at": today,
                "ends_at": today + datetime.timedelta(days=365),
            },
        )
        return tenant

    # ------------------------------------------------------------------
    # Territories
    # ------------------------------------------------------------------

    def _create_territories(self, tenant, firm_name):
        from apps.territories.models import Territory
        territories = []
        for t in TERRITORIES[firm_name]:
            obj, _ = Territory.objects.get_or_create(
                tenant=tenant,
                name=t["name"],
                defaults={"description": t["description"]},
            )
            territories.append(obj)
        self.stdout.write(f"  Created {len(territories)} territories for {tenant.firm_name}")
        return territories

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def _create_users(self, tenant, firm_name):
        from apps.users.models import CustomUser
        domain = tenant.company_email.split("@")[1]
        users_cfg = USERS[firm_name]

        tenant_admin = None
        team_lead = None
        advisors = []

        for role, first, last, email_prefix, _ in users_cfg:
            email = f"{email_prefix}@{domain}"
            obj, created = CustomUser.objects.get_or_create(
                email=email,
                tenant=tenant,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "password": make_password("Advisor1234!"),
                    "is_active": True,
                },
            )
            if role == "tenant_admin":
                tenant_admin = obj
            elif role == "team_lead":
                team_lead = obj
            else:
                advisors.append(obj)

        self.stdout.write(f"  Created users for {tenant.firm_name}: 1 admin, 1 team lead, {len(advisors)} advisors")
        return {"admin": tenant_admin, "team_lead": team_lead, "advisors": advisors}

    # ------------------------------------------------------------------
    # AdvisorTerritory assignments
    # ------------------------------------------------------------------

    def _assign_advisor_territories(self, advisors, territories, tenant):
        from apps.territories.models import AdvisorTerritory
        # Round-robin: advisor[i] gets territories[i] and territories[(i+1)%len]
        n = len(territories)
        for i, advisor in enumerate(advisors):
            primary = territories[i % n]
            secondary = territories[(i + 1) % n]
            for terr in [primary, secondary]:
                AdvisorTerritory.objects.get_or_create(
                    advisor=advisor,
                    territory=terr,
                    defaults={"assigned_by": None},
                )

    # ------------------------------------------------------------------
    # Timezone config
    # ------------------------------------------------------------------

    def _create_timezone_config(self, tenant, tenant_tz, advisors):
        from apps.timezones.models import TenantTimeZone, AdvisorTimeZone
        TenantTimeZone.objects.get_or_create(
            tenant=tenant,
            defaults={
                "timezone": tenant_tz,
                "office_start": datetime.time(8, 0),
                "office_end": datetime.time(18, 0),
                "working_days": [0, 1, 2, 3, 4],  # Mon–Fri
            },
        )
        users_cfg = USERS[tenant.firm_name]
        for (role, first, last, email_prefix, tz_override) in users_cfg:
            if tz_override and role == "advisor":
                domain = tenant.company_email.split("@")[1]
                from apps.users.models import CustomUser
                try:
                    advisor = CustomUser.objects.get(email=f"{email_prefix}@{domain}", tenant=tenant)
                    AdvisorTimeZone.objects.get_or_create(
                        advisor=advisor,
                        defaults={"timezone": tz_override},
                    )
                except CustomUser.DoesNotExist:
                    pass

    # ------------------------------------------------------------------
    # Campaigns + steps
    # ------------------------------------------------------------------

    def _create_campaigns(self, tenant, territories, created_by):
        from apps.campaigns.models import Campaign, CampaignStep
        campaigns = []
        for i, c_data in enumerate(CAMPAIGNS_TEMPLATE):
            campaign, created = Campaign.objects.get_or_create(
                tenant=tenant,
                name=c_data["name"],
                defaults={
                    "status": c_data["status"],
                    "created_by": created_by,
                },
            )
            # Assign 2 territories per campaign (rotating)
            n = len(territories)
            terr_a = territories[i % n]
            terr_b = territories[(i + 2) % n]
            campaign.territories.add(terr_a, terr_b)

            # Create steps
            for s in c_data["steps"]:
                CampaignStep.objects.get_or_create(
                    campaign=campaign,
                    step_number=s["step_number"],
                    defaults={
                        "channel": s["channel"],
                        "subject": s["subject"],
                        "content_template": s["content_template"],
                        "delay_value": s["delay_value"],
                        "delay_unit": s["delay_unit"],
                        "delay_days": s["delay_value"] if s["delay_unit"] == "days" else 0,
                    },
                )
            campaigns.append(campaign)

        self.stdout.write(f"  Created {len(campaigns)} campaigns for {tenant.firm_name}")
        return campaigns

    # ------------------------------------------------------------------
    # Leads
    # ------------------------------------------------------------------

    def _create_leads(self, tenant, firm_name, territories, advisors, campaigns):
        from apps.leads.models import Lead, KanbanCard
        from apps.campaigns.models import CampaignEnrollment

        leads_data = LEADS_DATA[firm_name]
        territory_map = {t.name: t for t in territories}
        advisor_cycle = 0
        created_count = 0
        all_leads = []
        today = datetime.date.today()

        for i, (first, last, email, phone, source, status, stage,
                territory_name, preferred_tz) in enumerate(leads_data):

            territory = territory_map.get(territory_name)
            lead, created = Lead.objects.get_or_create(
                tenant=tenant,
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "phone": phone,
                    "source": source,
                    "status": status,
                    "pipeline_stage": stage,
                    "territory": territory,
                    "preferred_timezone": preferred_tz,
                },
            )
            all_leads.append(lead)

            if created:
                created_count += 1

                # Assign primary advisor (round-robin)
                if advisors:
                    primary = advisors[advisor_cycle % len(advisors)]
                    lead.assigned_advisors.add(primary)
                    # Assign a second advisor to every 3rd lead (multi-advisor scenario)
                    if i % 3 == 0 and len(advisors) > 1:
                        secondary = advisors[(advisor_cycle + 1) % len(advisors)]
                        lead.assigned_advisors.add(secondary)
                    advisor_cycle += 1

                # Create KanbanCard
                KanbanCard.objects.get_or_create(
                    lead=lead,
                    defaults={"stage": stage, "position": created_count},
                )

                # Enroll active leads — distribute across campaigns for variety
                if status in ("new", "contacted", "qualified") and campaigns:
                    campaign = campaigns[i % len(campaigns)]
                    CampaignEnrollment.objects.get_or_create(
                        tenant=tenant,
                        campaign=campaign,
                        lead=lead,
                        defaults={"status": "active", "current_step": 0},
                    )

        # ── Today's leads: back-date the first 5 leads to today ──────────────
        # The existing leads already have created_at = now (auto_now_add).
        # Ensure 5 of them are stamped to today so the dashboard widget shows data.
        today_leads = all_leads[:5]
        for lead in today_leads:
            Lead.objects.filter(pk=lead.pk).update(
                created_at=django_tz.now().replace(hour=9, minute=0, second=0, microsecond=0),
            )
        # Back-date the rest to earlier days so the chart has spread
        for offset, lead in enumerate(all_leads[5:], start=1):
            days_back = (offset % 29) + 1
            Lead.objects.filter(pk=lead.pk).update(
                created_at=django_tz.now() - datetime.timedelta(days=days_back),
            )

        self.stdout.write(f"  Created {created_count} leads for {tenant.firm_name}")
        return all_leads

    # ------------------------------------------------------------------
    # Client leads (status='client' — no separate Client model)
    # ------------------------------------------------------------------

    def _create_clients(self, tenant, leads):
        # Lead IS the client entity. Return leads that are in client stage.
        clients = [lead for lead in leads if lead.status == 'client']
        self.stdout.write(f"  Found {len(clients)} client-stage leads for {tenant.firm_name}")
        return clients

    # ------------------------------------------------------------------
    # Financial Profiles (BRU-26/27)
    # ------------------------------------------------------------------

    def _create_financial_profiles(self, tenant, clients):
        from apps.financials.models import FinancialProfile
        today = datetime.date.today()
        profiles_data = [
            {
                "annual_income": "185000.00", "income_currency": "USD", "income_as_of": today,
                "annual_expenses": "72000.00", "expenses_currency": "USD", "expenses_as_of": today,
                "total_assets": "750000.00", "assets_currency": "USD", "assets_as_of": today,
                "total_liabilities": "120000.00", "liabilities_currency": "USD", "liabilities_as_of": today,
                "risk_tolerance": "moderate",
            },
            {
                "annual_income": "240000.00", "income_currency": "USD", "income_as_of": today,
                "annual_expenses": "95000.00", "expenses_currency": "USD", "expenses_as_of": today,
                "total_assets": "1250000.00", "assets_currency": "USD", "assets_as_of": today,
                "total_liabilities": "200000.00", "liabilities_currency": "USD", "liabilities_as_of": today,
                "risk_tolerance": "moderately_aggressive",
            },
            {
                "annual_income": "320000.00", "income_currency": "USD", "income_as_of": today,
                "annual_expenses": "110000.00", "expenses_currency": "USD", "expenses_as_of": today,
                "total_assets": "2100000.00", "assets_currency": "USD", "assets_as_of": today,
                "total_liabilities": "350000.00", "liabilities_currency": "USD", "liabilities_as_of": today,
                "risk_tolerance": "aggressive",
            },
        ]
        for i, lead in enumerate(clients):
            data = profiles_data[i % len(profiles_data)]
            FinancialProfile.objects.get_or_create(
                tenant=tenant, lead=lead,
                defaults=data,
            )
        self.stdout.write(f"  Created financial profiles for {len(clients)} client leads")

    # ------------------------------------------------------------------
    # Financial Goals (BRU-29)
    # ------------------------------------------------------------------

    def _create_financial_goals(self, tenant, clients):
        from apps.financials.models import FinancialGoal
        today = datetime.date.today()
        goals_templates = [
            {
                "goal_type": "retirement",
                "title": "Retirement at 65",
                "target_amount": "2000000.00",
                "target_currency": "USD",
                "target_date": today.replace(year=today.year + 15),
                "current_value": "750000.00",
                "progress_pct": "37.50",
                "is_off_track": False,
            },
            {
                "goal_type": "education",
                "title": "College Fund",
                "target_amount": "180000.00",
                "target_currency": "USD",
                "target_date": today.replace(year=today.year + 8),
                "current_value": "45000.00",
                "progress_pct": "25.00",
                "is_off_track": False,
            },
            {
                "goal_type": "wealth_accumulation",
                "title": "Investment Portfolio Growth",
                "target_amount": "500000.00",
                "target_currency": "USD",
                "target_date": today.replace(year=today.year + 5),
                "current_value": "85000.00",
                "progress_pct": "17.00",
                "is_off_track": True,
            },
        ]
        for lead in clients:
            for tpl in goals_templates:
                FinancialGoal.objects.get_or_create(
                    tenant=tenant,
                    lead=lead,
                    goal_type=tpl["goal_type"],
                    title=tpl["title"],
                    defaults={k: v for k, v in tpl.items() if k not in ("goal_type", "title")},
                )
        self.stdout.write(f"  Created financial goals for {len(clients)} client leads")

    # ------------------------------------------------------------------
    # Communications (outbound + inbound replies) — last 30 days
    # ------------------------------------------------------------------

    def _create_communications(self, tenant, leads, advisors):
        from apps.communications.models import Communication
        # created_at is auto_now_add — we back-date via update() after creation.

        now = django_tz.now()
        created_count = 0
        to_backdate = []  # list of (pk, datetime)

        for i, lead in enumerate(leads):
            advisor = advisors[i % len(advisors)] if advisors else None
            base_days_ago = (i % 30) + 1
            backdate_out = now - datetime.timedelta(days=base_days_ago)
            backdate_reply = now - datetime.timedelta(days=max(base_days_ago - 2, 0), hours=3)

            # Outbound email
            ext_id_out = f"seed-out-{tenant.pk}-{lead.pk}-email"
            obj, created = Communication.objects.get_or_create(
                external_id=ext_id_out,
                defaults={
                    "tenant": tenant,
                    "lead": lead,
                    "sent_by": advisor,
                    "channel": "email",
                    "direction": "outbound",
                    "status": "delivered",
                    "subject": f"Hello {lead.first_name}, following up on your inquiry",
                    "is_reply": False,
                },
            )
            if created:
                created_count += 1
                to_backdate.append((obj.pk, backdate_out))

            # Outbound SMS
            ext_id_sms = f"seed-out-{tenant.pk}-{lead.pk}-sms"
            obj, created = Communication.objects.get_or_create(
                external_id=ext_id_sms,
                defaults={
                    "tenant": tenant,
                    "lead": lead,
                    "sent_by": advisor,
                    "channel": "sms",
                    "direction": "outbound",
                    "status": "delivered",
                    "subject": f"Hi {lead.first_name}, quick follow-up from {tenant.firm_name}.",
                    "is_reply": False,
                },
            )
            if created:
                created_count += 1
                to_backdate.append((obj.pk, backdate_out - datetime.timedelta(days=1)))

            # Inbound reply (every other lead)
            if i % 2 == 0:
                ext_id_reply = f"seed-reply-{tenant.pk}-{lead.pk}"
                obj, created = Communication.objects.get_or_create(
                    external_id=ext_id_reply,
                    defaults={
                        "tenant": tenant,
                        "lead": lead,
                        "sent_by": advisor,
                        "channel": "email",
                        "direction": "inbound",
                        "status": "received",
                        "subject": f"Re: Hello {lead.first_name} — Yes, I'm interested",
                        "is_reply": True,
                    },
                )
                if created:
                    created_count += 1
                    to_backdate.append((obj.pk, backdate_reply))

            # Today's inbound reply for first 3 leads (Today's Responses widget)
            if i < 3:
                ext_id_today = f"seed-today-reply-{tenant.pk}-{lead.pk}"
                obj, created = Communication.objects.get_or_create(
                    external_id=ext_id_today,
                    defaults={
                        "tenant": tenant,
                        "lead": lead,
                        "sent_by": advisor,
                        "channel": "email",
                        "direction": "inbound",
                        "status": "received",
                        "subject": f"Re: {lead.first_name} — Interested in a consultation",
                        "is_reply": True,
                    },
                )
                if created:
                    created_count += 1
                    # Keep today's date — no back-dating needed for today's widget

        # Back-date created_at in bulk via raw update (bypasses auto_now_add)
        for pk, ts in to_backdate:
            Communication.objects.filter(pk=pk).update(created_at=ts)

        self.stdout.write(f"  Created {created_count} communication records for {tenant.firm_name}")

    # ------------------------------------------------------------------
    # Meetings (past + upcoming)
    # ------------------------------------------------------------------

    def _create_meetings(self, tenant, leads, clients, advisors):
        from apps.communications.models import Meeting
        now = django_tz.now()
        created_count = 0

        for i, lead in enumerate(leads[:6]):
            advisor = advisors[i % len(advisors)] if advisors else None

            # Past meeting (outcome recorded)
            Meeting.objects.get_or_create(
                tenant=tenant,
                lead=lead,
                scheduled_at=now - datetime.timedelta(days=(i + 1) * 3),
                defaults={
                    "advisor": advisor,
                    "outcome": "Discussed financial goals and next steps",
                    "outcome_recorded_at": now - datetime.timedelta(days=(i + 1) * 3 - 1),
                    "notes": f"Initial consultation with {lead.first_name} {lead.last_name}.",
                    "recipient_timezone": lead.preferred_timezone or "America/Chicago",
                },
            )
            created_count += 1

        for i, lead in enumerate(leads[:4]):
            advisor = advisors[i % len(advisors)] if advisors else None

            # Upcoming meeting (for upcoming_meetings widget)
            Meeting.objects.get_or_create(
                tenant=tenant,
                lead=lead,
                scheduled_at=now + datetime.timedelta(days=(i + 1) * 2),
                defaults={
                    "advisor": advisor,
                    "notes": f"Follow-up with {lead.first_name}.",
                    "recipient_timezone": lead.preferred_timezone or "America/Chicago",
                },
            )
            created_count += 1

        self.stdout.write(f"  Created {created_count} meetings for {tenant.firm_name}")

    # ------------------------------------------------------------------
    # CampaignExecutionTimeline entries
    # ------------------------------------------------------------------

    def _create_timeline_entries(self, tenant, leads, campaigns):
        from apps.campaigns.models import CampaignEnrollment, CampaignStep
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        now = django_tz.now()
        today_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        created_count = 0

        # Find all active enrollments — take up to 15 for variety
        enrollments = list(
            CampaignEnrollment.objects.filter(
                tenant=tenant,
                status='active',
            ).select_related('campaign', 'lead')[:15]
        )

        for i, enrollment in enumerate(enrollments):
            steps = list(CampaignStep.objects.filter(campaign=enrollment.campaign).order_by('step_number'))
            if not steps:
                continue

            first_step = steps[0]

            # Every enrollment gets a today-scheduled pending entry
            _, created = CampaignExecutionTimeline.objects.get_or_create(
                tenant=tenant,
                enrollment=enrollment,
                campaign_step=first_step,
                defaults={
                    "campaign": enrollment.campaign,
                    "lead": enrollment.lead,
                    "step_order": first_step.step_number,
                    "step_type": first_step.channel,
                    "subject_snapshot": first_step.subject or '',
                    "body_snapshot": first_step.content_template[:500],
                    "scheduled_at": today_start + datetime.timedelta(minutes=i * 45),
                    "status": CampaignExecutionTimeline.STATUS_PENDING,
                },
            )
            if created:
                created_count += 1

            # Past executed entry for step 2 (if exists)
            if len(steps) >= 2:
                second_step = steps[1]
                executed_at = now - datetime.timedelta(days=2, hours=i % 6)
                _, created = CampaignExecutionTimeline.objects.get_or_create(
                    tenant=tenant,
                    enrollment=enrollment,
                    campaign_step=second_step,
                    defaults={
                        "campaign": enrollment.campaign,
                        "lead": enrollment.lead,
                        "step_order": second_step.step_number,
                        "step_type": second_step.channel,
                        "subject_snapshot": second_step.subject or '',
                        "body_snapshot": second_step.content_template[:500],
                        "scheduled_at": executed_at,
                        "executed_at": executed_at,
                        "status": CampaignExecutionTimeline.STATUS_EXECUTED,
                    },
                )
                if created:
                    created_count += 1

            # Step 3 entry — some scheduled tomorrow, some failed
            if len(steps) >= 3:
                third_step = steps[2]
                sched_at = today_start + datetime.timedelta(days=1, hours=i % 4)
                st = CampaignExecutionTimeline.STATUS_SCHEDULED if i % 4 != 3 else CampaignExecutionTimeline.STATUS_FAILED
                _, created = CampaignExecutionTimeline.objects.get_or_create(
                    tenant=tenant,
                    enrollment=enrollment,
                    campaign_step=third_step,
                    defaults={
                        "campaign": enrollment.campaign,
                        "lead": enrollment.lead,
                        "step_order": third_step.step_number,
                        "step_type": third_step.channel,
                        "subject_snapshot": third_step.subject or '',
                        "body_snapshot": third_step.content_template[:500],
                        "scheduled_at": sched_at,
                        "status": st,
                        "failure_reason": "Mailbox rate limit" if st == CampaignExecutionTimeline.STATUS_FAILED else '',
                    },
                )
                if created:
                    created_count += 1

        self.stdout.write(f"  Created {created_count} timeline entries for {tenant.firm_name}")

    # ------------------------------------------------------------------
    # Billing records
    # ------------------------------------------------------------------

    def _create_billing(self, tenant):
        from apps.tenants.models import BillingRecord
        today = datetime.date.today()
        records = [
            {
                "record_type": "invoice",
                "status": "paid",
                "amount_cents": 49900,
                "currency": "USD",
                "period_start": today - datetime.timedelta(days=60),
                "period_end": today - datetime.timedelta(days=31),
                "invoice_number": f"INV-{tenant.pk:04d}-001",
                "external_invoice_id": f"ext-{tenant.pk}-001",
                "payment_method": "card",
                "transaction_id": f"txn_{tenant.pk}_001",
                "paid_at": django_tz.now() - datetime.timedelta(days=55),
                "notes": "Monthly subscription — Professional",
            },
            {
                "record_type": "invoice",
                "status": "paid",
                "amount_cents": 49900,
                "currency": "USD",
                "period_start": today - datetime.timedelta(days=30),
                "period_end": today,
                "invoice_number": f"INV-{tenant.pk:04d}-002",
                "external_invoice_id": f"ext-{tenant.pk}-002",
                "payment_method": "card",
                "transaction_id": f"txn_{tenant.pk}_002",
                "paid_at": django_tz.now() - datetime.timedelta(days=25),
                "notes": "Monthly subscription — Professional",
            },
            {
                "record_type": "invoice",
                "status": "pending",
                "amount_cents": 49900,
                "currency": "USD",
                "period_start": today + datetime.timedelta(days=1),
                "period_end": today + datetime.timedelta(days=30),
                "invoice_number": f"INV-{tenant.pk:04d}-003",
                "external_invoice_id": f"ext-{tenant.pk}-003",
                "notes": "Upcoming renewal",
            },
        ]
        for r in records:
            BillingRecord.objects.get_or_create(
                tenant=tenant,
                external_invoice_id=r["external_invoice_id"],
                defaults=r,
            )

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _create_notifications(self, tenant, advisors):
        from apps.notifications.models import Notification
        if not advisors:
            return
        events = [
            {
                "recipient": advisors[0],
                "event_type": "lead.assigned",
                "entity_type": "Lead",
                "entity_id": "1",
                "channels": ["in_app", "email"],
                "is_read": False,
            },
            {
                "recipient": advisors[-1],
                "event_type": "campaign.step_executed",
                "entity_type": "CampaignExecutionTimeline",
                "entity_id": "1",
                "channels": ["in_app"],
                "is_read": True,
            },
        ]
        for ev in events:
            Notification.objects.get_or_create(
                tenant=tenant,
                recipient=ev["recipient"],
                event_type=ev["event_type"],
                entity_type=ev["entity_type"],
                entity_id=ev["entity_id"],
                defaults={
                    "channels": ev["channels"],
                    "is_read": ev["is_read"],
                },
            )

    # ------------------------------------------------------------------
    # Branding
    # ------------------------------------------------------------------

    def _create_branding(self, tenant, branding_data):
        from apps.tenants.models import TenantBranding
        TenantBranding.objects.get_or_create(
            tenant=tenant,
            defaults={
                "primary_color": branding_data.get("primary_color", "#1A56DB"),
                "secondary_color": branding_data.get("secondary_color", "#6B7280"),
                "login_bg_url": "",
                "custom_smtp_host": "",
                "custom_smtp_port": 587,
                "custom_smtp_user": "",
                "custom_sms_provider": "",
            },
        )
