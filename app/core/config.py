import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./content_platform.db")
    
    # Application settings
    APP_NAME: str = "Content Creation Platform"
    APP_VERSION: str = "0.1.0"
    
    class Config:
        env_file = ".env"

# Create settings instance
settings = Settings()
