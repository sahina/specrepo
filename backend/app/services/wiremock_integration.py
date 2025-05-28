import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import httpx
import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OpenAPIEndpoint(BaseModel):
    """Represents a parsed OpenAPI endpoint."""

    path: str
    method: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class WireMockStub(BaseModel):
    """Represents a WireMock stub configuration."""

    request: Dict[str, Any]
    response: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class OpenAPIParser:
    """Parser for OpenAPI specifications."""

    @staticmethod
    def parse_specification(
        content: Union[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Parse OpenAPI specification from string or dict.

        Args:
            content: OpenAPI specification as string (JSON/YAML) or dict

        Returns:
            Parsed OpenAPI specification as dict

        Raises:
            ValueError: If content cannot be parsed
        """
        if isinstance(content, str):
            try:
                # Try JSON first
                return json.loads(content)
            except json.JSONDecodeError:
                try:
                    # Try YAML
                    return yaml.safe_load(content)
                except yaml.YAMLError as e:
                    raise ValueError(f"Failed to parse OpenAPI specification: {e}")
        elif isinstance(content, dict):
            return content
        else:
            raise ValueError("Content must be string or dict")

    @staticmethod
    def extract_endpoints(
        openapi_spec: Dict[str, Any],
    ) -> List[OpenAPIEndpoint]:
        """
        Extract endpoint definitions from OpenAPI specification.

        Args:
            openapi_spec: Parsed OpenAPI specification

        Returns:
            List of OpenAPIEndpoint objects
        """
        endpoints = []
        paths = openapi_spec.get("paths", {})

        for path, path_item in paths.items():
            # Handle path-level parameters
            path_parameters = path_item.get("parameters", [])

            for method, operation in path_item.items():
                if method.startswith("x-") or method == "parameters":
                    continue

                if not isinstance(operation, dict):
                    continue

                # Combine path-level and operation-level parameters
                operation_parameters = operation.get("parameters", [])
                all_parameters = path_parameters + operation_parameters

                endpoint = OpenAPIEndpoint(
                    path=path,
                    method=method.upper(),
                    operation_id=operation.get("operationId"),
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    parameters=all_parameters,
                    request_body=operation.get("requestBody"),
                    responses=operation.get("responses", {}),
                    tags=operation.get("tags", []),
                )

                endpoints.append(endpoint)

        return endpoints

    @staticmethod
    def get_example_from_schema(schema: Dict[str, Any]) -> Any:
        """
        Extract example value from OpenAPI schema.

        Args:
            schema: OpenAPI schema object

        Returns:
            Example value or None
        """
        # Check for explicit example
        if "example" in schema:
            return schema["example"]

        # Check for examples array
        if "examples" in schema and schema["examples"]:
            return list(schema["examples"].values())[0].get("value")

        # Generate simple example based on type
        schema_type = schema.get("type")
        if schema_type == "string":
            return "example_string"
        elif schema_type == "integer":
            return 123
        elif schema_type == "number":
            return 123.45
        elif schema_type == "boolean":
            return True
        elif schema_type == "array":
            items_schema = schema.get("items", {})
            item_example = OpenAPIParser.get_example_from_schema(items_schema)
            return [item_example] if item_example is not None else []
        elif schema_type == "object":
            properties = schema.get("properties", {})
            example_obj = {}
            for prop_name, prop_schema in properties.items():
                prop_example = OpenAPIParser.get_example_from_schema(prop_schema)
                if prop_example is not None:
                    example_obj[prop_name] = prop_example
            return example_obj

        return None


class WireMockStubGenerator:
    """Generates WireMock stub configurations from OpenAPI endpoints."""

    @staticmethod
    def generate_stub(endpoint: OpenAPIEndpoint, base_url: str = "") -> WireMockStub:
        """
        Generate WireMock stub from OpenAPI endpoint.

        Args:
            endpoint: OpenAPI endpoint definition
            base_url: Base URL for the API (optional)

        Returns:
            WireMockStub configuration
        """
        # Build request matcher
        request_config = {
            "method": endpoint.method,
            "urlPattern": WireMockStubGenerator._build_url_pattern(
                endpoint.path, endpoint.parameters
            ),
        }

        # Add query parameter matchers
        query_params = WireMockStubGenerator._extract_query_parameters(endpoint.parameters)
        if query_params:
            request_config["queryParameters"] = query_params

        # Add header matchers
        header_params = WireMockStubGenerator._extract_header_parameters(endpoint.parameters)
        if header_params:
            request_config["headers"] = header_params

        # Add request body matcher
        if endpoint.request_body:
            body_matcher = WireMockStubGenerator._build_body_matcher(endpoint.request_body)
            if body_matcher:
                request_config.update(body_matcher)

        # Build response
        response_config = WireMockStubGenerator._build_response(endpoint.responses)

        # Add metadata
        metadata = {
            "operationId": endpoint.operation_id,
            "summary": endpoint.summary,
            "tags": endpoint.tags,
        }

        return WireMockStub(request=request_config, response=response_config, metadata=metadata)

    @staticmethod
    def _build_url_pattern(path: str, parameters: List[Dict[str, Any]]) -> str:
        """Build URL pattern with path parameter placeholders."""
        url_pattern = path

        # Replace path parameters with regex patterns
        for param in parameters:
            if param.get("in") == "path":
                param_name = param.get("name")
                if param_name:
                    # Replace {param} with regex pattern
                    placeholder = f"{{{param_name}}}"
                    if placeholder in url_pattern:
                        # Use appropriate regex based on parameter type
                        param_type = param.get("schema", {}).get("type", "string")
                        if param_type == "integer":
                            pattern = r"[0-9]+"
                        elif param_type == "number":
                            pattern = r"[0-9]+\.?[0-9]*"
                        else:
                            pattern = r"[^/]+"

                        url_pattern = url_pattern.replace(placeholder, f"({pattern})")

        return url_pattern

    @staticmethod
    def _extract_query_parameters(
        parameters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract query parameter matchers."""
        query_params = {}

        for param in parameters:
            if param.get("in") == "query":
                param_name = param.get("name")
                if param_name:
                    # Use example value if available
                    schema = param.get("schema", {})
                    example = OpenAPIParser.get_example_from_schema(schema)

                    if example is not None:
                        query_params[param_name] = {"equalTo": str(example)}
                    elif param.get("required", False):
                        query_params[param_name] = {"matches": ".*"}

        return query_params

    @staticmethod
    def _extract_header_parameters(
        parameters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract header parameter matchers."""
        headers = {}

        for param in parameters:
            if param.get("in") == "header":
                param_name = param.get("name")
                if param_name:
                    schema = param.get("schema", {})
                    example = OpenAPIParser.get_example_from_schema(schema)

                    if example is not None:
                        headers[param_name] = {"equalTo": str(example)}
                    elif param.get("required", False):
                        headers[param_name] = {"matches": ".*"}

        return headers

    @staticmethod
    def _build_body_matcher(request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Build request body matcher."""
        content = request_body.get("content", {})

        # Handle JSON content
        if "application/json" in content:
            json_content = content["application/json"]
            schema = json_content.get("schema", {})
            example = OpenAPIParser.get_example_from_schema(schema)

            if example is not None:
                return {"bodyPatterns": [{"equalToJson": json.dumps(example)}]}

        # Handle other content types
        for content_type, content_spec in content.items():
            schema = content_spec.get("schema", {})
            example = OpenAPIParser.get_example_from_schema(schema)

            if example is not None:
                if content_type.startswith("text/"):
                    return {"bodyPatterns": [{"equalTo": str(example)}]}

        return {}

    @staticmethod
    def _build_response(
        responses: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build response configuration."""
        # Default to 200 OK if available, otherwise use first response
        response_spec = (
            responses.get("200") or responses.get("201") or next(iter(responses.values()), {})
        )

        response_config = {
            "status": 200,
            "headers": {"Content-Type": "application/json"},
        }

        # Extract status code
        for status_code, spec in responses.items():
            if status_code.isdigit():
                response_config["status"] = int(status_code)
                response_spec = spec
                break

        # Extract response body
        content = response_spec.get("content", {})
        if "application/json" in content:
            json_content = content["application/json"]
            schema = json_content.get("schema", {})
            example = OpenAPIParser.get_example_from_schema(schema)

            if example is not None:
                response_config["body"] = json.dumps(example)
                response_config["headers"]["Content-Type"] = "application/json"

        # Handle other content types
        for content_type, content_spec in content.items():
            if content_type != "application/json":
                schema = content_spec.get("schema", {})
                example = OpenAPIParser.get_example_from_schema(schema)

                if example is not None:
                    response_config["body"] = str(example)
                    response_config["headers"]["Content-Type"] = content_type
                    break

        return response_config


class WireMockClient:
    """Client for interacting with WireMock Admin API."""

    def __init__(self, base_url: str = None):
        """
        Initialize WireMock client.

        Args:
            base_url: WireMock server base URL (defaults to environment variable or localhost)
        """
        if base_url is None:
            base_url = os.getenv("WIREMOCK_URL", "http://localhost:8081")
        self.base_url = base_url.rstrip("/")
        self.admin_url = f"{self.base_url}/__admin"

    async def create_stub(self, stub: WireMockStub) -> Dict[str, Any]:
        """
        Create a new stub in WireMock.

        Args:
            stub: WireMock stub configuration

        Returns:
            Response from WireMock API

        Raises:
            httpx.HTTPError: If request fails
        """
        stub_config = {"request": stub.request, "response": stub.response}

        if stub.metadata:
            stub_config["metadata"] = stub.metadata

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.admin_url}/mappings",
                json=stub_config,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def get_stubs(self) -> List[Dict[str, Any]]:
        """
        Get all stubs from WireMock.

        Returns:
            List of stub configurations

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.admin_url}/mappings")
            response.raise_for_status()
            data = response.json()
            return data.get("mappings", [])

    async def delete_stub(self, stub_id: str) -> bool:
        """
        Delete a specific stub.

        Args:
            stub_id: UUID of the stub to delete

        Returns:
            True if deleted successfully

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.admin_url}/mappings/{stub_id}")
            response.raise_for_status()
            return True

    async def reset_stubs(self) -> bool:
        """
        Reset all stubs in WireMock.

        Returns:
            True if reset successfully

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.admin_url}/reset")
            response.raise_for_status()
            return True

    async def clear_stubs(self) -> bool:
        """
        Clear all stubs (delete all mappings).

        Returns:
            True if cleared successfully

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.admin_url}/mappings")
            response.raise_for_status()
            return True


class WireMockIntegrationService:
    """Main service for WireMock integration."""

    def __init__(self, wiremock_url: str = None):
        """
        Initialize WireMock integration service.

        Args:
            wiremock_url: WireMock server URL (defaults to environment variable or localhost)
        """
        self.parser = OpenAPIParser()
        self.stub_generator = WireMockStubGenerator()
        self.client = WireMockClient(wiremock_url)

    async def generate_stubs_from_openapi(
        self,
        openapi_content: Union[str, Dict[str, Any]],
        clear_existing: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Generate and create WireMock stubs from OpenAPI specification.

        Args:
            openapi_content: OpenAPI specification content
            clear_existing: Whether to clear existing stubs first

        Returns:
            List of created stub responses

        Raises:
            ValueError: If OpenAPI content is invalid
            httpx.HTTPError: If WireMock requests fail
        """
        try:
            # Parse OpenAPI specification
            openapi_spec = self.parser.parse_specification(openapi_content)
            endpoints = self.parser.extract_endpoints(openapi_spec)

            logger.info(f"Extracted {len(endpoints)} endpoints from OpenAPI specification")

            # Clear existing stubs if requested
            if clear_existing:
                await self.client.clear_stubs()
                logger.info("Cleared existing WireMock stubs")

            # Generate and create stubs
            created_stubs = []
            for endpoint in endpoints:
                try:
                    stub = self.stub_generator.generate_stub(endpoint)
                    result = await self.client.create_stub(stub)
                    created_stubs.append(result)

                    logger.info(
                        f"Created stub for {endpoint.method} {endpoint.path} "
                        f"(ID: {result.get('id', 'unknown')})"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create stub for {endpoint.method} {endpoint.path}: {e}"
                    )
                    # Continue with other endpoints

            logger.info(f"Successfully created {len(created_stubs)} WireMock stubs")
            return created_stubs

        except Exception as e:
            logger.error(f"Failed to generate stubs from OpenAPI: {e}")
            raise

    async def get_all_stubs(self) -> List[Dict[str, Any]]:
        """
        Get all current WireMock stubs.

        Returns:
            List of stub configurations
        """
        return await self.client.get_stubs()

    async def clear_all_stubs(self) -> bool:
        """
        Clear all WireMock stubs.

        Returns:
            True if successful
        """
        result = await self.client.clear_stubs()
        logger.info("Cleared all WireMock stubs")
        return result

    async def reset_wiremock(self) -> bool:
        """
        Reset WireMock to initial state.

        Returns:
            True if successful
        """
        result = await self.client.reset_stubs()
        logger.info("Reset WireMock to initial state")
        return result
