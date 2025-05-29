import json
import uuid
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.api_key import create_user_with_api_key
from app.db.session import get_db
from app.models import HARUpload, User
from main import app

# Create a test client that will be configured with database override
client = TestClient(app)


class TestHARUploads:
    """Test class for HAR upload endpoints."""

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
    def test_user(self, db_session: Session):
        """Create a test user and return the user object."""
        unique_id = str(uuid.uuid4())[:8]
        user, api_key = create_user_with_api_key(
            db_session,
            f"testuser_{unique_id}",
            f"test_{unique_id}@example.com",
        )
        user.plain_api_key = api_key  # Store plain text API key for testing
        return user

    @pytest.fixture
    def test_user_2(self, db_session: Session):
        """Create a second test user and return the user object."""
        unique_id = str(uuid.uuid4())[:8]
        user, api_key = create_user_with_api_key(
            db_session,
            f"testuser2_{unique_id}",
            f"test2_{unique_id}@example.com",
        )
        user.plain_api_key = api_key  # Store plain text API key for testing
        return user

    @pytest.fixture
    def sample_har_content(self):
        """Sample valid HAR content for testing."""
        return {
            "log": {
                "version": "1.2",
                "creator": {"name": "Test", "version": "1.0"},
                "entries": [
                    {
                        "startedDateTime": "2023-01-01T00:00:00.000Z",
                        "time": 100,
                        "request": {
                            "method": "GET",
                            "url": "https://api.example.com/users",
                            "httpVersion": "HTTP/1.1",
                            "headers": [],
                            "queryString": [],
                            "cookies": [],
                            "headersSize": -1,
                            "bodySize": 0,
                        },
                        "response": {
                            "status": 200,
                            "statusText": "OK",
                            "httpVersion": "HTTP/1.1",
                            "headers": [],
                            "cookies": [],
                            "content": {"size": 0, "mimeType": "application/json"},
                            "redirectURL": "",
                            "headersSize": -1,
                            "bodySize": 0,
                        },
                        "cache": {},
                        "timings": {"send": 0, "wait": 100, "receive": 0},
                    }
                ],
            }
        }

    @pytest.fixture
    def invalid_har_content(self):
        """Invalid HAR content for testing."""
        return {"invalid": "structure"}

    def test_upload_har_file_success(self, test_user: User, sample_har_content: dict):
        """Test successful HAR file upload."""
        har_json = json.dumps(sample_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["file_name"] == "test.har"
        assert data["user_id"] == test_user.id
        assert "uploaded_at" in data

    def test_upload_har_file_invalid_format(self, test_user: User, invalid_har_content: dict):
        """Test HAR file upload with invalid format."""
        har_json = json.dumps(invalid_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 400
        assert "Invalid HAR file format" in response.json()["detail"]

    def test_upload_har_file_invalid_extension(self, test_user: User, sample_har_content: dict):
        """Test HAR file upload with invalid file extension."""
        har_json = json.dumps(sample_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        response = client.post(
            "/api/har-uploads",
            files={"file": ("test.txt", file_content, "text/plain")},
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 400
        assert "File type not allowed" in response.json()["detail"]

    def test_upload_har_file_too_large(self, test_user: User):
        """Test HAR file upload that exceeds size limit."""
        # Create a large file (simulate 51MB)
        large_content = "x" * (51 * 1024 * 1024)
        file_content = BytesIO(large_content.encode("utf-8"))

        response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    def test_upload_har_file_invalid_encoding(self, test_user: User):
        """Test HAR file upload with invalid encoding."""
        # Create invalid UTF-8 content
        invalid_content = b"\xff\xfe\x00\x00"
        file_content = BytesIO(invalid_content)

        response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 400
        assert "File must be UTF-8 encoded" in response.json()["detail"]

    def test_upload_har_file_no_authentication(self, sample_har_content: dict):
        """Test HAR file upload without authentication."""
        har_json = json.dumps(sample_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
        )

        assert response.status_code == 401

    def test_list_har_uploads_empty(self, test_user: User):
        """Test listing HAR uploads when none exist."""
        response = client.get("/api/har-uploads", headers={"X-API-Key": test_user.plain_api_key})

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 10

    def test_list_har_uploads_with_data(self, test_user: User, sample_har_content: dict):
        """Test listing HAR uploads with existing data."""
        # Upload a HAR file first
        har_json = json.dumps(sample_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        upload_response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )
        assert upload_response.status_code == 201

        # List uploads
        response = client.get("/api/har-uploads", headers={"X-API-Key": test_user.plain_api_key})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["file_name"] == "test.har"

    def test_list_har_uploads_with_filtering(self, test_user: User, sample_har_content: dict):
        """Test listing HAR uploads with file name filtering."""
        # Upload multiple HAR files
        for i, filename in enumerate(["test1.har", "test2.har", "other.har"]):
            har_json = json.dumps(sample_har_content)
            file_content = BytesIO(har_json.encode("utf-8"))

            response = client.post(
                "/api/har-uploads",
                files={"file": (filename, file_content, "application/json")},
                headers={"X-API-Key": test_user.plain_api_key},
            )
            assert response.status_code == 201

        # Filter by file name
        response = client.get(
            "/api/har-uploads?file_name=test",
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all("test" in item["file_name"] for item in data["items"])

    def test_list_har_uploads_with_sorting(self, test_user: User, sample_har_content: dict):
        """Test listing HAR uploads with sorting."""
        # Upload multiple HAR files
        for filename in ["b.har", "a.har", "c.har"]:
            har_json = json.dumps(sample_har_content)
            file_content = BytesIO(har_json.encode("utf-8"))

            response = client.post(
                "/api/har-uploads",
                files={"file": (filename, file_content, "application/json")},
                headers={"X-API-Key": test_user.plain_api_key},
            )
            assert response.status_code == 201

        # Sort by file name ascending
        response = client.get(
            "/api/har-uploads?sort_by=file_name&sort_order=asc",
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        filenames = [item["file_name"] for item in data["items"]]
        assert filenames == ["a.har", "b.har", "c.har"]

    def test_list_har_uploads_pagination(self, test_user: User, sample_har_content: dict):
        """Test HAR uploads list pagination."""
        # Upload multiple HAR files
        for i in range(15):
            har_json = json.dumps(sample_har_content)
            file_content = BytesIO(har_json.encode("utf-8"))

            response = client.post(
                "/api/har-uploads",
                files={"file": (f"test{i}.har", file_content, "application/json")},
                headers={"X-API-Key": test_user.plain_api_key},
            )
            assert response.status_code == 201

        # Test first page
        response = client.get(
            "/api/har-uploads?page=1&size=10",
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15
        assert data["page"] == 1
        assert data["pages"] == 2

        # Test second page
        response = client.get(
            "/api/har-uploads?page=2&size=10",
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["page"] == 2

    def test_list_har_uploads_no_authentication(self):
        """Test listing HAR uploads without authentication."""
        response = client.get("/api/har-uploads")
        assert response.status_code == 401

    def test_get_har_upload_success(self, test_user: User, sample_har_content: dict):
        """Test getting a specific HAR upload."""
        # Upload a HAR file first
        har_json = json.dumps(sample_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        upload_response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )
        assert upload_response.status_code == 201
        upload_id = upload_response.json()["id"]

        # Get the upload
        response = client.get(
            f"/api/har-uploads/{upload_id}",
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == upload_id
        assert data["file_name"] == "test.har"
        assert data["user_id"] == test_user.id

    def test_get_har_upload_not_found(self, test_user: User):
        """Test getting a non-existent HAR upload."""
        response = client.get(
            "/api/har-uploads/999", headers={"X-API-Key": test_user.plain_api_key}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_har_upload_user_isolation(
        self, test_user: User, test_user_2: User, sample_har_content: dict
    ):
        """Test that users can only access their own HAR uploads."""
        # Upload HAR file as user 1
        har_json = json.dumps(sample_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        upload_response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )
        assert upload_response.status_code == 201
        upload_id = upload_response.json()["id"]

        # Try to access as user 2
        response = client.get(
            f"/api/har-uploads/{upload_id}",
            headers={"X-API-Key": test_user_2.plain_api_key},
        )

        assert response.status_code == 404

    def test_get_har_upload_no_authentication(self):
        """Test getting HAR upload without authentication."""
        response = client.get("/api/har-uploads/1")
        assert response.status_code == 401

    def test_delete_har_upload_success(self, test_user: User, sample_har_content: dict):
        """Test deleting a HAR upload."""
        # Upload a HAR file first
        har_json = json.dumps(sample_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        upload_response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )
        assert upload_response.status_code == 201
        upload_id = upload_response.json()["id"]

        # Delete the upload
        response = client.delete(
            f"/api/har-uploads/{upload_id}",
            headers={"X-API-Key": test_user.plain_api_key},
        )

        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(
            f"/api/har-uploads/{upload_id}",
            headers={"X-API-Key": test_user.plain_api_key},
        )
        assert get_response.status_code == 404

    def test_delete_har_upload_not_found(self, test_user: User):
        """Test deleting a non-existent HAR upload."""
        response = client.delete(
            "/api/har-uploads/999", headers={"X-API-Key": test_user.plain_api_key}
        )

        assert response.status_code == 404

    def test_delete_har_upload_user_isolation(
        self, test_user: User, test_user_2: User, sample_har_content: dict
    ):
        """Test that users can only delete their own HAR uploads."""
        # Upload HAR file as user 1
        har_json = json.dumps(sample_har_content)
        file_content = BytesIO(har_json.encode("utf-8"))

        upload_response = client.post(
            "/api/har-uploads",
            files={"file": ("test.har", file_content, "application/json")},
            headers={"X-API-Key": test_user.plain_api_key},
        )
        assert upload_response.status_code == 201
        upload_id = upload_response.json()["id"]

        # Try to delete as user 2
        response = client.delete(
            f"/api/har-uploads/{upload_id}",
            headers={"X-API-Key": test_user_2.plain_api_key},
        )

        assert response.status_code == 404

    def test_delete_har_upload_no_authentication(self):
        """Test deleting HAR upload without authentication."""
        response = client.delete("/api/har-uploads/1")
        assert response.status_code == 401

    def test_har_upload_service_validation(
        self, sample_har_content: dict, invalid_har_content: dict
    ):
        """Test HAR content validation in service layer."""
        from app.services.har_uploads import HARUploadService

        # Test valid content
        valid_content = json.dumps(sample_har_content)
        assert HARUploadService.validate_har_content(valid_content) is True

        # Test invalid content
        invalid_content = json.dumps(invalid_har_content)
        assert HARUploadService.validate_har_content(invalid_content) is False

        # Test malformed JSON
        assert HARUploadService.validate_har_content("invalid json") is False

    def test_har_upload_database_operations(
        self, db_session: Session, test_user: User, sample_har_content: dict
    ):
        """Test HAR upload database operations."""
        from app.schemas import HARUploadFilters
        from app.services.har_uploads import HARUploadService

        # Test create
        har_content = json.dumps(sample_har_content)
        upload = HARUploadService.create_har_upload(db_session, "test.har", har_content, test_user)
        assert upload.id is not None
        assert upload.file_name == "test.har"
        assert upload.user_id == test_user.id

        # Test get by ID
        retrieved = HARUploadService.get_har_upload(db_session, upload.id, test_user)
        assert retrieved is not None
        assert retrieved.id == upload.id

        # Test list with filters
        filters = HARUploadFilters()
        uploads, total = HARUploadService.get_har_uploads(db_session, test_user, filters)
        assert total == 1
        assert len(uploads) == 1

        # Test update artifacts
        artifacts = {"processed": True, "artifacts": ["spec1", "mock1"]}
        updated = HARUploadService.update_processed_artifacts(
            db_session, upload.id, test_user, artifacts
        )
        assert updated is not None
        assert updated.processed_artifacts_references == artifacts

        # Test delete
        deleted = HARUploadService.delete_har_upload(db_session, upload.id, test_user)
        assert deleted is True

        # Verify deletion
        retrieved = HARUploadService.get_har_upload(db_session, upload.id, test_user)
        assert retrieved is None
