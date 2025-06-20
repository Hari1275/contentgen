from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from sqlalchemy.orm import Session
from app.models.client import ClientCreate, Client as ClientSchema
from app.db.models import Client
from app.db.database import get_db
from app.core.supabase_auth import get_current_active_user, SupabaseUser

router = APIRouter(prefix="/clients", tags=["clients"])

@router.post("/", response_model=ClientSchema, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Create a new client for the authenticated user"""
    # Create a new client linked to the authenticated user
    db_client = Client(
        name=client.name,
        industry=client.industry,
        brand_voice=client.brand_voice,
        target_audience=client.target_audience,
        content_preferences=client.content_preferences,
        website_url=client.website_url,
        social_profiles=client.social_profiles,
        user_id=current_user.id  # Link to Supabase user ID
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@router.get("/", response_model=List[ClientSchema])
def read_clients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Get all clients for the authenticated user"""
    clients = db.query(Client).filter(
        Client.user_id == current_user.id
    ).offset(skip).limit(limit).all()

    return clients

@router.get("/{client_id}", response_model=ClientSchema)
def read_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Get a specific client (only if owned by authenticated user)"""
    db_client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@router.put("/{client_id}", response_model=ClientSchema)
def update_client(
    client_id: int,
    client: ClientCreate,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Update a client (only if owned by authenticated user)"""
    db_client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # Update client attributes
    for key, value in client.model_dump(exclude_unset=True).items():
        setattr(db_client, key, value)

    db.commit()
    db.refresh(db_client)
    return db_client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: SupabaseUser = Depends(get_current_active_user)
):
    """Delete a client (only if owned by authenticated user)"""
    db_client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == current_user.id
    ).first()
    if db_client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    db.delete(db_client)
    db.commit()
    return None




