web: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
worker: env REDIS_URL=$REDIS_URL celery -A celery_worker worker --loglevel=info
beat: env REDIS_URL=$REDIS_URL celery -A celery_worker beat --loglevel=info