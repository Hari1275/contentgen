import os
from pydantic_settings import BaseSettings
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables (but don't fail if .env doesn't exist in production)
try:
    load_dotenv(verbose=False)
except:
    pass

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Smart AI Content Generator"

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Supabase settings
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")
    SUPABASE_DB_PASSWORD: Optional[str] = os.getenv("SUPABASE_DB_PASSWORD")
    SUPABASE_JWT_SECRET: Optional[str] = os.getenv("SUPABASE_JWT_SECRET")

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]

    # API Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Only configure database if not already set via DATABASE_URL
        if not self.DATABASE_URL and self.SUPABASE_URL and self.SUPABASE_DB_PASSWORD:
            try:
                # Extract project ID from Supabase URL
                project_id = self.SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
                # Build database URL
                self.DATABASE_URL = f"postgresql://postgres:{self.SUPABASE_DB_PASSWORD}@db.{project_id}.supabase.co:5432/postgres"
            except Exception as e:
                pass
        
        # Validate required settings
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        
        # Configure Gemini API if available
        if self.GEMINI_API_KEY:
            try:
                genai.configure(api_key=self.GEMINI_API_KEY)
            except Exception as e:
                pass

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

settings = Settings()