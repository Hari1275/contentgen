from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.content import ContentCreate, Content as ContentSchema, ContentType, ContentStatus
from app.models.client import Client as ClientSchema
from app.db.models import Content, Client, ContentType as DBContentType, ContentStatus as DBContentStatus
from app.db.database import get_db
from app.services.crew_service import ContentCrewService
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/content", tags=["content"])

# Create a thread pool executor for running CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=3)

def run_crew_ai(client_info, topic):
    """Run CrewAI in a separate thread"""
    crew_service = ContentCrewService()
    return crew_service.generate_blog_post(client_info, topic)

@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_content(
    client_id: int, 
    content_type: str,
    topic: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    # Check if client exists
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Convert DB model to Pydantic model for the CrewAI service
    client_info = ClientSchema(
        id=db_client.id,
        name=db_client.name,
        industry=db_client.industry,
        brand_voice=db_client.brand_voice,
        target_audience=db_client.target_audience,
        content_preferences=db_client.content_preferences,
        created_at=db_client.created_at,
        updated_at=db_client.updated_at
    )
    
    # Map string content_type to enum
    try:
        db_content_type = DBContentType[content_type.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Content type '{content_type}' not supported")
    
    # Create a placeholder content entry
    content = Content(
        title=f"Generating {topic or 'content'}...",
        body="Content is being generated. Please check back in a few minutes.",
        content_type=db_content_type,
        status=DBContentStatus.DRAFT,
        topic=topic or "Generated Topic",
        keywords="",
        client_id=client_id
    )
    
    db.add(content)
    db.commit()
    db.refresh(content)
    
    # Run CrewAI in a background task
    async def generate_in_background():
        loop = asyncio.get_event_loop()
        # Since run_crew_ai is a regular function, not a coroutine, we don't need to await it
        result = await loop.run_in_executor(executor, run_crew_ai, client_info, topic)
        
        # Now result is a string, not a coroutine
        lines = result.split('\n')
        title = lines[0].strip() if lines else "Generated Blog Post"
        body = '\n'.join(lines[1:]) if len(lines) > 1 else result
        
        # Get a new session since we're in a background task
        from app.db.database import SessionLocal
        db = SessionLocal()
        try:
            # Update the content in the database
            content_obj = db.query(Content).filter(Content.id == content.id).first()
            if content_obj:
                content_obj.title = title
                content_obj.body = body
                content_obj.status = DBContentStatus.REVIEW
                content_obj.updated_at = datetime.now()
                db.commit()
        finally:
            db.close()
    
    # Start the background task
    if background_tasks:
        background_tasks.add_task(generate_in_background)
    
    return {
        "message": "Content generation started", 
        "content_id": content.id,
        "status": "processing"
    }

@router.get("/", response_model=List[ContentSchema])
def get_all_content(
    client_id: Optional[int] = None,
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Content)
    
    if client_id:
        query = query.filter(Content.client_id == client_id)
    
    if content_type:
        try:
            db_content_type = DBContentType[content_type.upper()]
            query = query.filter(Content.content_type == db_content_type)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Content type '{content_type}' not valid")
    
    if status:
        try:
            db_status = DBContentStatus[status.upper()]
            query = query.filter(Content.status == db_status)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Status '{status}' not valid")
    
    contents = query.all()
    return contents

@router.get("/{content_id}", response_model=ContentSchema)
def get_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(Content).filter(Content.id == content_id).first()
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return content

@router.put("/{content_id}/status")
def update_content_status(
    content_id: int, 
    status: str,
    db: Session = Depends(get_db)
):
    content = db.query(Content).filter(Content.id == content_id).first()
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    
    try:
        db_status = DBContentStatus[status.upper()]
        content.status = db_status
        content.updated_at = datetime.now()
        db.commit()
        db.refresh(content)
        return {"message": f"Content status updated to {status}"}
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Status '{status}' not valid")

@router.put("/{content_id}", response_model=ContentSchema)
async def update_content(
    content_id: int,
    content_update: ContentCreate,
    db: Session = Depends(get_db)
):
    content = db.query(Content).filter(Content.id == content_id).first()
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    
    for key, value in content_update.dict().items():
        if key == "keywords":
            setattr(content, key, ",".join(value))
        else:
            setattr(content, key, value)
    
    content.updated_at = datetime.now()
    db.commit()
    db.refresh(content)
    
    return content

@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(content_id: int, db: Session = Depends(get_db)):
    content = db.query(Content).filter(Content.id == content_id).first()
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    
    db.delete(content)
    db.commit()
    
    return None



