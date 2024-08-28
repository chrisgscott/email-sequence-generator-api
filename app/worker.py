import os
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

print(f"REDIS_URL from settings: {settings.REDIS_URL}")
print(f"REDIS_URL from environment: {os.getenv('REDIS_URL')}")

try:
    celery_app = Celery('email_sequence_generator',
                        broker=settings.REDIS_URL,
                        backend=settings.REDIS_URL)

    celery_app.conf.task_routes = {
        'app.tasks.*': {'queue': 'email_tasks'}
    }

    # Add more configuration and task definitions here

except Exception as e:
    print(f"Error initializing Celery app: {str(e)}")
    print(f"All environment variables: {os.environ}")