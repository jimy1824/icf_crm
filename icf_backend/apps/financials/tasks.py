from config.celery import app


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='financials')
def recompute_goals_for_lead(self, lead_id: int) -> None:
    """BRU-29: triggered by financial_profile.changed event. lead IS the client entity."""
    try:
        from apps.leads.models import Lead
        from apps.financials.services import GoalService
        lead = Lead.objects.get(pk=lead_id)
        for goal in lead.goals.all():
            GoalService.recompute_goal_progress(goal=goal)
    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='financials')
def send_off_track_goal_alert(self, goal_id: int) -> None:
    """FM-14: advisor notification when a goal goes off-track."""
    try:
        from apps.financials.models import FinancialGoal
        goal = FinancialGoal.objects.select_related('lead', 'tenant').get(pk=goal_id)
        if not goal.is_off_track:
            return
        from apps.common.events import event_bus
        event_bus.emit(
            'notification.send',
            tenant_id=goal.tenant_id,
            notification_type='goal_off_track',
            goal_id=goal_id,
            lead_id=goal.lead_id,
        )
    except Exception as exc:
        raise self.retry(exc=exc)
