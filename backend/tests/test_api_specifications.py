import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.api_key import create_user_with_api_key
from app.db.session import get_db
from main import app

# Create a test client that will be configured with database override
client = TestClient(app)


class TestAPISpecificationEndpoints:
    """Test API Specification CRUD endpoints."""

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
                                            "properties": {
                                                "message": {"type": "string"}
                                            },
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
    def auth_headers(self, db_session: Session):
        """Create a user and return authentication headers."""
        unique_id = str(uuid.uuid4())[:8]
        user, api_key = create_user_with_api_key(
            db_session,
            f"testuser_{unique_id}",
            f"test_{unique_id}@example.com",
        )
        return {"X-API-Key": api_key}

    @pytest.fixture
    def second_user_headers(self, db_session: Session):
        """Create a second user and return authentication headers."""
        unique_id = str(uuid.uuid4())[:8]
        user, api_key = create_user_with_api_key(
            db_session,
            f"testuser2_{unique_id}",
            f"test2_{unique_id}@example.com",
        )
        return {"X-API-Key": api_key}

    def test_create_specification_success(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test successful creation of API specification."""
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }

        response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test API"
        assert data["version_string"] == "v1.0"
        assert data["openapi_content"] == sample_openapi_spec
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data

    def test_create_specification_no_auth(self, sample_openapi_spec):
        """Test creation without authentication fails."""
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }

        response = client.post("/api/specifications", json=spec_data)
        assert response.status_code == 401

    def test_create_specification_invalid_openapi(self, auth_headers):
        """Test creation with invalid OpenAPI content fails."""
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": {
                "invalid": "content"
            },  # Missing required fields
        }

        response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )

        assert response.status_code == 422

    def test_create_specification_duplicate_name_version(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test creation with duplicate name and version fails."""
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }

        # Create first specification
        response1 = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    def test_list_specifications_empty(self, auth_headers):
        """Test listing specifications when none exist."""
        response = client.get("/api/specifications", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 10
        assert data["pages"] == 1

    def test_list_specifications_with_data(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test listing specifications with data."""
        # Create test specifications
        specs_data = [
            {
                "name": "API A",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            },
            {
                "name": "API B",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            },
            {
                "name": "API A",
                "version_string": "v2.0",
                "openapi_content": sample_openapi_spec,
            },
        ]

        for spec_data in specs_data:
            client.post(
                "/api/specifications", json=spec_data, headers=auth_headers
            )

        response = client.get("/api/specifications", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["size"] == 10

    def test_list_specifications_pagination(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test pagination in listing specifications."""
        # Create 5 test specifications
        for i in range(5):
            spec_data = {
                "name": f"API {i}",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            }
            client.post(
                "/api/specifications", json=spec_data, headers=auth_headers
            )

        # Test first page
        response = client.get(
            "/api/specifications?page=1&size=2", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2
        assert data["pages"] == 3

        # Test second page
        response = client.get(
            "/api/specifications?page=2&size=2", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 2

    def test_list_specifications_filtering(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test filtering in listing specifications."""
        # Create test specifications
        specs_data = [
            {
                "name": "User API",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            },
            {
                "name": "Product API",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            },
            {
                "name": "User API",
                "version_string": "v2.0",
                "openapi_content": sample_openapi_spec,
            },
        ]

        for spec_data in specs_data:
            client.post(
                "/api/specifications", json=spec_data, headers=auth_headers
            )

        # Filter by name
        response = client.get(
            "/api/specifications?name=User", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert all("User" in item["name"] for item in data["items"])

        # Filter by version
        response = client.get(
            "/api/specifications?version_string=v2.0", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["version_string"] == "v2.0"

    def test_list_specifications_sorting(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test sorting in listing specifications."""
        # Create test specifications with different names
        specs_data = [
            {
                "name": "Z API",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            },
            {
                "name": "A API",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            },
            {
                "name": "M API",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            },
        ]

        for spec_data in specs_data:
            client.post(
                "/api/specifications", json=spec_data, headers=auth_headers
            )

        # Sort by name ascending
        response = client.get(
            "/api/specifications?sort_by=name&sort_order=asc",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == ["A API", "M API", "Z API"]

        # Sort by name descending
        response = client.get(
            "/api/specifications?sort_by=name&sort_order=desc",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        assert names == ["Z API", "M API", "A API"]

    def test_list_specifications_user_isolation(
        self,
        db_session: Session,
        auth_headers,
        second_user_headers,
        sample_openapi_spec,
    ):
        """Test that users can only see their own specifications."""
        # Create specification for first user
        spec_data = {
            "name": "User 1 API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )

        # Create specification for second user
        spec_data = {
            "name": "User 2 API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        client.post(
            "/api/specifications", json=spec_data, headers=second_user_headers
        )

        # First user should only see their specification
        response = client.get("/api/specifications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "User 1 API"

        # Second user should only see their specification
        response = client.get(
            "/api/specifications", headers=second_user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "User 2 API"

    def test_get_specification_success(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test successful retrieval of specific specification."""
        # Create specification
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        create_response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        spec_id = create_response.json()["id"]

        # Get specification
        response = client.get(
            f"/api/specifications/{spec_id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == spec_id
        assert data["name"] == "Test API"
        assert data["version_string"] == "v1.0"
        assert data["openapi_content"] == sample_openapi_spec

    def test_get_specification_not_found(self, auth_headers):
        """Test retrieval of non-existent specification."""
        response = client.get("/api/specifications/999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_specification_user_isolation(
        self,
        db_session: Session,
        auth_headers,
        second_user_headers,
        sample_openapi_spec,
    ):
        """Test that users cannot access other users' specifications."""
        # Create specification for first user
        spec_data = {
            "name": "User 1 API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        create_response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        spec_id = create_response.json()["id"]

        # Second user tries to access first user's specification
        response = client.get(
            f"/api/specifications/{spec_id}", headers=second_user_headers
        )
        assert response.status_code == 404

    def test_update_specification_success(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test successful update of specification."""
        # Create specification
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        create_response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        spec_id = create_response.json()["id"]

        # Update specification
        update_data = {"name": "Updated API", "version_string": "v2.0"}
        response = client.put(
            f"/api/specifications/{spec_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated API"
        assert data["version_string"] == "v2.0"
        assert (
            data["openapi_content"] == sample_openapi_spec
        )  # Should remain unchanged

    def test_update_specification_partial(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test partial update of specification."""
        # Create specification
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        create_response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        spec_id = create_response.json()["id"]

        # Update only name
        update_data = {"name": "Updated API"}
        response = client.put(
            f"/api/specifications/{spec_id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated API"
        assert data["version_string"] == "v1.0"  # Should remain unchanged

    def test_update_specification_not_found(self, auth_headers):
        """Test update of non-existent specification."""
        update_data = {"name": "Updated API"}
        response = client.put(
            "/api/specifications/999", json=update_data, headers=auth_headers
        )
        assert response.status_code == 404

    def test_update_specification_duplicate_name_version(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test update that would create duplicate name/version fails."""
        # Create two specifications
        spec1_data = {
            "name": "API 1",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        spec2_data = {
            "name": "API 2",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }

        client.post(
            "/api/specifications", json=spec1_data, headers=auth_headers
        )
        create_response2 = client.post(
            "/api/specifications", json=spec2_data, headers=auth_headers
        )

        spec2_id = create_response2.json()["id"]

        # Try to update spec2 to have same name/version as spec1
        update_data = {"name": "API 1"}
        response = client.put(
            f"/api/specifications/{spec2_id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 409

    def test_update_specification_user_isolation(
        self,
        db_session: Session,
        auth_headers,
        second_user_headers,
        sample_openapi_spec,
    ):
        """Test that users cannot update other users' specifications."""
        # Create specification for first user
        spec_data = {
            "name": "User 1 API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        create_response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        spec_id = create_response.json()["id"]

        # Second user tries to update first user's specification
        update_data = {"name": "Hacked API"}
        response = client.put(
            f"/api/specifications/{spec_id}",
            json=update_data,
            headers=second_user_headers,
        )
        assert response.status_code == 404

    def test_delete_specification_success(
        self, db_session: Session, auth_headers, sample_openapi_spec
    ):
        """Test successful deletion of specification."""
        # Create specification
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        create_response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        spec_id = create_response.json()["id"]

        # Delete specification
        response = client.delete(
            f"/api/specifications/{spec_id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(
            f"/api/specifications/{spec_id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    def test_delete_specification_not_found(self, auth_headers):
        """Test deletion of non-existent specification."""
        response = client.delete(
            "/api/specifications/999", headers=auth_headers
        )
        assert response.status_code == 404

    def test_delete_specification_user_isolation(
        self,
        db_session: Session,
        auth_headers,
        second_user_headers,
        sample_openapi_spec,
    ):
        """Test that users cannot delete other users' specifications."""
        # Create specification for first user
        spec_data = {
            "name": "User 1 API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }
        create_response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        spec_id = create_response.json()["id"]

        # Second user tries to delete first user's specification
        response = client.delete(
            f"/api/specifications/{spec_id}", headers=second_user_headers
        )
        assert response.status_code == 404

        # Verify specification still exists for first user
        get_response = client.get(
            f"/api/specifications/{spec_id}", headers=auth_headers
        )
        assert get_response.status_code == 200

    def test_all_endpoints_require_authentication(self, sample_openapi_spec):
        """Test that all endpoints require authentication."""
        # Test create
        response = client.post(
            "/api/specifications",
            json={
                "name": "Test",
                "version_string": "v1.0",
                "openapi_content": sample_openapi_spec,
            },
        )
        assert response.status_code == 401

        # Test list
        response = client.get("/api/specifications")
        assert response.status_code == 401

        # Test get
        response = client.get("/api/specifications/1")
        assert response.status_code == 401

        # Test update
        response = client.put(
            "/api/specifications/1", json={"name": "Updated"}
        )
        assert response.status_code == 401

        # Test delete
        response = client.delete("/api/specifications/1")
        assert response.status_code == 401

    def test_invalid_query_parameters(self, auth_headers):
        """Test handling of invalid query parameters."""
        # Invalid sort_by
        response = client.get(
            "/api/specifications?sort_by=invalid_field", headers=auth_headers
        )
        assert response.status_code == 422

        # Invalid sort_order
        response = client.get(
            "/api/specifications?sort_order=invalid_order",
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Invalid page
        response = client.get(
            "/api/specifications?page=0", headers=auth_headers
        )
        assert response.status_code == 422

        # Invalid size
        response = client.get(
            "/api/specifications?size=0", headers=auth_headers
        )
        assert response.status_code == 422

        # Size too large
        response = client.get(
            "/api/specifications?size=101", headers=auth_headers
        )
        assert response.status_code == 422
