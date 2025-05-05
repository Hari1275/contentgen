from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.database import Base

class ContentType(enum.Enum):
    BLOG = "blog"
    SOCIAL_POST = "social_post"
    HEADLINE = "headline"

class ContentStatus(enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    industry = Column(String)
    brand_voice = Column(String)
    target_audience = Column(String)
    content_preferences = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    contents = relationship("Content", back_populates="client")

class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    body = Column(Text)
    content_type = Column(Enum(ContentType))
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT)
    topic = Column(String, index=True)
    keywords = Column(String, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    client = relationship("Client", back_populates="contents")

