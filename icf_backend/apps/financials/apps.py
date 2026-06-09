from django.apps import AppConfig


class FinancialsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.financials'

    def ready(self):
        # Register event handlers for BRU-29 goal recompute on financial changes
        from apps.common.events import event_bus
        from apps.financials import event_handlers  # noqa: F401 — registers subscriptions
