"""
Tests for the validation endpoints (Task 12).
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.api_key import create_user_with_api_key
from app.db.session import get_db
from app.models import APISpecification, User, ValidationRun
from app.schemas import AuthMethod, ValidationRunStatus
from main import app

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def override_get_db(db_session):
    """Override the get_db dependency to use the test database session."""

    def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides.clear()


class TestValidationEndpoints:
    """Test class for validation endpoints."""

    @pytest.fixture
    def sample_openapi_spec(self):
        """Sample OpenAPI specification for testing."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "A test API specification",
            },
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint",
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"message": {"type": "string"}},
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
        }

    @pytest.fixture
    def sample_user_and_headers(self, db_session: Session):
        """Create a test user and return both user and auth headers."""
        unique_id = str(uuid.uuid4())[:8]
        user, api_key = create_user_with_api_key(
            db_session,
            f"testuser_{unique_id}",
            f"test_{unique_id}@example.com",
        )
        return user, {"X-API-Key": api_key}

    @pytest.fixture
    def sample_user(self, sample_user_and_headers):
        """Get the sample user."""
        return sample_user_and_headers[0]

    @pytest.fixture
    def auth_headers(self, sample_user_and_headers):
        """Get the auth headers."""
        return sample_user_and_headers[1]

    @pytest.fixture
    def sample_api_specification(
        self,
        db_session: Session,
        sample_user: User,
        sample_openapi_spec: dict,
    ):
        """Create a test API specification."""
        spec = APISpecification(
            name="Test API",
            version_string="v1.0",
            openapi_content=sample_openapi_spec,
            user_id=sample_user.id,
        )
        db_session.add(spec)
        db_session.commit()
        db_session.refresh(spec)
        return spec

    @pytest.fixture
    def sample_validation_run(
        self,
        db_session: Session,
        sample_api_specification: APISpecification,
        sample_user: User,
    ):
        """Create a test validation run."""
        validation_run = ValidationRun(
            api_specification_id=sample_api_specification.id,
            provider_url="https://api.example.com",
            user_id=sample_user.id,
            auth_method=AuthMethod.NONE.value,
            status=ValidationRunStatus.PENDING.value,
        )
        db_session.add(validation_run)
        db_session.commit()
        db_session.refresh(validation_run)
        return validation_run

    def test_trigger_validation_success(
        self,
        db_session: Session,
        sample_user: User,
        sample_api_specification: APISpecification,
        auth_headers: dict,
    ):
        """Test successful validation triggering."""
        validation_data = {
            "api_specification_id": sample_api_specification.id,
            "provider_url": "https://httpbin.org/spec.json",
            "auth_method": AuthMethod.NONE.value,
            "max_examples": 50,
            "timeout": 120,
        }

        response = client.post(
            "/api/validations",
            json=validation_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["api_specification_id"] == sample_api_specification.id
        assert data["provider_url"] == "https://httpbin.org/spec.json"
        assert data["status"] == "pending"
        assert data["auth_method"] == AuthMethod.NONE.value
        assert data["user_id"] == sample_user.id
        assert "id" in data
        assert "triggered_at" in data

    def test_trigger_validation_invalid_url(
        self,
        db_session: Session,
        sample_api_specification: APISpecification,
        auth_headers: dict,
    ):
        """Test validation triggering with invalid provider URL."""
        validation_data = {
            "api_specification_id": sample_api_specification.id,
            "provider_url": "invalid-url",
            "auth_method": AuthMethod.NONE.value,
        }

        response = client.post(
            "/api/validations",
            json=validation_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_trigger_validation_unreachable_url(
        self,
        db_session: Session,
        sample_api_specification: APISpecification,
        auth_headers: dict,
    ):
        """Test validation triggering with unreachable provider URL."""
        validation_data = {
            "api_specification_id": sample_api_specification.id,
            "provider_url": "https://nonexistent-domain-12345.com",
            "auth_method": AuthMethod.NONE.value,
        }

        response = client.post(
            "/api/validations",
            json=validation_data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "not reachable" in response.json()["detail"]

    def test_get_validation_results_success(
        self,
        db_session: Session,
        sample_validation_run,
        auth_headers: dict,
    ):
        """Test successful retrieval of validation results."""
        response = client.get(
            f"/api/validations/{sample_validation_run.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_validation_run.id
        assert data["api_specification_id"] == sample_validation_run.api_specification_id
        assert data["provider_url"] == sample_validation_run.provider_url
        assert data["status"] == sample_validation_run.status
        assert data["user_id"] == sample_validation_run.user_id

    def test_get_validation_results_not_found(
        self,
        auth_headers: dict,
    ):
        """Test retrieval of non-existent validation results."""
        response = client.get(
            "/api/validations/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_list_validations_success(
        self,
        db_session: Session,
        sample_validation_run,
        auth_headers: dict,
    ):
        """Test successful listing of validations."""
        response = client.get(
            "/api/validations",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_validations_with_filters(
        self,
        db_session: Session,
        sample_validation_run,
        auth_headers: dict,
    ):
        """Test listing validations with filters."""
        response = client.get(
            "/api/validations",
            params={
                "api_specification_id": sample_validation_run.api_specification_id,
                "status": sample_validation_run.status,
                "page": 1,
                "size": 5,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5

        # All returned items should match the filter
        for item in data["items"]:
            assert (
                item["api_specification_id"] == sample_validation_run.api_specification_id
            )
            assert item["status"] == sample_validation_run.status

    def test_list_validations_pagination(
        self,
        auth_headers: dict,
    ):
        """Test validation listing pagination."""
        response = client.get(
            "/api/validations",
            params={"page": 1, "size": 2},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) <= 2

    def test_trigger_validation_unauthorized(
        self,
        sample_api_specification: APISpecification,
    ):
        """Test validation triggering without authentication."""
        validation_data = {
            "api_specification_id": sample_api_specification.id,
            "provider_url": "https://httpbin.org/spec.json",
            "auth_method": AuthMethod.NONE.value,
        }

        response = client.post(
            "/api/validations",
            json=validation_data,
        )

        assert response.status_code == 401

    def test_get_validation_results_unauthorized(
        self,
        sample_validation_run,
    ):
        """Test validation results retrieval without authentication."""
        response = client.get(f"/api/validations/{sample_validation_run.id}")

        assert response.status_code == 401

    def test_list_validations_unauthorized(
        self,
    ):
        """Test validation listing without authentication."""
        response = client.get("/api/validations")

        assert response.status_code == 401
