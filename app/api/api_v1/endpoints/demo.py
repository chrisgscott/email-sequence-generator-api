from fastapi import APIRouter, Depends, HTTPException
from app.services import openai_service
from app.schemas.demo import DemoPromptRequest, DemoPromptResponse
from app.core.config import settings
from app.services.openai_service import cached_generate_demo_prompt
import logging

logger = logging.getLogger(__name__)

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
        logger.error(f"Error in generate_demo_prompt: {str(e)}", exc_info=True)
        return DemoPromptResponse(
            journal_prompt="We encountered an error generating your prompt. Please try again later.",
            wrap_up="Every challenge is an opportunity for growth."
        )