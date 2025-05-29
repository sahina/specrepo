import json
from unittest.mock import patch

import pytest

from app.services.har_parser import APIInteraction, APIRequest, APIResponse, EndpointGroup
from app.services.har_to_openapi import HARToOpenAPITransformer


class TestHARToOpenAPITransformer:
    """Test suite for HAR to OpenAPI transformation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = HARToOpenAPITransformer()

    def create_sample_interaction(
        self,
        method="GET",
        url="https://api.example.com/users/123",
        status=200,
        request_body=None,
        response_body='{"id": 123, "name": "John Doe"}',
        query_params=None,
    ):
        """Create a sample API interaction for testing."""
        if query_params is None:
            query_params = {}

        request = APIRequest(
            method=method,
            url=url,
            domain="api.example.com",
            path="/users/123",
            query_params=query_params,
            headers={"Content-Type": "application/json"},
            body=request_body,
            content_type="application/json" if request_body else None,
            timestamp="2023-01-01T00:00:00Z",
        )

        response = APIResponse(
            status=status,
            status_text="OK" if status == 200 else "Error",
            headers={"Content-Type": "application/json"},
            body=response_body,
            content_type="application/json",
            size=len(response_body) if response_body else 0,
        )

        return APIInteraction(request=request, response=response, duration=100.0, entry_id="1")

    def create_sample_har_content(self):
        """Create sample HAR content for testing."""
        return json.dumps(
            {
                "log": {
                    "entries": [
                        {
                            "request": {
                                "method": "GET",
                                "url": "https://api.example.com/users/123",
                                "headers": [{"name": "Content-Type", "value": "application/json"}],
                                "queryString": [],
                                "postData": None,
                            },
                            "response": {
                                "status": 200,
                                "statusText": "OK",
                                "headers": [{"name": "Content-Type", "value": "application/json"}],
                                "content": {
                                    "text": (
                                        '{"id": 123, "name": "John Doe", '
                                        '"email": "john@example.com"}'
                                    )
                                },
                            },
                            "time": 100,
                            "startedDateTime": "2023-01-01T00:00:00Z",
                        },
                        {
                            "request": {
                                "method": "POST",
                                "url": "https://api.example.com/users",
                                "headers": [{"name": "Content-Type", "value": "application/json"}],
                                "queryString": [],
                                "postData": {
                                    "text": '{"name": "Jane Doe", "email": "jane@example.com"}'
                                },
                            },
                            "response": {
                                "status": 201,
                                "statusText": "Created",
                                "headers": [{"name": "Content-Type", "value": "application/json"}],
                                "content": {
                                    "text": (
                                        '{"id": 124, "name": "Jane Doe", '
                                        '"email": "jane@example.com"}'
                                    )
                                },
                            },
                            "time": 150,
                            "startedDateTime": "2023-01-01T00:01:00Z",
                        },
                    ]
                }
            }
        )

    def test_transform_har_to_openapi_basic(self):
        """Test basic HAR to OpenAPI transformation."""
        har_content = self.create_sample_har_content()

        result = self.transformer.transform_har_to_openapi(
            har_content, title="Test API", version="1.0.0", description="Test API documentation"
        )

        # Verify basic structure
        assert result["openapi"] == "3.0.3"
        assert result["info"]["title"] == "Test API"
        assert result["info"]["version"] == "1.0.0"
        assert result["info"]["description"] == "Test API documentation"

        # Verify servers
        assert len(result["servers"]) > 0
        assert result["servers"][0]["url"] == "https://api.example.com"

        # Verify paths
        assert "/users/{id}" in result["paths"]
        assert "/users" in result["paths"]

    def test_path_parameter_extraction(self):
        """Test path parameter extraction from URLs."""
        # Test numeric ID
        interaction = self.create_sample_interaction(url="https://api.example.com/users/123")
        path_template = self.transformer._extract_path_template(interaction)
        assert path_template == "/users/{id}"

        # Test UUID
        interaction = self.create_sample_interaction(
            url="https://api.example.com/users/550e8400-e29b-41d4-a716-446655440000"
        )
        path_template = self.transformer._extract_path_template(interaction)
        assert path_template == "/users/{id}"

        # Test no parameters
        interaction = self.create_sample_interaction(url="https://api.example.com/users")
        path_template = self.transformer._extract_path_template(interaction)
        assert path_template == "/users"

    def test_operation_id_generation(self):
        """Test operation ID generation."""
        interaction = self.create_sample_interaction(
            method="GET", url="https://api.example.com/users/123"
        )
        operation_id = self.transformer._generate_operation_id(interaction)
        assert operation_id == "getUsers"

        interaction = self.create_sample_interaction(
            method="POST", url="https://api.example.com/users"
        )
        operation_id = self.transformer._generate_operation_id(interaction)
        assert operation_id == "postUsers"

    def test_operation_summary_generation(self):
        """Test operation summary generation."""
        interaction = self.create_sample_interaction(
            method="GET", url="https://api.example.com/users/123"
        )
        summary = self.transformer._generate_operation_summary(interaction)
        assert summary == "GET Users"

        interaction = self.create_sample_interaction(
            method="POST", url="https://api.example.com/orders"
        )
        summary = self.transformer._generate_operation_summary(interaction)
        assert summary == "POST Orders"

    def test_operation_description_generation(self):
        """Test operation description generation."""
        interaction = self.create_sample_interaction(
            method="GET", url="https://api.example.com/users/123"
        )
        description = self.transformer._generate_operation_description(interaction)
        assert description == "Retrieve users"

        interaction = self.create_sample_interaction(
            method="POST", url="https://api.example.com/users"
        )
        description = self.transformer._generate_operation_description(interaction)
        assert description == "Create users"

        interaction = self.create_sample_interaction(
            method="DELETE", url="https://api.example.com/users/123"
        )
        description = self.transformer._generate_operation_description(interaction)
        assert description == "Delete users"

    def test_path_parameters_extraction(self):
        """Test path parameters extraction."""
        # Test numeric ID
        interaction = self.create_sample_interaction(url="https://api.example.com/users/123")
        params = self.transformer._extract_path_parameters(interaction)
        assert len(params) == 1
        assert params[0]["name"] == "id"
        assert params[0]["in"] == "path"
        assert params[0]["required"] is True
        assert params[0]["schema"]["type"] == "integer"

        # Test UUID
        interaction = self.create_sample_interaction(
            url="https://api.example.com/users/550e8400-e29b-41d4-a716-446655440000"
        )
        params = self.transformer._extract_path_parameters(interaction)
        assert len(params) == 1
        assert params[0]["schema"]["type"] == "string"
        assert params[0]["schema"]["format"] == "uuid"

    def test_query_parameters_extraction(self):
        """Test query parameters extraction."""
        interaction = self.create_sample_interaction(
            query_params={"limit": ["10"], "offset": ["0"], "active": ["true"]}
        )
        params = self.transformer._extract_query_parameters(interaction)

        assert len(params) == 3

        # Find specific parameters
        limit_param = next(p for p in params if p["name"] == "limit")
        assert limit_param["schema"]["type"] == "integer"
        assert limit_param["example"] == "10"

        active_param = next(p for p in params if p["name"] == "active")
        assert active_param["schema"]["type"] == "boolean"

    def test_request_body_extraction(self):
        """Test request body extraction."""
        # Test JSON request body
        request_data = '{"name": "John Doe", "age": 30, "active": true}'
        interaction = self.create_sample_interaction(method="POST", request_body=request_data)

        request_body = self.transformer._extract_request_body(interaction)
        assert request_body is not None
        assert request_body["required"] is True
        assert "application/json" in request_body["content"]

        schema = request_body["content"]["application/json"]["schema"]
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert schema["properties"]["active"]["type"] == "boolean"

        # Test GET request (should not have request body)
        interaction = self.create_sample_interaction(method="GET")
        request_body = self.transformer._extract_request_body(interaction)
        assert request_body is None

    def test_response_extraction(self):
        """Test response extraction."""
        response_data = '{"id": 123, "name": "John Doe", "tags": ["user", "admin"]}'
        interaction = self.create_sample_interaction(response_body=response_data)

        responses = self.transformer._extract_responses(interaction)
        assert "200" in responses

        response = responses["200"]
        assert response["description"] == "OK"
        assert "application/json" in response["content"]

        schema = response["content"]["application/json"]["schema"]
        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert schema["properties"]["id"]["type"] == "integer"
        assert schema["properties"]["tags"]["type"] == "array"
        assert schema["properties"]["tags"]["items"]["type"] == "string"

    def test_schema_inference(self):
        """Test JSON schema inference."""
        # Test primitive types
        assert self.transformer._infer_schema(None) == {"type": "null"}
        assert self.transformer._infer_schema(True) == {"type": "boolean"}
        assert self.transformer._infer_schema(42) == {"type": "integer"}
        assert self.transformer._infer_schema(3.14) == {"type": "number"}
        assert self.transformer._infer_schema("hello") == {"type": "string"}

        # Test array
        array_schema = self.transformer._infer_schema([1, 2, 3])
        assert array_schema["type"] == "array"
        assert array_schema["items"]["type"] == "integer"

        # Test object
        obj_schema = self.transformer._infer_schema({"name": "John", "age": 30})
        assert obj_schema["type"] == "object"
        assert "name" in obj_schema["properties"]
        assert "age" in obj_schema["properties"]
        assert obj_schema["properties"]["name"]["type"] == "string"
        assert obj_schema["properties"]["age"]["type"] == "integer"

    def test_type_inference_from_string(self):
        """Test type inference from string values."""
        assert self.transformer._infer_type("true") == "boolean"
        assert self.transformer._infer_type("false") == "boolean"
        assert self.transformer._infer_type("123") == "integer"
        assert self.transformer._infer_type("3.14") == "number"
        assert self.transformer._infer_type("hello") == "string"

    def test_server_extraction(self):
        """Test server extraction from endpoint groups."""
        interaction1 = self.create_sample_interaction(url="https://api.example.com/users")
        interaction2 = self.create_sample_interaction(url="https://api.example.com/orders")

        group = EndpointGroup(
            domain="api.example.com",
            base_path="/users",
            interactions=[interaction1, interaction2],
            methods={"GET"},
            content_types={"application/json"},
        )

        servers = self.transformer._extract_servers([group])
        assert len(servers) == 1
        assert servers[0]["url"] == "https://api.example.com"

    def test_invalid_har_content(self):
        """Test handling of invalid HAR content."""
        with pytest.raises(json.JSONDecodeError):
            self.transformer.transform_har_to_openapi("invalid json")

        with pytest.raises(ValueError):
            self.transformer.transform_har_to_openapi('{"invalid": "structure"}')

    def test_empty_interactions(self):
        """Test handling of HAR with no API interactions."""
        empty_har = json.dumps({"log": {"entries": []}})

        with patch.object(self.transformer.har_parser, "parse_har_content", return_value=[]):
            with pytest.raises(ValueError, match="No API interactions found"):
                self.transformer.transform_har_to_openapi(empty_har)

    def test_save_openapi_spec(self, tmp_path):
        """Test saving OpenAPI specification to file."""
        spec = {"openapi": "3.0.3", "info": {"title": "Test API", "version": "1.0.0"}}

        file_path = tmp_path / "openapi.json"
        self.transformer.save_openapi_spec(spec, str(file_path))

        assert file_path.exists()
        with open(file_path, "r") as f:
            saved_spec = json.load(f)

        assert saved_spec == spec

    def test_operation_merging(self):
        """Test merging of operations with different response codes."""
        interaction1 = self.create_sample_interaction(status=200)
        interaction2 = self.create_sample_interaction(
            status=404, response_body='{"error": "Not found"}'
        )

        group = EndpointGroup(
            domain="api.example.com",
            base_path="/users",
            interactions=[interaction1, interaction2],
            methods={"GET"},
            content_types={"application/json"},
        )

        paths = self.transformer._generate_paths([group])
        operation = paths["/users/{id}"]["get"]

        # Should have both response codes
        assert "200" in operation["responses"]
        assert "404" in operation["responses"]

    @patch("app.services.har_to_openapi.validate")
    def test_openapi_validation_success(self, mock_validate):
        """Test successful OpenAPI validation."""
        mock_validate.return_value = None  # No exception means valid

        spec = {"openapi": "3.0.3", "info": {"title": "Test", "version": "1.0.0"}}
        self.transformer._validate_openapi_spec(spec)

        mock_validate.assert_called_once_with(spec)

    @patch("app.services.har_to_openapi.validate")
    def test_openapi_validation_failure(self, mock_validate):
        """Test OpenAPI validation failure."""
        from openapi_spec_validator.exceptions import OpenAPISpecValidatorError

        mock_validate.side_effect = OpenAPISpecValidatorError("Invalid spec")

        spec = {"invalid": "spec"}
        with pytest.raises(OpenAPISpecValidatorError):
            self.transformer._validate_openapi_spec(spec)

    def test_full_transformation_workflow(self):
        """Test the complete transformation workflow."""
        har_content = self.create_sample_har_content()

        result = self.transformer.transform_har_to_openapi(
            har_content,
            title="Complete Test API",
            version="2.0.0",
            description="Complete test of HAR to OpenAPI transformation",
        )

        # Verify complete structure
        assert result["openapi"] == "3.0.3"
        assert result["info"]["title"] == "Complete Test API"
        assert result["info"]["version"] == "2.0.0"

        # Verify paths exist
        assert "/users/{id}" in result["paths"]
        assert "/users" in result["paths"]

        # Verify operations
        get_user_op = result["paths"]["/users/{id}"]["get"]
        assert get_user_op["operationId"] == "getUsers"
        assert get_user_op["summary"] == "GET Users"
        assert len(get_user_op["parameters"]) > 0  # Should have path parameter

        post_user_op = result["paths"]["/users"]["post"]
        assert post_user_op["operationId"] == "postUsers"
        assert "requestBody" in post_user_op

        # Verify components structure exists
        assert "components" in result
        assert "schemas" in result["components"]
