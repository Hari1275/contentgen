from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ContentStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"

class ContentType(str, Enum):
    BLOG = "blog"
    SOCIAL_POST = "social_post"
    HEADLINE = "headline"

class ContentBase(BaseModel):
    title: str
    content_type: ContentType
    status: ContentStatus = ContentStatus.DRAFT
    topic: str
    client_id: int
    
class ContentCreate(ContentBase):
    keywords: List[str] = []
    
class Content(ContentBase):
    id: int
    body: str
    keywords: str  # Stored as comma-separated values in DB
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
