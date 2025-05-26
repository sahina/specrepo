import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.api_key import create_user_with_api_key
from app.db.session import get_db
from app.models import MockConfiguration
from main import app

# Create a test client that will be configured with database override
client = TestClient(app)


class TestMocksEndpoints:
    """Test cases for mock management endpoints."""

    @pytest.fixture(autouse=True)
    def setup_db_override(self, db_session: Session):
        """Override the database dependency to use the test database."""

        def override_get_db():
            try:
                yield db_session
            finally:
                pass  # Don't close the session here, let the fixture handle it

        app.dependency_overrides[get_db] = override_get_db

        # Clean up any existing mock configurations before each test
        db_session.query(MockConfiguration).delete()
        db_session.commit()

        yield

        # Clean up after each test
        db_session.query(MockConfiguration).delete()
        db_session.commit()
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
    def test_api_specification(
        self,
        db_session: Session,
        auth_headers: dict,
        sample_openapi_spec: dict,
    ):
        """Create a test API specification."""
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": sample_openapi_spec,
        }

        response = client.post(
            "/api/specifications", json=spec_data, headers=auth_headers
        )
        assert response.status_code == 201
        return response.json()

    def test_deploy_mock_success(
        self,
        db_session: Session,
        test_api_specification: dict,
        auth_headers: dict,
    ):
        """Test successful mock deployment."""
        with patch(
            "app.routers.mocks.WireMockIntegrationService"
        ) as mock_wiremock_service:
            # Mock WireMock service
            mock_service_instance = AsyncMock()
            mock_wiremock_service.return_value = mock_service_instance
            mock_service_instance.generate_stubs_from_openapi.return_value = [
                {"id": "stub1", "request": {}, "response": {}},
                {"id": "stub2", "request": {}, "response": {}},
            ]

            # Make request
            response = client.post(
                "/api/mocks/deploy",
                json={
                    "specification_id": test_api_specification["id"],
                    "clear_existing": True,
                },
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert "Successfully deployed" in data["message"]
            assert data["stubs_created"] == 2
            assert data["status"] == "active"
            assert "configuration_id" in data

            # Verify mock configuration was created in database
            mock_config = (
                db_session.query(MockConfiguration)
                .filter(
                    MockConfiguration.api_specification_id
                    == test_api_specification["id"]
                )
                .first()
            )
            assert mock_config is not None
            assert mock_config.status == "active"
            assert len(mock_config.wiremock_mapping_json["stubs"]) == 2

    def test_deploy_mock_specification_not_found(self, auth_headers: dict):
        """Test mock deployment with non-existent specification."""
        response = client.post(
            "/api/mocks/deploy",
            json={"specification_id": 99999, "clear_existing": False},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_deploy_mock_wiremock_failure(
        self,
        test_api_specification: dict,
        auth_headers: dict,
    ):
        """Test mock deployment when WireMock service fails."""
        with patch(
            "app.routers.mocks.WireMockIntegrationService"
        ) as mock_wiremock_service:
            # Mock WireMock service to raise exception
            mock_service_instance = AsyncMock()
            mock_wiremock_service.return_value = mock_service_instance
            mock_service_instance.generate_stubs_from_openapi.side_effect = (
                Exception("WireMock connection failed")
            )

            response = client.post(
                "/api/mocks/deploy",
                json={
                    "specification_id": test_api_specification["id"],
                    "clear_existing": False,
                },
                headers=auth_headers,
            )

            assert response.status_code == 502
            assert "WireMock deployment failed" in response.json()["detail"]

    def test_reset_mocks_success(
        self,
        db_session: Session,
        test_api_specification: dict,
        auth_headers: dict,
    ):
        """Test successful mock reset."""
        # Create some mock configurations
        mock_config1 = MockConfiguration(
            api_specification_id=test_api_specification["id"],
            wiremock_mapping_json={"stubs": []},
            status="active",
        )
        mock_config2 = MockConfiguration(
            api_specification_id=test_api_specification["id"],
            wiremock_mapping_json={"stubs": []},
            status="active",
        )
        db_session.add(mock_config1)
        db_session.add(mock_config2)
        db_session.commit()

        with patch(
            "app.routers.mocks.WireMockIntegrationService"
        ) as mock_wiremock_service:
            # Mock WireMock service
            mock_service_instance = AsyncMock()
            mock_wiremock_service.return_value = mock_service_instance
            mock_service_instance.reset_wiremock.return_value = True

            response = client.delete("/api/mocks/reset", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "Successfully reset" in data["message"]
            assert data["configurations_reset"] == 2
            assert data["wiremock_reset"] is True

            # Verify configurations were marked as inactive
            db_session.refresh(mock_config1)
            db_session.refresh(mock_config2)
            assert mock_config1.status == "inactive"
            assert mock_config2.status == "inactive"

    def test_reset_mocks_wiremock_failure(
        self,
        db_session: Session,
        test_api_specification: dict,
        auth_headers: dict,
    ):
        """Test mock reset when WireMock service fails."""
        # Create a mock configuration
        mock_config = MockConfiguration(
            api_specification_id=test_api_specification["id"],
            wiremock_mapping_json={"stubs": []},
            status="active",
        )
        db_session.add(mock_config)
        db_session.commit()

        with patch(
            "app.routers.mocks.WireMockIntegrationService"
        ) as mock_wiremock_service:
            # Mock WireMock service to raise exception
            mock_service_instance = AsyncMock()
            mock_wiremock_service.return_value = mock_service_instance
            mock_service_instance.reset_wiremock.side_effect = Exception(
                "WireMock connection failed"
            )

            response = client.delete("/api/mocks/reset", headers=auth_headers)

            assert response.status_code == 502
            assert "WireMock reset failed" in response.json()["detail"]

    def test_get_mock_status_success(
        self,
        db_session: Session,
        test_api_specification: dict,
        auth_headers: dict,
    ):
        """Test successful mock status retrieval."""
        # Create mock configurations
        mock_config1 = MockConfiguration(
            api_specification_id=test_api_specification["id"],
            wiremock_mapping_json={
                "stubs": [{"id": "stub1"}, {"id": "stub2"}],
                "specification_name": "Test API",
                "specification_version": "1.0.0",
            },
            status="active",
        )
        mock_config2 = MockConfiguration(
            api_specification_id=test_api_specification["id"],
            wiremock_mapping_json={
                "stubs": [{"id": "stub3"}],
                "specification_name": "Test API",
                "specification_version": "1.1.0",
            },
            status="inactive",
        )
        db_session.add(mock_config1)
        db_session.add(mock_config2)
        db_session.commit()

        response = client.get("/api/mocks/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_configurations"] == 1  # Only active ones
        assert data["active_configurations"] == 1
        assert len(data["configurations"]) == 1

        config_data = data["configurations"][0]
        assert config_data["status"] == "active"
        assert config_data["stubs_count"] == 2
        assert config_data["specification_name"] == "Test API"

    def test_get_mock_status_empty(self, auth_headers: dict):
        """Test mock status retrieval with no configurations."""
        response = client.get("/api/mocks/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_configurations"] == 0
        assert data["active_configurations"] == 0
        assert data["configurations"] == []

    def test_deploy_mock_unauthorized(self):
        """Test mock deployment without authentication."""
        response = client.post(
            "/api/mocks/deploy",
            json={"specification_id": 1, "clear_existing": False},
        )

        assert response.status_code == 401

    def test_reset_mocks_unauthorized(self):
        """Test mock reset without authentication."""
        response = client.delete("/api/mocks/reset")

        assert response.status_code == 401

    def test_get_mock_status_unauthorized(self):
        """Test mock status retrieval without authentication."""
        response = client.get("/api/mocks/status")

        assert response.status_code == 401

    def test_deploy_mock_database_failure(
        self,
        test_api_specification: dict,
        auth_headers: dict,
    ):
        """Test mock deployment when database storage fails."""
        with (
            patch(
                "app.routers.mocks.WireMockIntegrationService"
            ) as mock_wiremock_service,
            patch(
                "app.routers.mocks.MockConfigurationService"
            ) as mock_config_service,
        ):
            # Mock WireMock service success
            mock_service_instance = AsyncMock()
            mock_wiremock_service.return_value = mock_service_instance
            mock_service_instance.generate_stubs_from_openapi.return_value = [
                {"id": "stub1"}
            ]
            mock_service_instance.clear_all_stubs.return_value = True

            # Mock database service failure
            mock_config_service.create_mock_configuration.side_effect = (
                Exception("Database error")
            )

            response = client.post(
                "/api/mocks/deploy",
                json={
                    "specification_id": test_api_specification["id"],
                    "clear_existing": False,
                },
                headers=auth_headers,
            )

            assert response.status_code == 500
            assert (
                "Failed to store deployment status"
                in response.json()["detail"]
            )

            # Verify cleanup was attempted
            mock_service_instance.clear_all_stubs.assert_called_once()

    def test_deploy_mock_invalid_request(self, auth_headers: dict):
        """Test mock deployment with invalid request data."""
        response = client.post(
            "/api/mocks/deploy",
            json={"invalid_field": "value"},
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error
