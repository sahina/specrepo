import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.api_key import create_user_with_api_key
from app.db.session import get_db
from app.services.har_uploads import HARUploadService
from main import app

client = TestClient(app)


@pytest.fixture
def sample_har_content():
    """Sample HAR content for testing."""
    return json.dumps(
        {
            "log": {
                "version": "1.2",
                "creator": {"name": "Test Creator", "version": "1.0"},
                "entries": [
                    {
                        "startedDateTime": "2023-01-01T00:00:00.000Z",
                        "time": 100,
                        "request": {
                            "method": "GET",
                            "url": "https://api.example.com/users",
                            "httpVersion": "HTTP/1.1",
                            "headers": [{"name": "Accept", "value": "application/json"}],
                            "queryString": [],
                            "cookies": [],
                            "headersSize": 100,
                            "bodySize": 0,
                        },
                        "response": {
                            "status": 200,
                            "statusText": "OK",
                            "httpVersion": "HTTP/1.1",
                            "headers": [{"name": "Content-Type", "value": "application/json"}],
                            "cookies": [],
                            "content": {
                                "size": 50,
                                "mimeType": "application/json",
                                "text": json.dumps([{"id": 1, "name": "John Doe"}]),
                            },
                            "redirectURL": "",
                            "headersSize": 100,
                            "bodySize": 50,
                        },
                        "cache": {},
                        "timings": {
                            "blocked": 0,
                            "dns": 0,
                            "connect": 0,
                            "send": 10,
                            "wait": 80,
                            "receive": 10,
                            "ssl": 0,
                        },
                    }
                ],
            }
        }
    )


class TestHARProcessingEndpoints:
    """Test HAR processing endpoints."""

    @pytest.fixture(autouse=True)
    def setup_db_override(self, db_session: Session):
        """Override the database dependency to use the test database."""

        def override_get_db():
            try:
                yield db_session
            finally:
                pass  # Don't close the session here, let the fixture handle it

        app.dependency_overrides[get_db] = override_get_db
        yield
        # Clean up the override after each test
        app.dependency_overrides.clear()

    @pytest.fixture
    def test_user_and_headers(self, db_session: Session):
        """Create a test user and return both the user object and auth headers."""
        unique_id = str(uuid.uuid4())[:8]
        user, api_key = create_user_with_api_key(
            db_session,
            f"testuser_{unique_id}",
            f"test_{unique_id}@example.com",
        )
        return user, {"X-API-Key": api_key}

    @pytest.fixture
    def auth_headers(self, test_user_and_headers):
        """Get authentication headers from the shared user."""
        _, headers = test_user_and_headers
        return headers

    @pytest.fixture
    def test_user(self, test_user_and_headers):
        """Get test user from the shared user."""
        user, _ = test_user_and_headers
        return user

    def test_process_har_file_not_found(self, auth_headers):
        """Test processing a non-existent HAR upload."""
        response = client.post("/api/har-uploads/999/process", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_processing_status_not_found(self, auth_headers):
        """Test getting status for non-existent HAR upload."""
        response = client.get("/api/har-uploads/999/status", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_artifacts_not_found(self, auth_headers):
        """Test getting artifacts for non-existent HAR upload."""
        response = client.get("/api/har-uploads/999/artifacts", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_process_har_file_with_options(
        self, auth_headers, sample_har_content, db_session, test_user
    ):
        """Test processing HAR file with custom options."""
        # First create a HAR upload
        har_upload = HARUploadService.create_har_upload(
            db_session, "test.har", sample_har_content, test_user
        )

        # Process with custom options
        processing_options = {
            "api_title": "Test API",
            "api_description": "Test API Description",
            "api_version": "1.0.0",
            "enable_ai_processing": True,
            "wiremock_stateful": True,
        }

        response = client.post(
            f"/api/har-uploads/{har_upload.id}/process",
            headers=auth_headers,
            json=processing_options,
        )

        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["upload_id"] == har_upload.id
        assert "processing started" in data["message"].lower()
        assert data["processing_status"]["status"] == "pending"
        assert data["processing_status"]["progress"] == 0
        assert data["processing_status"]["artifacts_available"] is False

    def test_process_already_processed_har(
        self, auth_headers, sample_har_content, db_session, test_user
    ):
        """Test processing a HAR file that's already been processed."""
        # Create a HAR upload with existing artifacts
        har_upload = HARUploadService.create_har_upload(
            db_session, "test.har", sample_har_content, test_user
        )

        # Simulate already processed by adding artifacts
        artifacts = {
            "openapi_specification": {"openapi": "3.0.0"},
            "wiremock_mappings": [],
            "processing_metadata": {"processed_at": "2023-01-01T00:00:00"},
        }
        HARUploadService.update_processed_artifacts(db_session, har_upload.id, test_user, artifacts)

        # Try to process again
        response = client.post(f"/api/har-uploads/{har_upload.id}/process", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "already been processed" in data["message"]
        assert data["processing_status"]["status"] == "completed"
        assert data["processing_status"]["artifacts_available"] is True

    def test_get_processing_status_completed(
        self, auth_headers, sample_har_content, db_session, test_user
    ):
        """Test getting status for a completed HAR processing."""
        # Create a HAR upload with artifacts
        har_upload = HARUploadService.create_har_upload(
            db_session, "test.har", sample_har_content, test_user
        )

        artifacts = {
            "openapi_specification": {"openapi": "3.0.0", "paths": {"/users": {}}},
            "wiremock_mappings": [{"request": {}, "response": {}}],
            "processing_metadata": {
                "processed_at": "2023-01-01T00:00:00",
                "interactions_count": 1,
                "openapi_paths_count": 1,
                "wiremock_stubs_count": 1,
            },
        }
        HARUploadService.update_processed_artifacts(db_session, har_upload.id, test_user, artifacts)

        response = client.get(f"/api/har-uploads/{har_upload.id}/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["artifacts_available"] is True
        assert data["interactions_count"] == 1
        assert data["openapi_paths_count"] == 1
        assert data["wiremock_stubs_count"] == 1

    def test_get_processing_status_pending(
        self, auth_headers, sample_har_content, db_session, test_user
    ):
        """Test getting status for a pending HAR processing."""
        # Create a HAR upload without artifacts
        har_upload = HARUploadService.create_har_upload(
            db_session, "test.har", sample_har_content, test_user
        )

        response = client.get(f"/api/har-uploads/{har_upload.id}/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["progress"] == 0
        assert data["artifacts_available"] is False

    def test_get_artifacts_success(self, auth_headers, sample_har_content, db_session, test_user):
        """Test getting artifacts for a processed HAR upload."""
        # Create a HAR upload with artifacts
        har_upload = HARUploadService.create_har_upload(
            db_session, "test.har", sample_har_content, test_user
        )

        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {"/users": {"get": {"responses": {"200": {"description": "Success"}}}}},
        }
        wiremock_mappings = [
            {
                "request": {"method": "GET", "url": "/users"},
                "response": {"status": 200, "body": "[]"},
            }
        ]

        # Use the correct structure matching HARProcessingArtifacts schema

        artifacts = {
            "openapi_specification": openapi_spec,
            "wiremock_mappings": wiremock_mappings,
            "processing_metadata": {
                "interactions_count": 1,
                "processed_interactions_count": 1,
                "openapi_paths_count": 1,
                "wiremock_stubs_count": 1,
                "processed_at": "2023-01-01T00:00:00",
                "processing_options": {},
            },
        }
        HARUploadService.update_processed_artifacts(db_session, har_upload.id, test_user, artifacts)

        response = client.get(f"/api/har-uploads/{har_upload.id}/artifacts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["upload_id"] == har_upload.id
        assert data["file_name"] == "test.har"
        assert data["artifacts"]["openapi_specification"] == openapi_spec
        assert data["artifacts"]["wiremock_mappings"] == wiremock_mappings
        assert "processing_metadata" in data["artifacts"]

    def test_get_artifacts_no_artifacts(
        self, auth_headers, sample_har_content, db_session, test_user
    ):
        """Test getting artifacts for unprocessed HAR upload."""
        # Create a HAR upload without artifacts
        har_upload = HARUploadService.create_har_upload(
            db_session, "test.har", sample_har_content, test_user
        )

        response = client.get(f"/api/har-uploads/{har_upload.id}/artifacts", headers=auth_headers)

        assert response.status_code == 404
        assert "No artifacts found" in response.json()["detail"]
        assert "Process the file first" in response.json()["detail"]

    def test_processing_options_validation(
        self, auth_headers, sample_har_content, db_session, test_user
    ):
        """Test processing options validation."""
        # Create a HAR upload
        har_upload = HARUploadService.create_har_upload(
            db_session, "test.har", sample_har_content, test_user
        )

        # Test with invalid options (too long strings)
        invalid_options = {
            "api_title": "x" * 101,  # Too long
            "api_description": "x" * 501,  # Too long
            "api_version": "x" * 21,  # Too long
        }

        response = client.post(
            f"/api/har-uploads/{har_upload.id}/process", headers=auth_headers, json=invalid_options
        )

        # Should return 422 for validation errors
        assert response.status_code == 422

    def test_unauthorized_access(self, sample_har_content, db_session, test_user):
        """Test that endpoints require authentication."""
        # Create a HAR upload
        har_upload = HARUploadService.create_har_upload(
            db_session, "test.har", sample_har_content, test_user
        )

        # Test without auth headers
        response = client.post(f"/api/har-uploads/{har_upload.id}/process")
        assert response.status_code == 401

        response = client.get(f"/api/har-uploads/{har_upload.id}/status")
        assert response.status_code == 401

        response = client.get(f"/api/har-uploads/{har_upload.id}/artifacts")
        assert response.status_code == 401
