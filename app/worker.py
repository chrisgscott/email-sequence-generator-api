from celery import Celery
from app.core.config import settings
from celery.schedules import crontab

print(f"REDIS_URL: {settings.REDIS_URL}")

celery_app = Celery('email_sequence_generator',
                    broker=settings.REDIS_URL,
                    backend=settings.REDIS_URL)

celery_app.conf.task_routes = {
    'app.tasks.*': {'queue': 'email_tasks'}
}

celery_app.conf.beat_schedule = {
    'send-scheduled-emails': {
        'task': 'app.tasks.send_scheduled_emails',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    },
}

celery_app.conf.update(task_track_started=True)