from fastapi import APIRouter
from app.api.routes import content, clients

# Create main API router
api_router = APIRouter()

# Include routers from different modules
api_router.include_router(content.router)
api_router.include_router(clients.router)