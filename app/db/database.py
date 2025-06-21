from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Use database URL from settings (Supabase PostgreSQL)
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Validate database URL
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL is not configured")

if SQLALCHEMY_DATABASE_URL.startswith('sqlite'):
    raise ValueError("SQLite is not supported. Please use PostgreSQL/Supabase database.")

if not SQLALCHEMY_DATABASE_URL.startswith('postgresql'):
    raise ValueError("Only PostgreSQL databases are supported. Please use a postgresql:// URL.")

# Create engine with PostgreSQL/Supabase parameters
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    echo=False,  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


