import logging

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.user import UserCreate
from app.core.auth import get_password_hash
import secrets
from app.services.email_service import send_email_to_brevo
from app.schemas.sequence import EmailContent
from datetime import datetime, timedelta
import pytz
from app.core.config import settings

def create_user_with_api_key(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.flush()

    api_key = secrets.token_urlsafe(32)
    db_api_key = APIKey(
        key=api_key,
        user_id=db_user.id,
        wordpress_url=user.wordpress_url,
        wordpress_username=user.wordpress_username,
        wordpress_app_password=user.wordpress_app_password
    )
    db.add(db_api_key)
    db.commit()
    db.refresh(db_user)

    return db_user, api_key

def send_password_reset_email(db: Session, email: str, reset_token: str):
    reset_link = f"{settings.BASE_URL}/reset-password/{reset_token}"
    
    email_content = EmailContent(
        subject="Password Reset Request",
        content={
            "body": f"Click the following link to reset your password: {reset_link}",
            "reset_link": reset_link
        },
        scheduled_for=datetime.now(pytz.UTC) + timedelta(minutes=1)
    )
    
    inputs = {}  # Add any additional inputs if needed
    
    try:
        message_id = send_email_to_brevo(db, email, email_content, inputs, settings.BREVO_PASSWORD_RESET_TEMPLATE_ID)
        logger.info(f"Password reset email sent to {email}. Message ID: {message_id}")
        return message_id
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        raise