from .base import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://macbook:1234@localhost:5433/icf_new_version_db')
}
