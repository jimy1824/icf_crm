"""
Event subscriptions for the financials app.
Imported by FinancialsConfig.ready() — do not import directly.
"""
from config.celery import app
from apps.common.events import event_bus


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='financials',
          name='financials.handle_profile_changed')
def handle_profile_changed(self, *, event_name, tenant_id, client_id, **kwargs):
    """BRU-29: recompute all goals when financial profile data changes."""
    try:
        from apps.financials.tasks import recompute_goals_for_client
        recompute_goals_for_client.delay(client_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='financials',
          name='financials.handle_goal_off_track')
def handle_goal_off_track(self, *, event_name, tenant_id, goal_id, **kwargs):
    """FM-14: dispatch off-track notification when a goal is flagged."""
    try:
        from apps.financials.tasks import send_off_track_goal_alert
        send_off_track_goal_alert.delay(goal_id)
    except Exception as exc:
        raise self.retry(exc=exc)


event_bus.subscribe('financial_profile.changed', handle_profile_changed)
event_bus.subscribe('goal.off_track', handle_goal_off_track)
