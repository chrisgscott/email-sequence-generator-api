from fastapi import APIRouter, Depends, HTTPException
from app.services import openai_service
from app.schemas.demo import DemoPromptRequest, DemoPromptResponse
from app.core.config import settings
from app.services.openai_service import cached_generate_demo_prompt

router = APIRouter()

@router.post("/generate-prompt", response_model=DemoPromptResponse)
async def generate_demo_prompt(request: DemoPromptRequest):
    try:
        demo_prompt = await cached_generate_demo_prompt(request.interests, request.goals)
        return DemoPromptResponse(
            journal_prompt=demo_prompt["journal_prompt"],
            wrap_up=demo_prompt["wrap_up"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))