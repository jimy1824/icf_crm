from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.campaigns'

    def ready(self):
        from apps.campaigns import event_handlers  # noqa: F401 — registers subscriptions
