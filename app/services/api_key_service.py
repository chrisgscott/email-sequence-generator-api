import secrets
from sqlalchemy.orm import Session
from app.models.api_key import APIKey
from datetime import datetime

def generate_api_key(db: Session, user_id: int) -> str:
    key = secrets.token_urlsafe(32)
    db_api_key = APIKey(key=key, user_id=user_id)
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    return key

def validate_api_key(db: Session, api_key: str) -> bool:
    db_api_key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.is_active == True).first()
    return db_api_key is not None

def deactivate_api_key(db: Session, key: str) -> bool:
    db_api_key = db.query(APIKey).filter(APIKey.key == key).first()
    if db_api_key:
        db_api_key.is_active = False
        db.commit()
        return True
    return False