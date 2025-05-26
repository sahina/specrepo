import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database URL from environment variable or default for development
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/appdb"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency that provides a database session.
    Yields a SQLAlchemy session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
