from pydantic import BaseModel

class DemoPromptRequest(BaseModel):
    interests: str
    goals: str

class DemoPromptResponse(BaseModel):
    journal_prompt: str
    wrap_up: str