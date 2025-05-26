import json
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pytest

from app.services.wiremock_integration import (
    OpenAPIEndpoint,
    OpenAPIParser,
    WireMockClient,
    WireMockIntegrationService,
    WireMockStub,
    WireMockStubGenerator,
)


class TestOpenAPIParser:
    """Test cases for OpenAPI parsing functionality."""

    def test_parse_json_specification(self):
        """Test parsing JSON OpenAPI specification."""
        json_spec = """
        {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        """

        result = OpenAPIParser.parse_specification(json_spec)

        assert result["openapi"] == "3.0.0"
        assert result["info"]["title"] == "Test API"
        assert "/users" in result["paths"]

    def test_parse_yaml_specification(self):
        """Test parsing YAML OpenAPI specification."""
        yaml_spec = """
        openapi: 3.0.0
        info:
          title: Test API
          version: 1.0.0
        paths:
          /users:
            get:
              summary: Get users
              responses:
                '200':
                  description: Success
        """

        result = OpenAPIParser.parse_specification(yaml_spec)

        assert result["openapi"] == "3.0.0"
        assert result["info"]["title"] == "Test API"
        assert "/users" in result["paths"]

    def test_parse_dict_specification(self):
        """Test parsing dict OpenAPI specification."""
        dict_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        result = OpenAPIParser.parse_specification(dict_spec)

        assert result == dict_spec

    def test_parse_invalid_specification(self):
        """Test parsing invalid specification raises ValueError."""
        invalid_spec = "{ invalid json: [ unclosed"

        with pytest.raises(
            ValueError, match="Failed to parse OpenAPI specification"
        ):
            OpenAPIParser.parse_specification(invalid_spec)

    def test_extract_endpoints_basic(self):
        """Test extracting basic endpoints from OpenAPI specification."""
        openapi_spec = {
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "summary": "Get all users",
                        "responses": {"200": {"description": "Success"}},
                    },
                    "post": {
                        "operationId": "createUser",
                        "summary": "Create user",
                        "responses": {"201": {"description": "Created"}},
                    },
                },
                "/users/{id}": {
                    "get": {
                        "operationId": "getUser",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {"200": {"description": "Success"}},
                    }
                },
            }
        }

        endpoints = OpenAPIParser.extract_endpoints(openapi_spec)

        assert len(endpoints) == 3

        # Check GET /users
        get_users = next(
            e for e in endpoints if e.path == "/users" and e.method == "GET"
        )
        assert get_users.operation_id == "getUsers"
        assert get_users.summary == "Get all users"

        # Check POST /users
        post_users = next(
            e for e in endpoints if e.path == "/users" and e.method == "POST"
        )
        assert post_users.operation_id == "createUser"
        assert post_users.summary == "Create user"

        # Check GET /users/{id}
        get_user = next(e for e in endpoints if e.path == "/users/{id}")
        assert get_user.operation_id == "getUser"
        assert len(get_user.parameters) == 1
        assert get_user.parameters[0]["name"] == "id"

    def test_extract_endpoints_with_path_parameters(self):
        """Test extracting endpoints with path-level parameters."""
        openapi_spec = {
            "paths": {
                "/users/{id}": {
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "get": {
                        "parameters": [
                            {
                                "name": "include",
                                "in": "query",
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "Success"}},
                    },
                }
            }
        }

        endpoints = OpenAPIParser.extract_endpoints(openapi_spec)

        assert len(endpoints) == 1
        endpoint = endpoints[0]
        assert len(endpoint.parameters) == 2  # path + query parameter

        path_param = next(p for p in endpoint.parameters if p["in"] == "path")
        query_param = next(
            p for p in endpoint.parameters if p["in"] == "query"
        )

        assert path_param["name"] == "id"
        assert query_param["name"] == "include"

    def test_get_example_from_schema_basic_types(self):
        """Test getting examples from basic schema types."""
        # String
        string_schema = {"type": "string", "example": "test_value"}
        assert (
            OpenAPIParser.get_example_from_schema(string_schema)
            == "test_value"
        )

        # Integer
        int_schema = {"type": "integer"}
        assert OpenAPIParser.get_example_from_schema(int_schema) == 123

        # Number
        number_schema = {"type": "number"}
        assert OpenAPIParser.get_example_from_schema(number_schema) == 123.45

        # Boolean
        bool_schema = {"type": "boolean"}
        assert OpenAPIParser.get_example_from_schema(bool_schema) is True

    def test_get_example_from_schema_complex_types(self):
        """Test getting examples from complex schema types."""
        # Array
        array_schema = {"type": "array", "items": {"type": "string"}}
        result = OpenAPIParser.get_example_from_schema(array_schema)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "example_string"

        # Object
        object_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        result = OpenAPIParser.get_example_from_schema(object_schema)
        assert isinstance(result, dict)
        assert result["name"] == "example_string"
        assert result["age"] == 123

    def test_get_example_from_schema_with_examples(self):
        """Test getting examples when examples array is provided."""
        schema = {
            "type": "string",
            "examples": {
                "example1": {"value": "first_example"},
                "example2": {"value": "second_example"},
            },
        }
        result = OpenAPIParser.get_example_from_schema(schema)
        assert result in ["first_example", "second_example"]


class TestWireMockStubGenerator:
    """Test cases for WireMock stub generation."""

    def test_generate_basic_stub(self):
        """Test generating a basic WireMock stub."""
        endpoint = OpenAPIEndpoint(
            path="/users",
            method="GET",
            operation_id="getUsers",
            summary="Get all users",
            responses={
                "200": {
                    "description": "Success",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                    },
                                },
                            }
                        }
                    },
                }
            },
        )

        stub = WireMockStubGenerator.generate_stub(endpoint)

        assert stub.request["method"] == "GET"
        assert stub.request["urlPattern"] == "/users"
        assert stub.response["status"] == 200
        assert "application/json" in stub.response["headers"]["Content-Type"]
        assert stub.metadata["operationId"] == "getUsers"

    def test_generate_stub_with_path_parameters(self):
        """Test generating stub with path parameters."""
        endpoint = OpenAPIEndpoint(
            path="/users/{id}",
            method="GET",
            parameters=[
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            responses={"200": {"description": "Success"}},
        )

        stub = WireMockStubGenerator.generate_stub(endpoint)

        assert stub.request["urlPattern"] == "/users/([0-9]+)"

    def test_generate_stub_with_query_parameters(self):
        """Test generating stub with query parameters."""
        endpoint = OpenAPIEndpoint(
            path="/users",
            method="GET",
            parameters=[
                {
                    "name": "limit",
                    "in": "query",
                    "schema": {"type": "integer", "example": 10},
                },
                {
                    "name": "search",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                },
            ],
            responses={"200": {"description": "Success"}},
        )

        stub = WireMockStubGenerator.generate_stub(endpoint)

        assert "queryParameters" in stub.request
        assert stub.request["queryParameters"]["limit"]["equalTo"] == "10"
        assert (
            stub.request["queryParameters"]["search"]["equalTo"]
            == "example_string"
        )

    def test_generate_stub_with_request_body(self):
        """Test generating stub with request body."""
        endpoint = OpenAPIEndpoint(
            path="/users",
            method="POST",
            request_body={
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "example": "John Doe",
                                },
                                "email": {
                                    "type": "string",
                                    "example": "john@example.com",
                                },
                            },
                        }
                    }
                }
            },
            responses={"201": {"description": "Created"}},
        )

        stub = WireMockStubGenerator.generate_stub(endpoint)

        assert "bodyPatterns" in stub.request
        body_pattern = stub.request["bodyPatterns"][0]
        assert "equalToJson" in body_pattern

        expected_body = {"name": "John Doe", "email": "john@example.com"}
        assert json.loads(body_pattern["equalToJson"]) == expected_body

    def test_build_url_pattern_with_different_param_types(self):
        """Test URL pattern building with different parameter types."""
        # Integer parameter
        int_params = [
            {"name": "id", "in": "path", "schema": {"type": "integer"}}
        ]
        pattern = WireMockStubGenerator._build_url_pattern(
            "/users/{id}", int_params
        )
        assert pattern == "/users/([0-9]+)"

        # Number parameter
        number_params = [
            {"name": "score", "in": "path", "schema": {"type": "number"}}
        ]
        pattern = WireMockStubGenerator._build_url_pattern(
            "/scores/{score}", number_params
        )
        assert pattern == r"/scores/([0-9]+\.?[0-9]*)"

        # String parameter (default)
        string_params = [
            {"name": "name", "in": "path", "schema": {"type": "string"}}
        ]
        pattern = WireMockStubGenerator._build_url_pattern(
            "/users/{name}", string_params
        )
        assert pattern == "/users/([^/]+)"


class TestWireMockClient:
    """Test cases for WireMock client functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = WireMockClient("http://test-wiremock:8080")

    def test_create_stub(self):
        """Test creating a stub via WireMock API."""

        async def _test():
            stub = WireMockStub(
                request={"method": "GET", "urlPattern": "/test"},
                response={"status": 200, "body": "test response"},
            )

            mock_response = MagicMock()
            mock_response.json.return_value = {"id": "test-stub-id"}
            mock_response.raise_for_status.return_value = None

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = (
                    AsyncMock(return_value=mock_response)
                )

                result = await self.client.create_stub(stub)

                assert result["id"] == "test-stub-id"
                mock_client.return_value.__aenter__.return_value.post.assert_called_once()

        anyio.run(_test)

    def test_get_stubs(self):
        """Test getting all stubs from WireMock."""

        async def _test():
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "mappings": [
                    {"id": "stub1", "request": {}, "response": {}},
                    {"id": "stub2", "request": {}, "response": {}},
                ]
            }
            mock_response.raise_for_status.return_value = None

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = (
                    AsyncMock(return_value=mock_response)
                )

                result = await self.client.get_stubs()

                assert len(result) == 2
                assert result[0]["id"] == "stub1"
                assert result[1]["id"] == "stub2"

        anyio.run(_test)

    def test_clear_stubs(self):
        """Test clearing all stubs."""

        async def _test():
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.delete = (
                    AsyncMock(return_value=mock_response)
                )

                result = await self.client.clear_stubs()

                assert result is True
                mock_client.return_value.__aenter__.return_value.delete.assert_called_once_with(
                    "http://test-wiremock:8080/__admin/mappings"
                )

        anyio.run(_test)

    def test_reset_stubs(self):
        """Test resetting WireMock."""

        async def _test():
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = (
                    AsyncMock(return_value=mock_response)
                )

                result = await self.client.reset_stubs()

                assert result is True
                mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
                    "http://test-wiremock:8080/__admin/reset"
                )

        anyio.run(_test)


class TestWireMockIntegrationService:
    """Test cases for the main WireMock integration service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = WireMockIntegrationService("http://test-wiremock:8080")

    def test_generate_stubs_from_openapi(self):
        """Test generating stubs from OpenAPI specification."""

        async def _test():
            openapi_content = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {
                    "/users": {
                        "get": {
                            "operationId": "getUsers",
                            "responses": {
                                "200": {
                                    "description": "Success",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "array",
                                                "items": {"type": "object"},
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    },
                    "/users/{id}": {
                        "get": {
                            "operationId": "getUser",
                            "parameters": [
                                {
                                    "name": "id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "integer"},
                                }
                            ],
                            "responses": {"200": {"description": "Success"}},
                        }
                    },
                },
            }

            # Mock the WireMock client
            mock_create_responses = [
                {"id": "stub1", "request": {}, "response": {}},
                {"id": "stub2", "request": {}, "response": {}},
            ]

            with patch.object(
                self.service.client, "create_stub"
            ) as mock_create:
                mock_create.side_effect = mock_create_responses

                result = await self.service.generate_stubs_from_openapi(
                    openapi_content
                )

                assert len(result) == 2
                assert result[0]["id"] == "stub1"
                assert result[1]["id"] == "stub2"
                assert mock_create.call_count == 2

        anyio.run(_test)

    def test_generate_stubs_with_clear_existing(self):
        """Test generating stubs with clearing existing ones first."""

        async def _test():
            openapi_content = {
                "openapi": "3.0.0",
                "paths": {
                    "/test": {
                        "get": {
                            "responses": {"200": {"description": "Success"}}
                        }
                    }
                },
            }

            with (
                patch.object(self.service.client, "clear_stubs") as mock_clear,
                patch.object(
                    self.service.client, "create_stub"
                ) as mock_create,
            ):
                mock_create.return_value = {"id": "test-stub"}

                await self.service.generate_stubs_from_openapi(
                    openapi_content, clear_existing=True
                )

                mock_clear.assert_called_once()
                mock_create.assert_called_once()

        anyio.run(_test)

    def test_generate_stubs_handles_errors(self):
        """Test that stub generation handles individual endpoint errors "
        "gracefully."""

        async def _test():
            openapi_content = {
                "openapi": "3.0.0",
                "paths": {
                    "/working": {
                        "get": {
                            "responses": {"200": {"description": "Success"}}
                        }
                    },
                    "/failing": {
                        "get": {
                            "responses": {"200": {"description": "Success"}}
                        }
                    },
                },
            }

            def mock_create_stub(stub):
                if "working" in str(stub.request):
                    return {"id": "working-stub"}
                else:
                    raise Exception("Stub creation failed")

            with patch.object(
                self.service.client,
                "create_stub",
                side_effect=mock_create_stub,
            ):
                result = await self.service.generate_stubs_from_openapi(
                    openapi_content
                )

                # Should return only the successful stub
                assert len(result) == 1
                assert result[0]["id"] == "working-stub"

        anyio.run(_test)

    def test_get_all_stubs(self):
        """Test getting all stubs."""

        async def _test():
            mock_stubs = [
                {"id": "stub1", "request": {}, "response": {}},
                {"id": "stub2", "request": {}, "response": {}},
            ]

            with patch.object(
                self.service.client, "get_stubs", return_value=mock_stubs
            ):
                result = await self.service.get_all_stubs()

                assert result == mock_stubs

        anyio.run(_test)

    def test_clear_all_stubs(self):
        """Test clearing all stubs."""

        async def _test():
            with patch.object(
                self.service.client, "clear_stubs", return_value=True
            ):
                result = await self.service.clear_all_stubs()

                assert result is True

        anyio.run(_test)

    def test_reset_wiremock(self):
        """Test resetting WireMock."""

        async def _test():
            with patch.object(
                self.service.client, "reset_stubs", return_value=True
            ):
                result = await self.service.reset_wiremock()

                assert result is True

        anyio.run(_test)
