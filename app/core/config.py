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

    # Database settings (will be configured automatically for Supabase)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Supabase settings
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")
    SUPABASE_DB_PASSWORD: Optional[str] = os.getenv("SUPABASE_DB_PASSWORD")
    SUPABASE_JWT_SECRET: Optional[str] = os.getenv("SUPABASE_JWT_SECRET")

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]

    # API Keys - Use regular string for simplicity
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Print environment variables for debugging
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Configure database URL based on Supabase credentials
        if self.SUPABASE_URL and self.SUPABASE_KEY:
            # Extract project ID from Supabase URL
            project_id = self.SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
            # Use the class attribute for database password
            db_password = self.SUPABASE_DB_PASSWORD or "[SET-YOUR-DB-PASSWORD]"

            # Use the correct Supabase database connection format
            self.DATABASE_URL = f"postgresql://postgres:{db_password}@db.{project_id}.supabase.co:5432/postgres"
            print(f"Supabase configuration detected. Project ID: {project_id}")
            if db_password == "[SET-YOUR-DB-PASSWORD]":
                print("WARNING: Please set SUPABASE_DB_PASSWORD in your .env file")
            else:
                print("Supabase database connection configured")
        else:
            print("ERROR: Supabase configuration not found!")
            print("Please set up your Supabase credentials in .env file:")
            print("- SUPABASE_URL=https://zixrefecjrzqngadgjxj.supabase.co")
            print("- SUPABASE_KEY=your_api_key")
            print("- SUPABASE_DB_PASSWORD=your_database_password")
            raise ValueError("Supabase configuration required")

        print(f"Database URL: {self.DATABASE_URL}")
        print(f"GEMINI_API_KEY configured: {'Yes' if self.GEMINI_API_KEY else 'No'}")

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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

settings = Settings()





