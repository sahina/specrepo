import json
import os
import tempfile
from unittest.mock import AsyncMock

import pytest

from app.services.har_parser import APIInteraction, APIRequest, APIResponse
from app.services.har_to_wiremock import HARToWireMockService, HARToWireMockTransformer


class TestHARToWireMockTransformer:
    """Test cases for HARToWireMockTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create a transformer instance for testing."""
        return HARToWireMockTransformer()

    @pytest.fixture
    def sample_request(self):
        """Create a sample API request."""
        return APIRequest(
            method="GET",
            url="https://api.example.com/users/123",
            domain="api.example.com",
            path="/users/123",
            query_params={"include": ["profile"]},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            body=None,
            content_type="application/json",
            timestamp="2023-01-01T12:00:00Z",
        )

    @pytest.fixture
    def sample_response(self):
        """Create a sample API response."""
        return APIResponse(
            status=200,
            status_text="OK",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
            body='{"id": 123, "name": "John Doe", "email": "john@example.com"}',
            content_type="application/json",
            size=1024,
        )

    @pytest.fixture
    def sample_interaction(self, sample_request, sample_response):
        """Create a sample API interaction."""
        return APIInteraction(
            request=sample_request, response=sample_response, duration=150.5, entry_id="entry_1"
        )

    def test_transform_single_interaction(self, transformer, sample_interaction):
        """Test transforming a single HAR interaction."""
        stubs = transformer.transform_interactions([sample_interaction])

        assert len(stubs) == 1
        stub = stubs[0]

        # Check request configuration
        assert stub.request["method"] == "GET"
        assert stub.request["urlPattern"] == "/users/\\d+"
        assert "queryParameters" in stub.request
        assert stub.request["queryParameters"]["include"]["equalTo"] == "profile"

        # Check response configuration
        assert stub.response["status"] == 200
        assert "Content-Type" in stub.response["headers"]

        # Check that templating was applied (email should be templated)
        response_body = json.loads(stub.response["body"])
        assert response_body["email"] == "{{randomValue type='EMAIL'}}"
        assert response_body["name"] == "John Doe"  # Static field unchanged

        # Check metadata
        assert stub.metadata["source"] == "har_transformation"
        assert stub.metadata["entry_id"] == "entry_1"

    def test_transform_empty_interactions(self, transformer):
        """Test transforming empty interactions list."""
        stubs = transformer.transform_interactions([])
        assert stubs == []

    def test_normalize_path_with_numeric_id(self, transformer):
        """Test path normalization with numeric IDs."""
        path = "/users/123/posts/456"
        normalized = transformer._normalize_path(path)
        assert normalized == "/users/{id}/posts/{id}"

    def test_normalize_path_with_uuid(self, transformer):
        """Test path normalization with UUIDs."""
        path = "/users/550e8400-e29b-41d4-a716-446655440000/profile"
        normalized = transformer._normalize_path(path)
        assert normalized == "/users/{uuid}/profile"

    def test_has_dynamic_segments(self, transformer):
        """Test detection of dynamic path segments."""
        assert transformer._has_dynamic_segments("/users/123")
        assert transformer._has_dynamic_segments("/users/550e8400-e29b-41d4-a716-446655440000")
        assert not transformer._has_dynamic_segments("/users/profile")

    def test_create_url_pattern(self, transformer):
        """Test URL pattern creation."""
        pattern = transformer._create_url_pattern("/users/123/posts/456")
        assert pattern == "/users/\\d+/posts/\\d+"

    def test_group_by_endpoint(self, transformer, sample_interaction):
        """Test grouping interactions by endpoint."""
        # Create multiple interactions for same endpoint
        interaction1 = sample_interaction
        interaction2 = APIInteraction(
            request=APIRequest(
                method="GET",
                url="https://api.example.com/users/456",
                domain="api.example.com",
                path="/users/456",
                query_params={},
                headers={"Content-Type": "application/json"},
                body=None,
                content_type="application/json",
                timestamp="2023-01-01T12:01:00Z",
            ),
            response=sample_interaction.response,
            duration=120.0,
            entry_id="entry_2",
        )

        groups = transformer._group_by_endpoint([interaction1, interaction2])
        assert len(groups) == 1
        assert "GET:/users/{id}" in groups
        assert len(groups["GET:/users/{id}"]) == 2

    def test_create_stateful_stubs(self, transformer, sample_interaction):
        """Test creation of stateful stubs."""
        # Create multiple interactions for stateful behavior
        interactions = [sample_interaction]
        for i in range(2, 4):
            interaction = APIInteraction(
                request=APIRequest(
                    method="GET",
                    url=f"https://api.example.com/users/{i}",
                    domain="api.example.com",
                    path=f"/users/{i}",
                    query_params={},
                    headers={"Content-Type": "application/json"},
                    body=None,
                    content_type="application/json",
                    timestamp=f"2023-01-01T12:0{i}:00Z",
                ),
                response=sample_interaction.response,
                duration=120.0,
                entry_id=f"entry_{i}",
            )
            interactions.append(interaction)

        stubs = transformer._create_stateful_stubs(interactions)
        assert len(stubs) == 3

        # Check scenario configuration
        scenario_name = stubs[0].request["scenario"]
        assert all(stub.request["scenario"] == scenario_name for stub in stubs)

        # Check state transitions
        assert "requiredScenarioState" not in stubs[0].request
        assert stubs[0].response["newScenarioState"] == "state_1"
        assert stubs[1].request["requiredScenarioState"] == "state_1"
        assert stubs[1].response["newScenarioState"] == "state_2"
        assert stubs[2].request["requiredScenarioState"] == "state_2"
        assert "newScenarioState" not in stubs[2].response

    def test_create_body_matcher_json(self, transformer):
        """Test JSON body matcher creation."""
        body = '{"name": "test", "value": 123}'
        content_type = "application/json"

        matcher = transformer._create_body_matcher(body, content_type)
        assert "bodyPatterns" in matcher
        assert matcher["bodyPatterns"][0]["equalToJson"] == body
        assert matcher["bodyPatterns"][0]["ignoreArrayOrder"] is True

    def test_create_body_matcher_text(self, transformer):
        """Test text body matcher creation."""
        body = "plain text body"
        content_type = "text/plain"

        matcher = transformer._create_body_matcher(body, content_type)
        assert "bodyPatterns" in matcher
        assert matcher["bodyPatterns"][0]["equalTo"] == body

    def test_create_templated_response(self, transformer):
        """Test templated response creation."""
        body = (
            '{"id": 123, "uuid": "550e8400-e29b-41d4-a716-446655440000", '
            '"email": "test@example.com", "created_at": "2023-01-01T12:00:00Z"}'
        )

        templated = transformer._create_templated_response(body)
        assert templated is not None

        templated_data = json.loads(templated)
        # The 'id' field should remain unchanged since it's numeric, not string
        # Only string fields matching patterns get templated
        assert templated_data["id"] == 123  # Numeric ID stays unchanged
        assert templated_data["uuid"] == "{{randomValue type='UUID'}}"
        assert templated_data["email"] == "{{randomValue type='EMAIL'}}"
        assert templated_data["created_at"] == "{{now}}"

    def test_create_templated_response_string_ids(self, transformer):
        """Test templated response creation with string IDs."""
        body = '{"id": "abc123", "user_id": 456, "profile_id": "def789"}'

        templated = transformer._create_templated_response(body)
        assert templated is not None

        templated_data = json.loads(templated)
        # String ID should be templated as UUID
        assert templated_data["id"] == "{{randomValue type='UUID'}}"
        # Numeric _id field should be templated as numeric
        assert templated_data["user_id"] == "{{randomValue type='NUMERIC' length=8}}"
        # String _id field should be templated as numeric
        assert templated_data["profile_id"] == "{{randomValue type='NUMERIC' length=8}}"

    def test_strict_matching_mode(self):
        """Test strict matching mode."""
        transformer = HARToWireMockTransformer(strict_matching=True)

        request = APIRequest(
            method="POST",
            url="https://api.example.com/users",
            domain="api.example.com",
            path="/users",
            query_params={},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer token123",
                "X-Custom-Header": "custom-value",
            },
            body='{"name": "test"}',
            content_type="application/json",
            timestamp="2023-01-01T12:00:00Z",
        )

        config = transformer._create_request_matcher(request)

        # Should include custom headers in strict mode
        assert "headers" in config
        assert "X-Custom-Header" in config["headers"]
        # But should exclude authorization header
        assert "Authorization" not in config["headers"]

    def test_export_to_files(self, transformer, sample_interaction):
        """Test exporting stubs to files."""
        stubs = transformer.transform_interactions([sample_interaction])

        with tempfile.TemporaryDirectory() as temp_dir:
            created_files = transformer.export_to_files(stubs, temp_dir)

            assert len(created_files) == 1
            assert os.path.exists(created_files[0])

            # Check file content
            with open(created_files[0], "r") as f:
                content = json.load(f)

            assert "request" in content
            assert "response" in content
            assert "metadata" in content

    def test_base_url_stripping(self, transformer, sample_interaction):
        """Test base URL stripping from requests."""
        base_url = "https://api.example.com"
        stubs = transformer.transform_interactions([sample_interaction], base_url)

        stub = stubs[0]
        # URL pattern should not include the base URL
        assert stub.request["urlPattern"] == "/users/\\d+"


class TestHARToWireMockService:
    """Test cases for HARToWireMockService."""

    @pytest.fixture
    def mock_wiremock_client(self):
        """Create a mock WireMock client."""
        client = AsyncMock()
        client.create_stub = AsyncMock(return_value={"id": "stub_123"})
        client.clear_stubs = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def service(self, mock_wiremock_client):
        """Create a service instance for testing."""
        return HARToWireMockService(wiremock_client=mock_wiremock_client)

    @pytest.fixture
    def sample_interaction(self):
        """Create a sample API interaction."""
        request = APIRequest(
            method="GET",
            url="https://api.example.com/users/123",
            domain="api.example.com",
            path="/users/123",
            query_params={},
            headers={"Content-Type": "application/json"},
            body=None,
            content_type="application/json",
            timestamp="2023-01-01T12:00:00Z",
        )

        response = APIResponse(
            status=200,
            status_text="OK",
            headers={"Content-Type": "application/json"},
            body='{"id": 123, "name": "John Doe"}',
            content_type="application/json",
            size=1024,
        )

        return APIInteraction(
            request=request, response=response, duration=150.5, entry_id="entry_1"
        )

    @pytest.mark.asyncio
    async def test_transform_and_deploy_success(
        self, service, sample_interaction, mock_wiremock_client
    ):
        """Test successful transformation and deployment."""
        result = await service.transform_and_deploy([sample_interaction])

        assert result["success"] is True
        assert result["stubs_created"] == 1
        assert result["stubs_deployed"] == 1
        assert len(result["errors"]) == 0

        # Verify WireMock client was called
        mock_wiremock_client.create_stub.assert_called_once()

    @pytest.mark.asyncio
    async def test_transform_and_deploy_with_clear(
        self, service, sample_interaction, mock_wiremock_client
    ):
        """Test transformation and deployment with clearing existing stubs."""
        result = await service.transform_and_deploy([sample_interaction], clear_existing=True)

        assert result["success"] is True
        mock_wiremock_client.clear_stubs.assert_called_once()
        mock_wiremock_client.create_stub.assert_called_once()

    @pytest.mark.asyncio
    async def test_transform_and_deploy_no_client(self):
        """Test transformation without WireMock client."""
        service = HARToWireMockService()

        with pytest.raises(ValueError, match="WireMock client not configured"):
            await service.transform_and_deploy([])

    @pytest.mark.asyncio
    async def test_transform_and_deploy_empty_interactions(self, service):
        """Test transformation with empty interactions."""
        result = await service.transform_and_deploy([])

        assert result["success"] is True
        assert result["stubs_created"] == 0
        assert result["stubs_deployed"] == 0

    @pytest.mark.asyncio
    async def test_transform_and_deploy_with_errors(
        self, service, sample_interaction, mock_wiremock_client
    ):
        """Test transformation with deployment errors."""
        mock_wiremock_client.create_stub.side_effect = Exception("Deployment failed")

        result = await service.transform_and_deploy([sample_interaction])

        assert result["success"] is False
        assert result["stubs_created"] == 1
        assert result["stubs_deployed"] == 0
        assert len(result["errors"]) == 1

    def test_transform_to_files(self, service, sample_interaction):
        """Test transformation to files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = service.transform_to_files([sample_interaction], temp_dir)

            assert result["success"] is True
            assert result["stubs_created"] == 1
            assert len(result["files_created"]) == 1
            assert result["output_directory"] == temp_dir

    def test_transform_to_files_empty_interactions(self, service):
        """Test transformation to files with empty interactions."""
        result = service.transform_to_files([])

        assert result["success"] is True
        assert result["stubs_created"] == 0
        assert len(result["files_created"]) == 0


class TestIntegration:
    """Integration tests for HAR to WireMock transformation."""

    def test_end_to_end_transformation(self):
        """Test complete end-to-end transformation process."""
        # Create sample HAR-like data
        request = APIRequest(
            method="POST",
            url="https://api.example.com/users",
            domain="api.example.com",
            path="/users",
            query_params={"format": ["json"]},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer token123",
            },
            body='{"name": "John Doe", "email": "john@example.com"}',
            content_type="application/json",
            timestamp="2023-01-01T12:00:00Z",
        )

        response = APIResponse(
            status=201,
            status_text="Created",
            headers={"Content-Type": "application/json", "Location": "/users/123"},
            body=(
                '{"id": 123, "name": "John Doe", "email": "john@example.com", '
                '"created_at": "2023-01-01T12:00:00Z"}'
            ),
            content_type="application/json",
            size=2048,
        )

        interaction = APIInteraction(
            request=request, response=response, duration=250.0, entry_id="entry_1"
        )

        # Transform with different configurations
        transformer = HARToWireMockTransformer(
            enable_stateful=True, enable_templating=True, strict_matching=False
        )

        stubs = transformer.transform_interactions([interaction])

        assert len(stubs) == 1
        stub = stubs[0]

        # Verify request matching
        assert stub.request["method"] == "POST"
        assert stub.request["url"] == "/users"
        assert "queryParameters" in stub.request
        assert stub.request["queryParameters"]["format"]["equalTo"] == "json"

        # Verify essential headers are included, but not authorization
        assert "Content-Type" in stub.request["headers"]
        assert "Authorization" not in stub.request["headers"]

        # Verify body matching
        assert "bodyPatterns" in stub.request
        assert stub.request["bodyPatterns"][0]["equalToJson"] == request.body

        # Verify response configuration
        assert stub.response["status"] == 201
        assert "Content-Type" in stub.response["headers"]
        assert "Location" in stub.response["headers"]

        # Verify templated response (should contain templates for dynamic fields)
        response_body = json.loads(stub.response["body"])
        assert response_body["id"] == 123  # Numeric ID stays unchanged
        assert response_body["created_at"] == "{{now}}"
        assert response_body["name"] == "John Doe"  # Static field unchanged

    def test_multiple_endpoints_stateful(self):
        """Test stateful behavior with multiple related endpoints."""
        # Create login interaction
        login_request = APIRequest(
            method="POST",
            url="https://api.example.com/auth/login",
            domain="api.example.com",
            path="/auth/login",
            query_params={},
            headers={"Content-Type": "application/json"},
            body='{"username": "user", "password": "pass"}',
            content_type="application/json",
            timestamp="2023-01-01T12:00:00Z",
        )

        login_response = APIResponse(
            status=200,
            status_text="OK",
            headers={"Content-Type": "application/json"},
            body='{"token": "abc123", "expires_in": 3600}',
            content_type="application/json",
            size=512,
        )

        login_interaction = APIInteraction(
            request=login_request, response=login_response, duration=100.0, entry_id="login_1"
        )

        # Create profile fetch interaction
        profile_request = APIRequest(
            method="GET",
            url="https://api.example.com/user/profile",
            domain="api.example.com",
            path="/user/profile",
            query_params={},
            headers={"Content-Type": "application/json", "Authorization": "Bearer abc123"},
            body=None,
            content_type=None,
            timestamp="2023-01-01T12:01:00Z",
        )

        profile_response = APIResponse(
            status=200,
            status_text="OK",
            headers={"Content-Type": "application/json"},
            body='{"id": 1, "username": "user", "email": "user@example.com"}',
            content_type="application/json",
            size=1024,
        )

        profile_interaction = APIInteraction(
            request=profile_request, response=profile_response, duration=50.0, entry_id="profile_1"
        )

        transformer = HARToWireMockTransformer(enable_stateful=True)
        stubs = transformer.transform_interactions([login_interaction, profile_interaction])

        # Should create separate stubs for different endpoints
        assert len(stubs) == 2

        # Each should have different scenarios or no scenario (since they're different endpoints)
        login_stub = next(s for s in stubs if s.request["method"] == "POST")
        profile_stub = next(s for s in stubs if s.request["method"] == "GET")

        assert login_stub.request["url"] == "/auth/login"
        assert profile_stub.request["url"] == "/user/profile"
