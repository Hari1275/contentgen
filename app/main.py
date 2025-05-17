from fastapi import FastAPI
from app.api.api import api_router
from app.core.config import settings
from app.db.init_db import init_db
import os
from fastapi.middleware.cors import CORSMiddleware

# Create data directory if it doesn't exist
os.makedirs("./data", exist_ok=True)

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
def startup_event():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart AI Content Generator API"}



