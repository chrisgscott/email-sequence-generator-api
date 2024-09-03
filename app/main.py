import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import engine, Base, SessionLocal
from app.api.api_v1.api import router as api_router
from app.services.email_service import check_and_send_scheduled_emails, check_and_schedule_emails
from app.services import api_key_service
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

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
def read_root():
    return {"message": "Welcome to the Email Sequence Generator API"}

scheduler = BackgroundScheduler()

def locked_check_and_send_scheduled_emails():
    check_and_send_scheduled_emails()

scheduler.add_job(locked_check_and_send_scheduled_emails, CronTrigger(minute="*/5")) #Set to 5 minutes for testing. Change this to something more appropriate for production.
scheduler.add_job(check_and_schedule_emails, CronTrigger(hour="0", minute="0"))  # Run daily at midnight
scheduler.start()

app.add_event_handler("shutdown", scheduler.shutdown)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def validate_api_key(api_key: str = Depends(api_key_header), db: Session = Depends(get_db)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key is missing")
    if not api_key_service.validate_api_key(db, api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dailyjournalprompts.co"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", API_KEY_NAME],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, workers=8, timeout_keep_alive=120)