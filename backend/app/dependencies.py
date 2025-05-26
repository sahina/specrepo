import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.api_key import get_user_by_api_key
from app.db.session import get_db
from app.models import User

# Set up logging
logger = logging.getLogger(__name__)

# Security scheme for API key authentication
# (auto_error=False to handle manually)
security = HTTPBearer(auto_error=False)


def get_api_key_from_header(request: Request) -> Optional[str]:
    """
    Extract API key from X-API-Key header.

    Args:
        request: FastAPI request object

    Returns:
        API key if present, None otherwise
    """
    return request.headers.get("X-API-Key")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    Dependency to get the current authenticated user.
    Supports both Bearer token and X-API-Key header authentication.

    Args:
        request: FastAPI request object
        db: Database session
        credentials: Bearer token credentials (optional)

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    client_ip = request.client.host if request.client else "unknown"
    api_key = None

    # Try to get API key from X-API-Key header first
    api_key = get_api_key_from_header(request)

    # If not found, try Bearer token
    if not api_key and credentials:
        api_key = credentials.credentials

    if not api_key:
        logger.warning(
            f"Authentication failed: No API key provided from {client_ip}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate API key
    user = get_user_by_api_key(db, api_key)

    if not user:
        logger.warning(
            f"Authentication failed: Invalid API key from {client_ip}"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(
        f"Authentication successful for user {user.username} from {client_ip}"
    )
    return user


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional dependency to get the current user.
    Returns None if no valid authentication is provided.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None
