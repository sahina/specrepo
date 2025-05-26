import hashlib
import secrets
import string
from typing import Optional

from sqlalchemy.orm import Session

from app.models import User


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.

    Args:
        length: Length of the API key (default: 32)

    Returns:
        A secure random API key string
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.

    Args:
        api_key: The plain text API key

    Returns:
        The hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify a plain text API key against its hash.

    Args:
        plain_key: The plain text API key
        hashed_key: The stored hashed API key

    Returns:
        True if the keys match, False otherwise
    """
    return hash_api_key(plain_key) == hashed_key


def get_user_by_api_key(db: Session, api_key: str) -> Optional[User]:
    """
    Retrieve a user by their API key.

    Args:
        db: Database session
        api_key: The plain text API key

    Returns:
        User object if found and API key is valid, None otherwise
    """
    hashed_key = hash_api_key(api_key)
    return db.query(User).filter(User.api_key == hashed_key).first()


def create_user_with_api_key(
    db: Session, username: str, email: str
) -> tuple[User, str]:
    """
    Create a new user with a generated API key.

    Args:
        db: Database session
        username: Username for the new user
        email: Email for the new user

    Returns:
        Tuple of (User object, plain text API key)
    """
    plain_api_key = generate_api_key()
    hashed_api_key = hash_api_key(plain_api_key)

    user = User(username=username, email=email, api_key=hashed_api_key)

    db.add(user)
    db.commit()
    db.refresh(user)

    return user, plain_api_key
