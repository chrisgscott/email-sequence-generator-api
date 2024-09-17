from fastapi.security import APIKeyHeader
from fastapi import Security, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services import api_key_service

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Security(api_key_header), db: Session = Depends(get_db)):
    if api_key_service.validate_api_key(db, api_key):
        return api_key
    raise HTTPException(status_code=403, detail="Could not validate API Key")