from pydantic import BaseModel
from typing import Dict, Any

class BlogPostCreate(BaseModel):
    content: str
    metadata: Dict[str, Any]

class BlogPostResponse(BaseModel):
    message: str