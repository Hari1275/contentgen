from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.database import Base

# Enums for content type and status
class ContentType(enum.Enum):
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

class ContentStatus(enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"

# Note: Users are managed by Supabase, not in our database
# We only store the Supabase user ID reference

# Client model
class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    industry = Column(String(200))
    brand_voice = Column(Text)  # Changed to Text for longer descriptions
    target_audience = Column(Text)  # Changed to Text for longer descriptions
    content_preferences = Column(JSON, nullable=True)  # Store as JSON
    website_url = Column(String(255), nullable=True)  # Add website_url column
    social_profiles = Column(JSON, nullable=True)  # Add social_profiles column
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Foreign keys - Supabase user UUID
    user_id = Column(String(36), nullable=False, index=True)  # Supabase user UUID

    # Relationships
    contents = relationship("Content", back_populates="client")

# Content model
class Content(Base):
    __tablename__ = "contents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    content_type = Column(Enum(ContentType), nullable=False)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT)
    topic = Column(String(255), nullable=True)
    keywords = Column(String(255), nullable=True)
    word_count = Column(Integer, default=500)
    visual_suggestions = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    client_id = Column(Integer, ForeignKey("clients.id"))
    
    # Relationships
    client = relationship("Client", back_populates="contents")




