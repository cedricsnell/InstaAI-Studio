"""
Database connection and session management.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost/instaai"  # Default for local development
)

# Create engine
# For production, use connection pooling
# For local development with SQLite (fallback), use NullPool
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,
        max_overflow=20
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency for getting database session.

    Usage in FastAPI endpoints:
    ```python
    @app.get("/users")
    def get_users(db: Session = Depends(get_db)):
        return db.query(User).all()
    ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables."""
    from .models import Base
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def drop_db():
    """Drop all tables - USE WITH CAUTION!"""
    from .models import Base
    Base.metadata.drop_all(bind=engine)
    print("Database dropped!")
