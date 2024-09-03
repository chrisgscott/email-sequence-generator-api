from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services import api_key_service
from app.core.auth import get_current_active_user
from app.schemas.user import User

router = APIRouter()

@router.post("/generate")
async def generate_api_key(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    api_key = api_key_service.generate_api_key(db, current_user.id)
    return {"api_key": api_key}

@router.post("/deactivate")
async def deactivate_api_key(api_key: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    success = api_key_service.deactivate_api_key(db, api_key)
    if success:
        return {"message": "API key deactivated successfully"}
    else:
        raise HTTPException(status_code=404, detail="API key not found")