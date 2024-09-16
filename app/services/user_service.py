from sqlalchemy.orm import Session
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.user import UserCreate
from app.core.auth import get_password_hash
import secrets

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
        wordpress_password=user.wordpress_password
    )
    db.add(db_api_key)
    db.commit()
    db.refresh(db_user)

    return db_user, api_key