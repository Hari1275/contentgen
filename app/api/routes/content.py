from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.content import ContentCreate, Content as ContentSchema, ContentType, ContentStatus, ContentSuggestion
from app.models.client import Client as ClientSchema
from app.db.models import Content, Client, ContentType as DBContentType, ContentStatus as DBContentStatus
from app.db.database import get_db
from app.core.supabase_auth import get_current_active_user, SupabaseUser
from app.services.crew_service import ContentCrewService
from app.services.memory_service import MemoryService
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/content", tags=["content"])

# Create a thread pool executor for running CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=3)

def run_crew_ai(client_info, topic, content_type="blog", word_count=500):
    """Run CrewAI in a separate thread"""
    crew_service = ContentCrewService()
    return crew_service.generate_blog_post(client_info, topic, content_type, word_count)

@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_content(
    background_tasks: BackgroundTasks,
    client_id: int,
    content_type: str,
    topic: Optional[str] = None,
    word_count: Optional[int] = 500,
    tone: Optional[str] = None,
    keywords: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Generate content for a client (only if owned by authenticated user)"""
    # Check if client exists and belongs to the authenticated user
    db_client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found or access denied")
    
    # Convert DB model to Pydantic model for the CrewAI service
    client_info = ClientSchema(
        id=db_client.id,
        name=db_client.name,
        industry=db_client.industry,
        brand_voice=db_client.brand_voice,
        target_audience=db_client.target_audience,
        content_preferences=db_client.content_preferences,
        website_url=getattr(db_client, 'website_url', None),
        social_profiles=getattr(db_client, 'social_profiles', None),
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
        keywords=keywords or "",
        client_id=client_id,
        word_count=word_count
    )
    
    db.add(content)
    db.commit()
    db.refresh(content)
    
    # Run CrewAI in a background task
    async def generate_in_background():
        try:
            # Use direct function call instead of run_in_executor for debugging
            from app.services.crew_service import ContentCrewService
            crew_service = ContentCrewService()

            # Check if this is a social media post that needs special handling
            social_media_types = ['instagram', 'twitter', 'linkedin', 'facebook', 'social']

            if content_type.lower() in social_media_types:
                # Use the specialized social media generation method
                result = crew_service.generate_social_media_post(
                    client_info,
                    topic,
                    platform=content_type.lower(),
                    word_count=word_count or 100,  # Default to 100 words for social media
                    tone=tone,
                    keywords=keywords
                )
            else:
                # Use the standard blog post generation method
                result = crew_service.generate_blog_post(
                    client_info,
                    topic,
                    content_type.lower(),
                    word_count,
                    tone,
                    keywords
                )
            
            # Process the result to separate content and visual suggestions
            if "VISUAL SUGGESTIONS:" in result:
                content_parts = result.split("VISUAL SUGGESTIONS:", 1)  # Split only on first occurrence
                main_content = content_parts[0].strip()
                visual_suggestions = "VISUAL SUGGESTIONS:" + content_parts[1].strip()
            else:
                main_content = result.strip()
                visual_suggestions = "No specific visual suggestions provided."
            
            # If main_content is empty, use a fallback
            if not main_content:
                main_content = f"""
                {topic}
                
                Are you tired of allergies disrupting your daily life? Nishamritha Tablets offer a natural, Ayurvedic solution to provide lasting relief from allergy symptoms.
                
                ## Understanding Allergies
                Allergies occur when your immune system reacts to foreign substances that are typically harmless. These reactions can cause sneezing, itching, and other uncomfortable symptoms that affect your quality of life.
                
                ## The Ayurvedic Approach
                Nishamritha Tablets are formulated based on ancient Ayurvedic principles, using a blend of natural herbs and ingredients known for their anti-allergic properties. Unlike conventional medications, these tablets address the root cause of allergies rather than just masking the symptoms.
                
                ## Key Benefits
                - Natural ingredients with no harsh chemicals
                - Long-lasting relief rather than temporary symptom suppression
                - No drowsiness or other common side effects
                - Strengthens your immune system over time
                
                Try Nishamritha Tablets today and experience the freedom of living without allergy constraints.
                """
            
            # Extract title and body from main content
            lines = main_content.split('\n')
            
            # The first non-empty line is the title
            title_lines = [line for line in lines if line.strip()]
            title = title_lines[0].strip() if title_lines else topic
            
            # Everything after the title is the body
            if len(title_lines) > 1:
                # Find the index of the title in the original lines
                title_index = lines.index(title_lines[0])
                # Body is everything after the title
                body = '\n'.join(lines[title_index+1:]).strip()
            else:
                body = ""
            
            # If body is still empty, use the main_content except the first line
            if not body and len(lines) > 1:
                body = '\n'.join(lines[1:]).strip()
            
            # If body is still empty, use the entire main_content
            if not body:
                body = main_content
                
            # If title is the same as topic and body starts with a potential title, extract it
            if title == topic and body:
                body_lines = body.split('\n')
                if body_lines and body_lines[0].strip():
                    potential_title = body_lines[0].strip()
                    # Check if it looks like a title (not too long, no periods at end)
                    if len(potential_title) < 100 and not potential_title.endswith('.'):
                        title = potential_title
                        body = '\n'.join(body_lines[1:]).strip()
            
            # If body is still empty after all attempts, use a fallback
            if not body:
                body = f"""
                Are you tired of allergies disrupting your daily life? Nishamritha Tablets offer a natural, Ayurvedic solution to provide lasting relief from allergy symptoms.
                
                ## Understanding Allergies
                Allergies occur when your immune system reacts to foreign substances that are typically harmless. These reactions can cause sneezing, itching, and other uncomfortable symptoms that affect your quality of life.
                
                ## The Ayurvedic Approach
                Nishamritha Tablets are formulated based on ancient Ayurvedic principles, using a blend of natural herbs and ingredients known for their anti-allergic properties. Unlike conventional medications, these tablets address the root cause of allergies rather than just masking the symptoms.
                
                ## Key Benefits
                - Natural ingredients with no harsh chemicals
                - Long-lasting relief rather than temporary symptom suppression
                - No drowsiness or other common side effects
                - Strengthens your immune system over time
                
                Try Nishamritha Tablets today and experience the freedom of living without allergy constraints.
                """
            
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
                    content_obj.visual_suggestions = visual_suggestions
                    content_obj.updated_at = datetime.now()
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            
            # Update content with error message
            from app.db.database import SessionLocal
            db = SessionLocal()
            try:
                content_obj = db.query(Content).filter(Content.id == content.id).first()
                if content_obj:
                    content_obj.title = f"Error: {str(e)[:50]}"
                    content_obj.body = f"Error generating content: {str(e)}\n\n{error_details}"
                    content_obj.status = DBContentStatus.REVIEW
                    content_obj.updated_at = datetime.now()
                    db.commit()
            finally:
                db.close()
    
    # Start the background task
    background_tasks.add_task(generate_in_background)
    
    return {
        "message": "Content generation started", 
        "content_id": content.id,
        "status": "processing"
    }

@router.get("/", response_model=List[ContentSchema])
def read_contents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Get all content for the authenticated user (from their clients only)"""
    # Get all client IDs that belong to the user
    user_client_ids = db.query(Client.id).filter(Client.user_id == current_user.id).subquery()

    # Get content only from user's clients
    contents = db.query(Content).filter(
        Content.client_id.in_(user_client_ids)
    ).offset(skip).limit(limit).all()

    return contents

@router.get("/client/{client_id}", response_model=List[ContentSchema])
def get_content_by_client(
    client_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Get all content for a specific client (only if owned by authenticated user)"""
    # First, check if client exists at all
    client_exists = db.query(Client).filter(Client.id == client_id).first()
    if not client_exists:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check if client belongs to the authenticated user
    if client_exists.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Client not found or access denied")

    # Check if client exists and belongs to the authenticated user
    db_client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found or access denied")

    # Build query for client's content
    query = db.query(Content).filter(Content.client_id == client_id)

    # Apply optional filters
    if status:
        try:
            status_enum = DBContentStatus[status.upper()]
            query = query.filter(Content.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if content_type:
        try:
            content_type_enum = DBContentType[content_type.upper()]
            query = query.filter(Content.content_type == content_type_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid content type: {content_type}")

    # Order by most recent first and apply pagination
    contents = query.order_by(Content.created_at.desc()).offset(skip).limit(limit).all()

    return contents

@router.get("/client/{client_id}/stats")
def get_client_content_stats(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Get content statistics for a specific client (only if owned by authenticated user)"""
    # Check if client exists and belongs to the authenticated user
    db_client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found or access denied")

    # Get total content count
    total_content = db.query(Content).filter(Content.client_id == client_id).count()

    # Get content by status
    status_counts = {}
    for status in DBContentStatus:
        count = db.query(Content).filter(
            Content.client_id == client_id,
            Content.status == status
        ).count()
        status_counts[status.value] = count

    # Get content by type
    type_counts = {}
    for content_type in DBContentType:
        count = db.query(Content).filter(
            Content.client_id == client_id,
            Content.content_type == content_type
        ).count()
        type_counts[content_type.value] = count

    # Get recent content (last 7 days)
    from datetime import datetime, timedelta
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_content = db.query(Content).filter(
        Content.client_id == client_id,
        Content.created_at >= seven_days_ago
    ).count()

    return {
        "client_id": client_id,
        "total_content": total_content,
        "status_breakdown": status_counts,
        "type_breakdown": type_counts,
        "recent_content_7_days": recent_content
    }

@router.get("/{content_id}", response_model=ContentSchema)
def read_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Get specific content (only if from user's client)"""
    # Get content and verify it belongs to user's client
    content = db.query(Content).join(Client).filter(
        Content.id == content_id,
        Client.user_id == current_user.id
    ).first()
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found or access denied")
    return content

@router.put("/{content_id}", response_model=ContentSchema)
def update_content(
    content_id: int,
    content: ContentCreate,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Update content (only if from user's client)"""
    # Get content and verify it belongs to user's client
    db_content = db.query(Content).join(Client).filter(
        Content.id == content_id,
        Client.user_id == current_user.id
    ).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found or access denied")

    # Update content attributes
    for key, value in content.model_dump().items():
        if key == 'content_type':
            db_content.content_type = DBContentType[value.upper()]
        elif key == 'status':
            db_content.status = DBContentStatus[value.upper()]
        else:
            setattr(db_content, key, value)

    db.commit()
    db.refresh(db_content)
    return db_content

@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Delete content (only if from user's client)"""
    # Get content and verify it belongs to user's client
    db_content = db.query(Content).join(Client).filter(
        Content.id == content_id,
        Client.user_id == current_user.id
    ).first()
    if db_content is None:
        raise HTTPException(status_code=404, detail="Content not found or access denied")

    db.delete(db_content)
    db.commit()
    return None

@router.get("/suggestions/{client_id}", response_model=List[ContentSuggestion])
async def get_content_suggestions(
    client_id: int,
    suggestion_count: int = 3,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Get AI-generated content suggestions for a specific client (only if owned by user)"""
    # Check if client exists and belongs to the authenticated user
    db_client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found or access denied")
    
    # Validate suggestion_count
    try:
        suggestion_count = int(suggestion_count)
        if suggestion_count < 1 or suggestion_count > 10:
            suggestion_count = 3  # Default to 3 if out of range
    except (ValueError, TypeError):
        suggestion_count = 3  # Default to 3 if not a valid integer
    
    # Use memory service to generate suggestions
    memory_service = MemoryService(db)
    suggestions = await memory_service.generate_content_suggestions(client_id, suggestion_count)
    
    if suggestions and isinstance(suggestions[0], dict) and "error" in suggestions[0]:
        raise HTTPException(status_code=500, detail=suggestions[0]["error"])
    
    return suggestions

@router.get("/debug/database-state")
def debug_database_state(db: Session = Depends(get_db)):
    """Debug endpoint to check database state"""

    # Check all clients
    all_clients = db.query(Client).all()

    clients_info = []
    for client in all_clients:
        clients_info.append({
            "id": client.id,
            "name": client.name,
            "user_id": getattr(client, 'user_id', 'NO_USER_ID'),
            "has_user_id": hasattr(client, 'user_id') and client.user_id is not None
        })

    # Check all content
    all_content = db.query(Content).all()

    content_info = []
    for content in all_content:
        # Check if the client for this content exists
        client_exists = db.query(Client).filter(Client.id == content.client_id).first()
        content_info.append({
            "id": content.id,
            "title": content.title,
            "client_id": content.client_id,
            "client_exists": client_exists is not None,
            "client_user_id": getattr(client_exists, 'user_id', None) if client_exists else None
        })

    return {
        "clients": clients_info,
        "content": content_info,
        "summary": {
            "total_clients": len(all_clients),
            "total_content": len(all_content),
            "clients_with_user_id": len([c for c in clients_info if c["has_user_id"]]),
            "orphaned_content": len([c for c in content_info if not c["client_exists"]])
        }
    }

@router.post("/generate-test", status_code=status.HTTP_200_OK)
async def test_generate_content(
    client_id: int,
    content_type: str,
    topic: Optional[str] = None,
    word_count: Optional[int] = 500,
    tone: Optional[str] = None,
    keywords: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Test endpoint that generates content synchronously (only for user's clients)"""
    # Check if client exists and belongs to the authenticated user
    db_client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found or access denied")
    
    # Convert DB model to Pydantic model for the CrewAI service
    client_info = ClientSchema(
        id=db_client.id,
        name=db_client.name,
        industry=db_client.industry,
        brand_voice=db_client.brand_voice,
        target_audience=db_client.target_audience,
        content_preferences=db_client.content_preferences,
        website_url=getattr(db_client, 'website_url', None),
        social_profiles=getattr(db_client, 'social_profiles', None),
        created_at=db_client.created_at,
        updated_at=db_client.updated_at
    )
    
    # Generate content directly (will block)
    from app.services.crew_service import ContentCrewService
    crew_service = ContentCrewService()

    try:
        # Check if this is a social media post that needs special handling
        social_media_types = ['instagram', 'twitter', 'linkedin', 'facebook', 'social']

        if content_type.lower() in social_media_types:
            # Use the specialized social media generation method
            result = crew_service.generate_social_media_post(
                client_info,
                topic,
                platform=content_type.lower(),
                word_count=word_count or 100,  # Default to 100 words for social media
                tone=tone,
                keywords=keywords
            )
        else:
            # Use the standard blog post generation method
            result = crew_service.generate_blog_post(
                client_info,
                topic,
                content_type.lower(),
                word_count,
                tone,
                keywords
            )
        
        return {"result": result}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating content: {str(e)}\n\n{error_details}"
        )