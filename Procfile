web: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
worker: celery -A celery_worker worker --loglevel=info
beat: celery -A celery_worker beat --loglevel=info