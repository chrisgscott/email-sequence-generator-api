import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import engine, Base
from app.api.api_v1.api import router as api_router
from app.services.email_service import check_and_send_scheduled_emails, check_and_schedule_emails
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from threading import Lock

# Configure logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Email Sequence Generator API"}

scheduler = BackgroundScheduler()
email_send_lock = Lock()

def locked_check_and_send_scheduled_emails():
    if email_send_lock.acquire(blocking=False):
        try:
            check_and_send_scheduled_emails()
        finally:
            email_send_lock.release()
    else:
        logger.info("Skipping email check as previous job is still running")

scheduler.add_job(locked_check_and_send_scheduled_emails, CronTrigger(minute="*/15"))
scheduler.add_job(check_and_schedule_emails, CronTrigger(hour="0", minute="0"))  # Run daily at midnight
scheduler.start()

app.add_event_handler("shutdown", scheduler.shutdown)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True, timeout_keep_alive=120)