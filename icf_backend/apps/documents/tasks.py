from config.celery import app


@app.task
def purge_expired_documents():
    # BRU-37: run on schedule; skip documents under legal hold (BRU-38)
    import datetime
    from apps.documents.models import Document
    today = datetime.date.today()
    Document.objects.filter(
        retain_until__lt=today,
        is_under_legal_hold=False,
    ).delete()
