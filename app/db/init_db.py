from app.db.database import Base, engine
from app.db.models import Client, Content, ContentType, ContentStatus
from sqlalchemy.orm import Session
from app.db.database import SessionLocal

def init_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a session
    db = SessionLocal()
    
    # Check if we already have clients
    if db.query(Client).first() is None:
        # Add a sample client - check if columns exist in the model
        client_data = {
            "name": "Sample Client",
            "industry": "Technology",
            "brand_voice": "Professional and friendly",
            "target_audience": "Tech professionals aged 25-45",
            "content_preferences": {"preferred_formats": ["blog", "social"]}
        }
        
        # Only add website_url if it exists in the model
        try:
            sample_client = Client(
                **client_data,
                website_url="https://example.com"
            )
        except TypeError:
            # If website_url is not a valid column, create without it
            sample_client = Client(**client_data)
        
        db.add(sample_client)
        db.commit()
        db.refresh(sample_client)
        
        # Add a sample content
        content_data = {
            "title": "Welcome to Smart AI Content Generator",
            "body": "This is a sample content piece. Generate real content using the API.",
            "content_type": ContentType.BLOG,
            "status": ContentStatus.PUBLISHED,
            "topic": "AI Content Generation",
            "keywords": "AI, content, automation",
            "client_id": sample_client.id
        }
        
        # Only add word_count and visual_suggestions if they exist in the model
        try:
            sample_content = Content(
                **content_data,
                word_count=500,
                visual_suggestions="Example visual suggestion: Use an image showing AI generating content"
            )
        except TypeError:
            # If new columns don't exist, create without them
            sample_content = Content(**content_data)
        
        db.add(sample_content)
        db.commit()
    
    db.close()

if __name__ == "__main__":
    init_db()

