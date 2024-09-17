import secrets
from sqlalchemy.orm import Session
from app.models.api_key import APIKey
from datetime import datetime
from typing import List
import logging

logger = logging.getLogger(__name__)

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

def get_api_key(db: Session, api_key: str) -> APIKey:
    return db.query(APIKey).filter(APIKey.key == api_key, APIKey.is_active == True).first()

def get_all_active_domains(db: Session) -> List[str]:
    active_api_keys = db.query(APIKey).filter(APIKey.is_active == True, APIKey.wordpress_url.isnot(None)).all()
    domains = list(set(extract_domain(api_key.wordpress_url) for api_key in active_api_keys))
    logger.info(f"Active domains: {['https://' + domain for domain in domains]}")
    return domains

def extract_domain(url: str) -> str:
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    logger.info(f"Extracted domain '{domain}' from URL '{url}'")
    return domain