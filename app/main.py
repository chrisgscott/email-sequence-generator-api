import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import engine, Base, SessionLocal
from app.api.api_v1.api import router as api_router
from app.services.email_service import check_and_send_scheduled_emails, check_and_schedule_emails
from app.services import api_key_service
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.auth import get_current_active_user
from app.schemas.user import User
from contextlib import contextmanager
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# Configure logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    environment=settings.ENVIRONMENT
)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dailyjournalprompts.co"],  # Add your frontend domain
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Welcome to the Email Sequence Generator API, {current_user.email}"}

scheduler = BackgroundScheduler()

def locked_check_and_send_scheduled_emails():
    check_and_send_scheduled_emails()

scheduler.add_job(locked_check_and_send_scheduled_emails, CronTrigger(minute="*/5")) #Set to 5 minutes for testing. Change this to something more appropriate for production.
scheduler.add_job(check_and_schedule_emails, CronTrigger(hour="0", minute="0"))  # Run daily at midnight
scheduler.start()

app.add_event_handler("shutdown", scheduler.shutdown)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, workers=8, timeout_keep_alive=120)