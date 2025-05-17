from pydantic import BaseModel
from typing import Dict, Any, Optional, Union
from datetime import datetime

class ClientBase(BaseModel):
    name: str
    industry: str
    brand_voice: str
    target_audience: str
    website_url: Optional[str] = None
    social_profiles: Optional[Dict[str, str]] = None
    content_preferences: Optional[Union[Dict[str, Any], str]] = None

class ClientCreate(ClientBase):
    pass

class Client(ClientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Updated from orm_mode




