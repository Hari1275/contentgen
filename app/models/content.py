from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ContentType(str, Enum):
    BLOG = "blog"
    ARTICLE = "article"
    SOCIAL = "social"
    EMAIL = "email"
    WEBSITE = "website"
    CONTENT_PLAN = "content_plan"
    STRATEGY = "strategy"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"

class ContentStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ContentBase(BaseModel):
    title: str
    body: str
    content_type: ContentType
    status: ContentStatus = ContentStatus.DRAFT
    topic: Optional[str] = None
    keywords: Optional[str] = None
    client_id: int

class ContentCreate(ContentBase):
    pass

class Content(ContentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    word_count: Optional[int] = 500
    visual_suggestions: Optional[str] = None

    class Config:
        from_attributes = True  # Updated from orm_mode

class ContentSuggestion(BaseModel):
    title: str
    content_type: str
    description: str
    keywords: List[str]
    hashtags: List[str]





