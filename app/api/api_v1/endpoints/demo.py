from fastapi import APIRouter, Depends, HTTPException
from app.services import openai_service
from app.schemas.demo import DemoPromptRequest, DemoPromptResponse
from app.core.config import settings

router = APIRouter()

@router.post("/generate-prompt", response_model=DemoPromptResponse)
async def generate_demo_prompt(request: DemoPromptRequest):
    try:
        email_structure = settings.EMAIL_STRUCTURE
        demo_prompt = await openai_service.generate_demo_prompt(
            topic=settings.DEMO_TOPIC,
            inputs={
                "interests_and_topics": request.interests,
                "goals_and_aspirations": request.goals
            },
            email_structure=email_structure
        )
        return DemoPromptResponse(
            journal_prompt=demo_prompt["content"]["journal_prompt"],
            wrap_up=demo_prompt["content"]["wrap_up"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))