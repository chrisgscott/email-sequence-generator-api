from fastapi import APIRouter
from app.api.api_v1.endpoints import users, sequences, api_keys, demo

router = APIRouter()

router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(sequences.router, prefix="/sequences", tags=["sequences"])
router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
router.include_router(demo.router, prefix="/demo", tags=["demo"])