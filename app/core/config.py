import os
from pydantic_settings import BaseSettings
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Explicitly load the .env file
load_dotenv(verbose=True)

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Smart AI Content Generator"
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Print environment variables for debugging
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"GEMINI_API_KEY configured: {'Yes' if self.GEMINI_API_KEY else 'No'}")
        print(f"Raw GEMINI_API_KEY from env: {os.getenv('GEMINI_API_KEY')}")
        
        if not self.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY not set. Content generation will not work.")
        else:
            # Test the API key
            try:
                genai.configure(api_key=self.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content("Hello")
                print("GEMINI_API_KEY is valid and working.")
            except Exception as e:
                print(f"ERROR: GEMINI_API_KEY is set but not working: {str(e)}")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()


