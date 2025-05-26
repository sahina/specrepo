import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.api_key import (
    create_user_with_api_key,
    generate_api_key,
    get_user_by_api_key,
    hash_api_key,
    verify_api_key,
)
from app.db.session import get_db
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_get_db(db_session):
    """Override the get_db dependency to use the test database session."""

    def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiting():
    """Reset rate limiting between tests."""
    # Reset the rate limiting middleware class variable
    from app.middleware import RateLimitMiddleware

    RateLimitMiddleware.reset_attempts()
    yield


class TestAPIKeyUtilities:
    """Test API key generation, hashing, and validation utilities."""

    def test_generate_api_key_default_length(self):
        """Test API key generation with default length."""
        api_key = generate_api_key()
        assert len(api_key) == 32
        assert api_key.isalnum()

    def test_generate_api_key_custom_length(self):
        """Test API key generation with custom length."""
        api_key = generate_api_key(length=16)
        assert len(api_key) == 16
        assert api_key.isalnum()

    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100  # All keys should be unique

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "test_api_key_123"
        hashed = hash_api_key(api_key)

        assert len(hashed) == 64  # SHA-256 produces 64-character hex string
        assert hashed != api_key  # Hash should be different from original

        # Same input should produce same hash
        assert hash_api_key(api_key) == hashed

    def test_verify_api_key_valid(self):
        """Test API key verification with valid key."""
        api_key = "test_api_key_123"
        hashed = hash_api_key(api_key)

        assert verify_api_key(api_key, hashed) is True

    def test_verify_api_key_invalid(self):
        """Test API key verification with invalid key."""
        api_key = "test_api_key_123"
        wrong_key = "wrong_api_key_456"
        hashed = hash_api_key(api_key)

        assert verify_api_key(wrong_key, hashed) is False


class TestUserAPIKeyOperations:
    """Test user creation and API key operations with database."""

    def test_create_user_with_api_key(self, db_session: Session):
        """Test creating a user with an API key."""
        username = "testuser"
        email = "test@example.com"

        user, plain_api_key = create_user_with_api_key(
            db_session, username, email
        )

        assert user.id is not None
        assert user.username == username
        assert user.email == email
        assert user.api_key != plain_api_key  # Should be hashed
        assert len(plain_api_key) == 32
        assert plain_api_key.isalnum()

        # Verify the API key is properly hashed
        assert verify_api_key(plain_api_key, user.api_key)

    def test_get_user_by_api_key_valid(self, db_session: Session):
        """Test retrieving user by valid API key."""
        username = "testuser2"
        email = "test2@example.com"

        user, plain_api_key = create_user_with_api_key(
            db_session, username, email
        )

        # Retrieve user by API key
        retrieved_user = get_user_by_api_key(db_session, plain_api_key)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.username == username
        assert retrieved_user.email == email

    def test_get_user_by_api_key_invalid(self, db_session: Session):
        """Test retrieving user by invalid API key."""
        invalid_key = "invalid_api_key_123"

        retrieved_user = get_user_by_api_key(db_session, invalid_key)

        assert retrieved_user is None

    def test_get_user_by_api_key_nonexistent(self, db_session: Session):
        """Test retrieving user by non-existent API key."""
        nonexistent_key = generate_api_key()

        retrieved_user = get_user_by_api_key(db_session, nonexistent_key)

        assert retrieved_user is None


class TestAuthenticationEndpoints:
    """Test FastAPI authentication endpoints."""

    def test_health_endpoint_no_auth(self):
        """Test health endpoint doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_create_user_endpoint(self, db_session: Session):
        """Test user creation endpoint."""
        response = client.post(
            "/api/users",
            params={"username": "newuser", "email": "new@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User created successfully"
        assert data["username"] == "newuser"
        assert "api_key" in data
        assert len(data["api_key"]) == 32

    def test_protected_endpoint_no_auth(self):
        """Test protected endpoint without authentication."""
        response = client.get("/api/protected")
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_protected_endpoint_invalid_auth(self):
        """Test protected endpoint with invalid API key."""
        headers = {"X-API-Key": "invalid_key"}
        response = client.get("/api/protected", headers=headers)
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_protected_endpoint_valid_auth_header(self, db_session: Session):
        """Test protected endpoint with valid API key in header."""
        # Create a user first
        user, api_key = create_user_with_api_key(
            db_session, "authuser", "auth@example.com"
        )

        headers = {"X-API-Key": api_key}
        response = client.get("/api/protected", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "Hello authuser!" in data["message"]
        assert data["user_id"] == user.id

    def test_protected_endpoint_valid_auth_bearer(self, db_session: Session):
        """Test protected endpoint with valid API key as Bearer token."""
        # Create a user first
        user, api_key = create_user_with_api_key(
            db_session, "beareruser", "bearer@example.com"
        )

        headers = {"Authorization": f"Bearer {api_key}"}
        response = client.get("/api/protected", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "Hello beareruser!" in data["message"]
        assert data["user_id"] == user.id

    def test_profile_endpoint_valid_auth(self, db_session: Session):
        """Test profile endpoint with valid authentication."""
        # Create a user first
        user, api_key = create_user_with_api_key(
            db_session, "profileuser", "profile@example.com"
        )

        headers = {"X-API-Key": api_key}
        response = client.get("/api/profile", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["username"] == "profileuser"
        assert data["email"] == "profile@example.com"
        assert "created_at" in data


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiting_multiple_failed_attempts(self, db_session: Session):
        """Test rate limiting after multiple failed authentication attempts."""
        headers = {"X-API-Key": "invalid_key"}

        # Make 5 failed requests - these should all return 401
        for i in range(5):
            response = client.get("/api/protected", headers=headers)
            assert response.status_code == 401
            assert "Invalid API key" in response.json()["detail"]

        # The 6th attempt should be rate limited and raise an HTTPException
        # Since TestClient doesn't handle middleware HTTPExceptions well,
        # we'll test that the exception is raised
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            client.get("/api/protected", headers=headers)

        assert exc_info.value.status_code == 429
        assert "Too many failed authentication attempts" in str(
            exc_info.value.detail
        )

    def test_rate_limiting_successful_auth_resets(self, db_session: Session):
        """Test that successful auth doesn't trigger rate limiting."""
        # Create a user first
        user, api_key = create_user_with_api_key(
            db_session, "ratelimituser", "ratelimit@example.com"
        )

        headers = {"X-API-Key": api_key}

        # Make multiple successful requests
        for _ in range(10):
            response = client.get("/api/protected", headers=headers)
            assert response.status_code == 200


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_api_key(self):
        """Test authentication with empty API key."""
        headers = {"X-API-Key": ""}
        response = client.get("/api/protected", headers=headers)
        assert response.status_code == 401

    def test_whitespace_api_key(self):
        """Test authentication with whitespace API key."""
        headers = {"X-API-Key": "   "}
        response = client.get("/api/protected", headers=headers)
        assert response.status_code == 401

    def test_very_long_api_key(self):
        """Test authentication with very long API key."""
        long_key = "a" * 1000
        headers = {"X-API-Key": long_key}
        response = client.get("/api/protected", headers=headers)
        assert response.status_code == 401

    def test_special_characters_api_key(self):
        """Test authentication with special characters in API key."""
        special_key = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        headers = {"X-API-Key": special_key}
        response = client.get("/api/protected", headers=headers)
        assert response.status_code == 401

    def test_duplicate_user_creation(self, db_session: Session):
        """Test creating users with duplicate usernames or emails."""
        # Create first user
        create_user_with_api_key(db_session, "duplicate", "dup@example.com")

        # Try to create user with same username
        with pytest.raises(Exception):  # Should raise IntegrityError
            create_user_with_api_key(
                db_session, "duplicate", "different@example.com"
            )

        # Try to create user with same email
        with pytest.raises(Exception):  # Should raise IntegrityError
            create_user_with_api_key(
                db_session, "different", "dup@example.com"
            )
