from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env', overwrite=False)

SECRET_KEY = env('SECRET_KEY', default='change-me-in-production')

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
]

PROJECT_APPS = [
    'apps.common',
    'apps.tenants',
    'apps.users',
    'apps.employees',
    'apps.leads',
    'apps.financials',
    'apps.campaigns',
    'apps.communications',
    'apps.documents',
    'apps.audit',
    'apps.notifications',
    'apps.search',
    'apps.analytics',
    'apps.support',
    'apps.compliance',
    'apps.territories',
    'apps.timezones',
    'apps.campaign_timeline',
    'apps.portal',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://postgres:postgres@localhost:5432/icf_crm')
}

AUTH_USER_MODEL = 'users.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Queue definitions — docs/22, BRU-16 (idempotent), NFR-PERF-3 (tenant fairness)
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = {
    'default': {},           # general tasks
    'leads': {},             # lead distribution, territory auto-assignment
    'campaigns': {},         # campaign scheduler / executor
    'communications': {},    # outbound email / SMS / calls
    'notifications': {},     # in-app + email notifications
    'financials': {},        # net-worth / goal recompute
    'audit': {},             # audit persistence & retention
    'integrations': {},      # OAuth token lifecycle, mailbox sync, calendar sync
    'search': {},            # search indexing
    'billing': {},           # billing / dunning
}

CELERY_TASK_ROUTES = {
    'apps.territories.tasks.*': {'queue': 'leads'},
    'apps.campaigns.tasks.*': {'queue': 'campaigns'},
    'apps.campaign_timeline.tasks.*': {'queue': 'campaigns'},
    'apps.communications.tasks.*': {'queue': 'communications'},
    'apps.notifications.tasks.*': {'queue': 'notifications'},
    'apps.financials.tasks.*': {'queue': 'financials'},
    'apps.audit.tasks.*': {'queue': 'audit'},
    'apps.tenants.tasks.*': {'queue': 'billing'},
}

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    'poll-due-timeline-entries': {
        'task': 'apps.campaign_timeline.tasks.poll_due_timeline_entries',
        'schedule': 60.0,  # every 60 seconds
    },
    'run-dunning-sweep': {
        'task': 'apps.tenants.tasks.run_dunning_sweep',
        'schedule': crontab(hour=1, minute=0),  # 01:00 UTC daily
    },
    'generate-subscription-renewals': {
        'task': 'apps.tenants.tasks.generate_subscription_renewals',
        'schedule': crontab(hour=0, minute=5),  # 00:05 UTC daily
    },
    'poll-trial-expirations': {
        'task': 'apps.tenants.tasks.poll_trial_expirations',
        'schedule': crontab(hour=0, minute=15),  # 00:15 UTC daily
    },
}

# Retry defaults for all tasks — docs/22 BRU-16
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# email uniqueness is enforced per-tenant via UniqueConstraint, not a global unique=True.
SILENCED_SYSTEM_CHECKS = ['auth.E003']
