from config.celery import app


@app.task
def send_mfa_setup_email(user_id):
    pass
