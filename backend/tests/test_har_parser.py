import json
from unittest.mock import patch

import pytest

from app.services.har_parser import APIInteraction, APIRequest, APIResponse, HARParser


class TestHARParser:
    """Test class for HAR parser functionality."""

    @pytest.fixture
    def har_parser(self):
        """Create a HAR parser instance for testing."""
        return HARParser()

    @pytest.fixture
    def sample_har_data(self):
        """Sample HAR data for testing."""
        return {
            "log": {
                "version": "1.2",
                "creator": {"name": "Test", "version": "1.0"},
                "entries": [
                    {
                        "startedDateTime": "2023-01-01T12:00:00.000Z",
                        "time": 150.5,
                        "request": {
                            "method": "GET",
                            "url": "https://api.example.com/v1/users/123",
                            "httpVersion": "HTTP/1.1",
                            "headers": [
                                {"name": "Content-Type", "value": "application/json"},
                                {"name": "Authorization", "value": "Bearer token123"},
                            ],
                            "queryString": [{"name": "include", "value": "profile"}],
                            "cookies": [],
                            "headersSize": 150,
                            "bodySize": 0,
                        },
                        "response": {
                            "status": 200,
                            "statusText": "OK",
                            "httpVersion": "HTTP/1.1",
                            "headers": [
                                {
                                    "name": "Content-Type",
                                    "value": "application/json; charset=utf-8",
                                },
                                {"name": "Cache-Control", "value": "no-cache"},
                            ],
                            "cookies": [],
                            "content": {
                                "size": 256,
                                "mimeType": "application/json",
                                "text": (
                                    '{"id": 123, "name": "John Doe", "email": "john@example.com"}'
                                ),
                            },
                            "redirectURL": "",
                            "headersSize": 200,
                            "bodySize": 256,
                        },
                        "cache": {},
                        "timings": {"wait": 50, "receive": 100},
                    },
                    {
                        "startedDateTime": "2023-01-01T12:01:00.000Z",
                        "time": 75.2,
                        "request": {
                            "method": "POST",
                            "url": "https://api.example.com/v1/users",
                            "httpVersion": "HTTP/1.1",
                            "headers": [{"name": "Content-Type", "value": "application/json"}],
                            "queryString": [],
                            "cookies": [],
                            "headersSize": 100,
                            "bodySize": 85,
                            "postData": {
                                "mimeType": "application/json",
                                "text": '{"name": "Jane Doe", "email": "jane@example.com"}',
                            },
                        },
                        "response": {
                            "status": 201,
                            "statusText": "Created",
                            "httpVersion": "HTTP/1.1",
                            "headers": [{"name": "Content-Type", "value": "application/json"}],
                            "cookies": [],
                            "content": {
                                "size": 128,
                                "mimeType": "application/json",
                                "text": (
                                    '{"id": 124, "name": "Jane Doe", "email": "jane@example.com"}'
                                ),
                            },
                            "redirectURL": "",
                            "headersSize": 150,
                            "bodySize": 128,
                        },
                        "cache": {},
                        "timings": {"wait": 25, "receive": 50},
                    },
                    {
                        "startedDateTime": "2023-01-01T12:02:00.000Z",
                        "time": 25.0,
                        "request": {
                            "method": "GET",
                            "url": "https://example.com/static/style.css",
                            "httpVersion": "HTTP/1.1",
                            "headers": [{"name": "Accept", "value": "text/css"}],
                            "queryString": [],
                            "cookies": [],
                            "headersSize": 80,
                            "bodySize": 0,
                        },
                        "response": {
                            "status": 200,
                            "statusText": "OK",
                            "httpVersion": "HTTP/1.1",
                            "headers": [{"name": "Content-Type", "value": "text/css"}],
                            "cookies": [],
                            "content": {
                                "size": 1024,
                                "mimeType": "text/css",
                                "text": "body { margin: 0; }",
                            },
                            "redirectURL": "",
                            "headersSize": 100,
                            "bodySize": 1024,
                        },
                        "cache": {},
                        "timings": {"wait": 10, "receive": 15},
                    },
                ],
            }
        }

    @pytest.fixture
    def sample_har_content(self, sample_har_data):
        """Sample HAR content as JSON string."""
        return json.dumps(sample_har_data)

    def test_parse_har_content_success(self, har_parser, sample_har_content):
        """Test successful HAR content parsing."""
        interactions = har_parser.parse_har_content(sample_har_content)

        # Should extract 2 API interactions (excluding CSS file)
        assert len(interactions) == 2

        # Check first interaction (GET /users/123)
        first_interaction = interactions[0]
        assert first_interaction.request.method == "GET"
        assert first_interaction.request.url == "https://api.example.com/v1/users/123"
        assert first_interaction.request.domain == "api.example.com"
        assert first_interaction.request.path == "/v1/users/123"
        assert first_interaction.response.status == 200
        assert first_interaction.duration == 150.5

        # Check second interaction (POST /users)
        second_interaction = interactions[1]
        assert second_interaction.request.method == "POST"
        assert second_interaction.request.url == "https://api.example.com/v1/users"
        assert (
            second_interaction.request.body == '{"name": "Jane Doe", "email": "jane@example.com"}'
        )
        assert second_interaction.response.status == 201

    def test_parse_har_content_invalid_json(self, har_parser):
        """Test parsing with invalid JSON content."""
        with pytest.raises(json.JSONDecodeError):
            har_parser.parse_har_content("invalid json content")

    def test_parse_har_content_missing_log(self, har_parser):
        """Test parsing with missing log structure."""
        invalid_har = json.dumps({"invalid": "structure"})
        with pytest.raises(ValueError, match="Invalid HAR structure"):
            har_parser.parse_har_content(invalid_har)

    def test_parse_har_content_missing_entries(self, har_parser):
        """Test parsing with missing entries."""
        invalid_har = json.dumps({"log": {"version": "1.2"}})
        with pytest.raises(ValueError, match="Invalid HAR structure"):
            har_parser.parse_har_content(invalid_har)

    def test_is_api_request_api_url_pattern(self, har_parser):
        """Test API request detection based on URL patterns."""
        # API-like URLs
        api_entry = {
            "request": {"method": "GET", "url": "https://example.com/api/users", "headers": []},
            "response": {"status": 200, "headers": [], "content": {}},
        }
        assert har_parser._is_api_request(api_entry) is True

        versioned_entry = {
            "request": {"method": "GET", "url": "https://example.com/v1/products", "headers": []},
            "response": {"status": 200, "headers": [], "content": {}},
        }
        assert har_parser._is_api_request(versioned_entry) is True

    def test_is_api_request_non_api_patterns(self, har_parser):
        """Test API request detection filtering out non-API patterns."""
        # Static file URLs
        css_entry = {
            "request": {"method": "GET", "url": "https://example.com/style.css", "headers": []},
            "response": {"status": 200, "headers": [], "content": {}},
        }
        assert har_parser._is_api_request(css_entry) is False

        js_entry = {
            "request": {"method": "GET", "url": "https://example.com/app.js", "headers": []},
            "response": {"status": 200, "headers": [], "content": {}},
        }
        assert har_parser._is_api_request(js_entry) is False

        image_entry = {
            "request": {"method": "GET", "url": "https://example.com/logo.png", "headers": []},
            "response": {"status": 200, "headers": [], "content": {}},
        }
        assert har_parser._is_api_request(image_entry) is False

    def test_is_api_request_content_type(self, har_parser):
        """Test API request detection based on content types."""
        json_entry = {
            "request": {
                "method": "POST",
                "url": "https://example.com/submit",
                "headers": [{"name": "Content-Type", "value": "application/json"}],
            },
            "response": {"status": 200, "headers": [], "content": {}},
        }
        assert har_parser._is_api_request(json_entry) is True

        xml_entry = {
            "request": {
                "method": "POST",
                "url": "https://example.com/soap",
                "headers": [{"name": "Content-Type", "value": "application/xml"}],
            },
            "response": {"status": 200, "headers": [], "content": {}},
        }
        assert har_parser._is_api_request(xml_entry) is True

    def test_is_api_request_json_response(self, har_parser):
        """Test API request detection based on JSON response."""
        json_response_entry = {
            "request": {"method": "GET", "url": "https://example.com/data", "headers": []},
            "response": {
                "status": 200,
                "headers": [],
                "content": {"mimeType": "application/json", "text": '{"data": "value"}'},
            },
        }
        assert har_parser._is_api_request(json_response_entry) is True

    def test_parse_request(self, har_parser):
        """Test request parsing functionality."""
        request_data = {
            "method": "POST",
            "url": "https://api.example.com/v1/users?include=profile&sort=name",
            "headers": [
                {"name": "Content-Type", "value": "application/json"},
                {"name": "Authorization", "value": "Bearer token123"},
            ],
            "postData": {"text": '{"name": "John Doe"}'},
        }

        request = har_parser._parse_request(request_data, "2023-01-01T12:00:00.000Z")

        assert request.method == "POST"
        assert request.url == "https://api.example.com/v1/users?include=profile&sort=name"
        assert request.domain == "api.example.com"
        assert request.path == "/v1/users"
        assert request.query_params == {"include": ["profile"], "sort": ["name"]}
        assert request.headers["content-type"] == "application/json"
        assert request.headers["authorization"] == "Bearer token123"
        assert request.body == '{"name": "John Doe"}'
        assert request.content_type == "application/json"
        assert request.timestamp == "2023-01-01T12:00:00.000Z"

    def test_parse_response(self, har_parser):
        """Test response parsing functionality."""
        response_data = {
            "status": 201,
            "statusText": "Created",
            "headers": [
                {"name": "Content-Type", "value": "application/json; charset=utf-8"},
                {"name": "Location", "value": "/users/123"},
            ],
            "content": {"text": '{"id": 123, "name": "John Doe"}'},
            "bodySize": 256,
        }

        response = har_parser._parse_response(response_data)

        assert response.status == 201
        assert response.status_text == "Created"
        assert response.headers["content-type"] == "application/json; charset=utf-8"
        assert response.headers["location"] == "/users/123"
        assert response.body == '{"id": 123, "name": "John Doe"}'
        assert response.content_type == "application/json"
        assert response.size == 256

    def test_parse_response_unknown_size(self, har_parser):
        """Test response parsing with unknown body size."""
        response_data = {
            "status": 200,
            "statusText": "OK",
            "headers": [],
            "content": {"text": "Hello World"},
            "bodySize": -1,  # Unknown size
        }

        response = har_parser._parse_response(response_data)
        assert response.size == 11  # Length of "Hello World"

    def test_extract_base_path(self, har_parser):
        """Test base path extraction functionality."""
        # Test numeric ID replacement
        assert har_parser._extract_base_path("/api/users/123") == "/api/users/{id}"
        assert (
            har_parser._extract_base_path("/api/orders/456/items/789")
            == "/api/orders/{id}/items/{id}"
        )

        # Test UUID replacement
        uuid_path = "/api/users/550e8400-e29b-41d4-a716-446655440000"
        assert har_parser._extract_base_path(uuid_path) == "/api/users/{uuid}"

        # Test alphanumeric ID replacement
        assert har_parser._extract_base_path("/api/users/abc123def456") == "/api/users/{id}"

        # Test collection endpoints (now normalized to include {id})
        assert har_parser._extract_base_path("/api/users") == "/api/users/{id}"
        assert har_parser._extract_base_path("/v1/products") == "/v1/products/{id}"

        # Test non-collection endpoints
        assert har_parser._extract_base_path("/v1/products/search") == "/v1/products/search"
        assert har_parser._extract_base_path("/api/auth/login") == "/api/auth/login"

        # Test empty/root paths
        assert har_parser._extract_base_path("") == "/"
        assert har_parser._extract_base_path("/") == "/"

    def test_group_endpoints(self, har_parser, sample_har_content):
        """Test endpoint grouping functionality."""
        interactions = har_parser.parse_har_content(sample_har_content)
        groups = har_parser.group_endpoints(interactions)

        # Should have one group for api.example.com
        assert len(groups) == 1

        group = groups[0]
        assert group.domain == "api.example.com"
        assert group.base_path == "/v1/users/{id}"  # Both /users/123 and /users should normalize
        assert len(group.interactions) == 2
        assert "GET" in group.methods
        assert "POST" in group.methods
        assert "application/json" in group.content_types

    def test_filter_interactions_by_domain(self, har_parser, sample_har_content):
        """Test filtering interactions by domain."""
        interactions = har_parser.parse_har_content(sample_har_content)

        # Filter by existing domain
        filtered = har_parser.filter_interactions(interactions, domains=["api.example.com"])
        assert len(filtered) == 2

        # Filter by non-existing domain
        filtered = har_parser.filter_interactions(interactions, domains=["other.com"])
        assert len(filtered) == 0

    def test_filter_interactions_by_method(self, har_parser, sample_har_content):
        """Test filtering interactions by HTTP method."""
        interactions = har_parser.parse_har_content(sample_har_content)

        # Filter by GET method
        filtered = har_parser.filter_interactions(interactions, methods=["GET"])
        assert len(filtered) == 1
        assert filtered[0].request.method == "GET"

        # Filter by POST method
        filtered = har_parser.filter_interactions(interactions, methods=["POST"])
        assert len(filtered) == 1
        assert filtered[0].request.method == "POST"

    def test_filter_interactions_by_status_code(self, har_parser, sample_har_content):
        """Test filtering interactions by status code."""
        interactions = har_parser.parse_har_content(sample_har_content)

        # Filter by 200 status
        filtered = har_parser.filter_interactions(interactions, status_codes=[200])
        assert len(filtered) == 1
        assert filtered[0].response.status == 200

        # Filter by 201 status
        filtered = har_parser.filter_interactions(interactions, status_codes=[201])
        assert len(filtered) == 1
        assert filtered[0].response.status == 201

    def test_filter_interactions_by_content_type(self, har_parser, sample_har_content):
        """Test filtering interactions by content type."""
        interactions = har_parser.parse_har_content(sample_har_content)

        # Filter by JSON content type
        filtered = har_parser.filter_interactions(interactions, content_types=["application/json"])
        assert len(filtered) == 2  # Both interactions have JSON content type

    def test_get_summary_stats(self, har_parser, sample_har_content):
        """Test summary statistics generation."""
        interactions = har_parser.parse_har_content(sample_har_content)
        stats = har_parser.get_summary_stats(interactions)

        assert stats["total_interactions"] == 2
        assert stats["unique_domains"] == 1
        assert stats["unique_paths"] == 2
        assert stats["methods"]["GET"] == 1
        assert stats["methods"]["POST"] == 1
        assert stats["status_codes"][200] == 1
        assert stats["status_codes"][201] == 1
        assert "application/json" in stats["content_types"]
        assert stats["avg_duration"] == (150.5 + 75.2) / 2
        assert stats["total_response_size"] == 256 + 128

    def test_get_summary_stats_empty(self, har_parser):
        """Test summary statistics with empty interactions list."""
        stats = har_parser.get_summary_stats([])

        assert stats["total_interactions"] == 0
        assert stats["unique_domains"] == 0
        assert stats["unique_paths"] == 0
        assert stats["methods"] == {}
        assert stats["status_codes"] == {}
        assert stats["content_types"] == []
        assert stats["avg_duration"] == 0
        assert stats["total_response_size"] == 0

    def test_parse_headers(self, har_parser):
        """Test header parsing functionality."""
        headers_list = [
            {"name": "Content-Type", "value": "application/json"},
            {"name": "Authorization", "value": "Bearer token123"},
            {"name": "X-Custom-Header", "value": "custom-value"},
        ]

        headers = har_parser._parse_headers(headers_list)

        assert headers["content-type"] == "application/json"
        assert headers["authorization"] == "Bearer token123"
        assert headers["x-custom-header"] == "custom-value"

    def test_get_content_type(self, har_parser):
        """Test content type extraction."""
        headers_list = [
            {"name": "Content-Type", "value": "application/json; charset=utf-8"},
            {"name": "Authorization", "value": "Bearer token123"},
        ]

        content_type = har_parser._get_content_type(headers_list)
        assert content_type == "application/json"

    def test_get_content_type_not_found(self, har_parser):
        """Test content type extraction when not present."""
        headers_list = [{"name": "Authorization", "value": "Bearer token123"}]

        content_type = har_parser._get_content_type(headers_list)
        assert content_type is None

    @patch("app.services.har_parser.logger")
    def test_error_handling_in_parse_entry(self, mock_logger, har_parser):
        """Test error handling during entry parsing."""
        # Invalid entry structure
        invalid_entry = {"invalid": "structure"}

        result = har_parser._parse_entry(invalid_entry, "test_id")
        assert result is None
        mock_logger.warning.assert_called()

    @patch("app.services.har_parser.logger")
    def test_error_handling_in_is_api_request(self, mock_logger, har_parser):
        """Test error handling in API request detection."""
        # Entry that will cause an exception
        problematic_entry = None

        result = har_parser._is_api_request(problematic_entry)
        assert result is False
        mock_logger.warning.assert_called()

    def test_complex_endpoint_grouping(self, har_parser):
        """Test endpoint grouping with complex scenarios."""
        # Create interactions with different domains and paths
        interactions = [
            APIInteraction(
                request=APIRequest(
                    method="GET",
                    url="https://api1.com/v1/users/123",
                    domain="api1.com",
                    path="/v1/users/123",
                    query_params={},
                    headers={},
                    body=None,
                    content_type="application/json",
                    timestamp="2023-01-01T12:00:00.000Z",
                ),
                response=APIResponse(
                    status=200,
                    status_text="OK",
                    headers={},
                    body=None,
                    content_type="application/json",
                    size=100,
                ),
                duration=100.0,
                entry_id="1",
            ),
            APIInteraction(
                request=APIRequest(
                    method="POST",
                    url="https://api1.com/v1/users",
                    domain="api1.com",
                    path="/v1/users",
                    query_params={},
                    headers={},
                    body=None,
                    content_type="application/json",
                    timestamp="2023-01-01T12:01:00.000Z",
                ),
                response=APIResponse(
                    status=201,
                    status_text="Created",
                    headers={},
                    body=None,
                    content_type="application/json",
                    size=150,
                ),
                duration=75.0,
                entry_id="2",
            ),
            APIInteraction(
                request=APIRequest(
                    method="GET",
                    url="https://api2.com/v2/products/456",
                    domain="api2.com",
                    path="/v2/products/456",
                    query_params={},
                    headers={},
                    body=None,
                    content_type="application/json",
                    timestamp="2023-01-01T12:02:00.000Z",
                ),
                response=APIResponse(
                    status=200,
                    status_text="OK",
                    headers={},
                    body=None,
                    content_type="application/json",
                    size=200,
                ),
                duration=50.0,
                entry_id="3",
            ),
        ]

        groups = har_parser.group_endpoints(interactions)

        # Should have 2 groups (different domains)
        assert len(groups) == 2

        # Check first group (api1.com)
        api1_group = next(g for g in groups if g.domain == "api1.com")
        assert api1_group.base_path == "/v1/users/{id}"  # Both paths should normalize to this
        assert len(api1_group.interactions) == 2
        assert "GET" in api1_group.methods
        assert "POST" in api1_group.methods

        # Check second group (api2.com)
        api2_group = next(g for g in groups if g.domain == "api2.com")
        assert api2_group.base_path == "/v2/products/{id}"
        assert len(api2_group.interactions) == 1
        assert "GET" in api2_group.methods
