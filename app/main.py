from fastapi import FastAPI
from app.api.api import api_router
from app.core.config import settings
from app.db.init_db import init_db
from fastapi.middleware.cors import CORSMiddleware

# Using Supabase PostgreSQL - no local data directory needed

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except Exception as e:
        # Don't fail the startup, just log the error
        pass

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart AI Content Generator API"}



