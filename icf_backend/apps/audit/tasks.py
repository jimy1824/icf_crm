from config.celery import app


@app.task
def export_audit_log(tenant_id, from_date, to_date):
    # BRU-36: supervisor export of communication audit records
    pass
