from config.celery import app


@app.task
def auto_assign_lead(lead_id):
    # BRU-06: assign at least one advisor per assignment rules
    pass


@app.task
def process_inbound_email(external_id, payload):
    # BRU-16: idempotent — guard on external_id before creating Lead
    pass
