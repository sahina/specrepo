import logging
from typing import Dict

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.auth.api_key import create_user_with_api_key
from app.db.session import get_db
from app.dependencies import get_current_user
from app.middleware import RateLimitMiddleware
from app.models import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SpecRepo API", version="1.0.0")

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, max_attempts=5, window_seconds=300)


@app.get("/health")
def read_root():
    """Health check endpoint - no authentication required."""
    return {"status": "healthy"}


@app.post("/api/users", response_model=Dict[str, str])
def create_user(username: str, email: str, db: Session = Depends(get_db)):
    """
    Create a new user with an API key.
    This endpoint is public for user registration.
    """
    try:
        user, api_key = create_user_with_api_key(db, username, email)
        logger.info(f"Created new user: {username}")
        return {
            "message": "User created successfully",
            "username": user.username,
            "api_key": api_key,
        }
    except Exception as e:
        logger.error(f"Failed to create user {username}: {str(e)}")
        raise


@app.get("/api/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile - requires authentication.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at,
    }


@app.get("/api/protected")
def protected_endpoint(current_user: User = Depends(get_current_user)):
    """
    Example protected endpoint that requires authentication.
    """
    return {
        "message": f"Hello {current_user.username}! "
        f"This is a protected endpoint.",
        "user_id": current_user.id,
    }
