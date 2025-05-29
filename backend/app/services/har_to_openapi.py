import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from openapi_spec_validator import validate
from openapi_spec_validator.exceptions import OpenAPISpecValidatorError

from .har_parser import APIInteraction, EndpointGroup, HARParser

logger = logging.getLogger(__name__)


@dataclass
class OpenAPIParameter:
    """Represents an OpenAPI parameter."""

    name: str
    location: str  # "path", "query", "header", "cookie"
    required: bool
    schema: Dict[str, Any]
    description: Optional[str] = None


@dataclass
class OpenAPIResponse:
    """Represents an OpenAPI response."""

    status_code: str
    description: str
    content: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None


@dataclass
class OpenAPIOperation:
    """Represents an OpenAPI operation."""

    method: str
    path: str
    operation_id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[OpenAPIParameter] = None
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, OpenAPIResponse] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.responses is None:
            self.responses = {}
        if self.tags is None:
            self.tags = []


class HARToOpenAPITransformer:
    """
    Transforms HAR data into OpenAPI 3.0 specifications.

    This class takes parsed HAR data and generates valid OpenAPI 3.0
    documents with intelligent type inference, path parameter extraction,
    and meaningful operation descriptions.
    """

    def __init__(self):
        """Initialize the HAR to OpenAPI transformer."""
        self.har_parser = HARParser()

    def transform_har_to_openapi(
        self,
        har_content: str,
        title: str = "API Documentation",
        version: str = "1.0.0",
        description: str = "API documentation generated from HAR file",
    ) -> Dict[str, Any]:
        """
        Transform HAR content into an OpenAPI 3.0 specification.

        Args:
            har_content: Raw HAR file content as string
            title: Title for the OpenAPI document
            version: Version for the API
            description: Description for the API

        Returns:
            OpenAPI 3.0 specification as dictionary

        Raises:
            ValueError: If HAR content is invalid or transformation fails
            OpenAPISpecValidatorError: If generated OpenAPI spec is invalid
        """
        try:
            # Parse HAR content
            interactions = self.har_parser.parse_har_content(har_content)
            if not interactions:
                raise ValueError("No API interactions found in HAR file")

            # Group endpoints
            endpoint_groups = self.har_parser.group_endpoints(interactions)

            # Generate OpenAPI document
            openapi_spec = self._generate_openapi_document(
                endpoint_groups, title, version, description
            )

            # Validate the generated specification
            self._validate_openapi_spec(openapi_spec)

            logger.info(
                f"Successfully transformed HAR to OpenAPI with "
                f"{len(endpoint_groups)} endpoint groups"
            )
            return openapi_spec

        except Exception as e:
            logger.error(f"Failed to transform HAR to OpenAPI: {e}")
            raise

    def _generate_openapi_document(
        self, endpoint_groups: List[EndpointGroup], title: str, version: str, description: str
    ) -> Dict[str, Any]:
        """Generate the complete OpenAPI 3.0 document structure."""
        # Base OpenAPI document structure
        openapi_doc = {
            "openapi": "3.0.3",
            "info": {"title": title, "version": version, "description": description},
            "servers": [],
            "paths": {},
            "components": {"schemas": {}, "parameters": {}, "responses": {}, "examples": {}},
        }

        # Extract servers from endpoint groups
        servers = self._extract_servers(endpoint_groups)
        openapi_doc["servers"] = servers

        # Generate paths from endpoint groups
        paths = self._generate_paths(endpoint_groups)
        openapi_doc["paths"] = paths

        return openapi_doc

    def _extract_servers(self, endpoint_groups: List[EndpointGroup]) -> List[Dict[str, str]]:
        """Extract server information from endpoint groups."""
        servers = set()

        for group in endpoint_groups:
            # Use the domain from the first interaction as the server
            if group.interactions:
                first_interaction = group.interactions[0]
                parsed_url = urlparse(first_interaction.request.url)
                server_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                servers.add(server_url)

        return [{"url": server} for server in sorted(servers)]

    def _generate_paths(self, endpoint_groups: List[EndpointGroup]) -> Dict[str, Any]:
        """Generate OpenAPI paths from endpoint groups."""
        paths = {}
        operation_ids = set()  # Track used operation IDs

        for group in endpoint_groups:
            for interaction in group.interactions:
                path_template = self._extract_path_template(interaction)
                method = interaction.request.method.lower()

                if path_template not in paths:
                    paths[path_template] = {}

                if method not in paths[path_template]:
                    operation = self._generate_operation(interaction, group)

                    # Ensure operation ID is unique
                    base_operation_id = operation["operationId"]
                    operation_id = base_operation_id
                    counter = 1

                    while operation_id in operation_ids:
                        operation_id = f"{base_operation_id}{counter}"
                        counter += 1

                    operation["operationId"] = operation_id
                    operation_ids.add(operation_id)

                    paths[path_template][method] = operation
                else:
                    # Merge with existing operation if needed
                    self._merge_operation(paths[path_template][method], interaction)

        return paths

    def _extract_path_template(self, interaction: APIInteraction) -> str:
        """Extract path template with parameters from URL."""
        parsed_url = urlparse(interaction.request.url)
        path = parsed_url.path

        # Simple path parameter detection
        # Look for numeric IDs and UUIDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)",
            "/{id}",
            path,
            flags=re.IGNORECASE,
        )

        return path

    def _generate_operation(
        self, interaction: APIInteraction, group: EndpointGroup
    ) -> Dict[str, Any]:
        """Generate OpenAPI operation from interaction."""
        operation = {
            "operationId": self._generate_operation_id(interaction),
            "summary": self._generate_operation_summary(interaction),
            "description": self._generate_operation_description(interaction),
            "tags": [group.domain],
            "parameters": [],
            "responses": {},
        }

        # Add parameters
        parameters = self._extract_parameters(interaction)
        if parameters:
            operation["parameters"] = parameters

        # Add request body if present
        request_body = self._extract_request_body(interaction)
        if request_body:
            operation["requestBody"] = request_body

        # Add responses
        responses = self._extract_responses(interaction)
        operation["responses"] = responses

        return operation

    def _generate_operation_id(self, interaction: APIInteraction) -> str:
        """Generate operation ID from method and path."""
        method = interaction.request.method.lower()
        path = urlparse(interaction.request.url).path

        # Clean path for operation ID
        path_parts = [part for part in path.split("/") if part and not part.isdigit()]
        if path_parts:
            resource = path_parts[-1]
            # Remove file extensions
            resource = re.sub(r"\.[^.]+$", "", resource)
            # Replace non-alphanumeric characters
            resource = re.sub(r"[^a-zA-Z0-9]", "", resource)
            return f"{method}{resource.capitalize()}"

        return f"{method}Root"

    def _generate_operation_summary(self, interaction: APIInteraction) -> str:
        """Generate operation summary."""
        method = interaction.request.method.upper()
        path = urlparse(interaction.request.url).path

        # Extract resource name from path
        path_parts = [part for part in path.split("/") if part and not part.isdigit()]
        if path_parts:
            resource = path_parts[-1].replace("_", " ").replace("-", " ").title()
            return f"{method} {resource}"

        return f"{method} Resource"

    def _generate_operation_description(self, interaction: APIInteraction) -> str:
        """Generate operation description."""
        method = interaction.request.method.upper()
        path = urlparse(interaction.request.url).path

        descriptions = {
            "GET": "Retrieve",
            "POST": "Create",
            "PUT": "Update",
            "PATCH": "Partially update",
            "DELETE": "Delete",
        }

        action = descriptions.get(method, method)
        path_parts = [part for part in path.split("/") if part and not part.isdigit()]

        if path_parts:
            resource = path_parts[-1].replace("_", " ").replace("-", " ")
            return f"{action} {resource}"

        return f"{action} resource"

    def _extract_parameters(self, interaction: APIInteraction) -> List[Dict[str, Any]]:
        """Extract parameters from interaction."""
        parameters = []

        # Path parameters
        path_params = self._extract_path_parameters(interaction)
        parameters.extend(path_params)

        # Query parameters
        query_params = self._extract_query_parameters(interaction)
        parameters.extend(query_params)

        return parameters

    def _extract_path_parameters(self, interaction: APIInteraction) -> List[Dict[str, Any]]:
        """Extract path parameters from URL."""
        parameters = []
        path = urlparse(interaction.request.url).path

        # Check if path contains numeric IDs
        if re.search(r"/\d+(?=/|$)", path):
            parameters.append(
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                    "description": "Resource identifier",
                }
            )

        # Check for UUID parameters
        if re.search(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)",
            path,
            re.IGNORECASE,
        ):
            parameters.append(
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string", "format": "uuid"},
                    "description": "Resource identifier",
                }
            )

        return parameters

    def _extract_query_parameters(self, interaction: APIInteraction) -> List[Dict[str, Any]]:
        """Extract query parameters from request."""
        parameters = []

        for param_name, param_values in interaction.request.query_params.items():
            if param_values:
                # Infer type from first value
                param_type = self._infer_type(param_values[0])

                parameter = {
                    "name": param_name,
                    "in": "query",
                    "required": False,
                    "schema": {"type": param_type},
                    "description": f"Query parameter {param_name}",
                }

                # Add example if available
                if param_values:
                    parameter["example"] = param_values[0]

                parameters.append(parameter)

        return parameters

    def _extract_request_body(self, interaction: APIInteraction) -> Optional[Dict[str, Any]]:
        """Extract request body schema from interaction."""
        if not interaction.request.body or interaction.request.method.upper() in ["GET", "DELETE"]:
            return None

        content_type = interaction.request.content_type or "application/json"

        request_body = {"required": True, "content": {content_type: {}}}

        # Try to parse JSON body for schema
        if "json" in content_type.lower() and interaction.request.body:
            try:
                body_data = json.loads(interaction.request.body)
                schema = self._infer_schema(body_data)
                request_body["content"][content_type]["schema"] = schema
                request_body["content"][content_type]["example"] = body_data
            except json.JSONDecodeError:
                # Fallback to string schema
                request_body["content"][content_type]["schema"] = {"type": "string"}
                request_body["content"][content_type]["example"] = interaction.request.body
        else:
            # Non-JSON content
            request_body["content"][content_type]["schema"] = {"type": "string"}
            if interaction.request.body:
                request_body["content"][content_type]["example"] = interaction.request.body

        return request_body

    def _extract_responses(self, interaction: APIInteraction) -> Dict[str, Any]:
        """Extract response schemas from interaction."""
        responses = {}

        status_code = str(interaction.response.status)
        content_type = interaction.response.content_type or "application/json"

        response = {
            "description": interaction.response.status_text or f"HTTP {status_code}",
            "content": {},
        }

        if interaction.response.body:
            response_content = {content_type: {}}

            # Try to parse JSON response for schema
            if "json" in content_type.lower():
                try:
                    response_data = json.loads(interaction.response.body)
                    schema = self._infer_schema(response_data)
                    response_content[content_type]["schema"] = schema
                    response_content[content_type]["example"] = response_data
                except json.JSONDecodeError:
                    # Fallback to string schema
                    response_content[content_type]["schema"] = {"type": "string"}
                    response_content[content_type]["example"] = interaction.response.body
            else:
                # Non-JSON content
                response_content[content_type]["schema"] = {"type": "string"}
                response_content[content_type]["example"] = interaction.response.body

            response["content"] = response_content

        responses[status_code] = response

        return responses

    def _infer_schema(self, data: Any) -> Dict[str, Any]:
        """Infer JSON schema from data."""
        if data is None:
            return {"type": "null"}
        elif isinstance(data, bool):
            return {"type": "boolean"}
        elif isinstance(data, int):
            return {"type": "integer"}
        elif isinstance(data, float):
            return {"type": "number"}
        elif isinstance(data, str):
            return {"type": "string"}
        elif isinstance(data, list):
            if not data:
                return {"type": "array", "items": {}}

            # Infer schema from first item
            item_schema = self._infer_schema(data[0])
            return {"type": "array", "items": item_schema}
        elif isinstance(data, dict):
            properties = {}
            required = []

            for key, value in data.items():
                properties[key] = self._infer_schema(value)
                if value is not None:
                    required.append(key)

            schema = {"type": "object", "properties": properties}
            if required:
                schema["required"] = required

            return schema
        else:
            return {"type": "string"}

    def _infer_type(self, value: str) -> str:
        """Infer simple type from string value."""
        if value.lower() in ["true", "false"]:
            return "boolean"

        try:
            int(value)
            return "integer"
        except ValueError:
            pass

        try:
            float(value)
            return "number"
        except ValueError:
            pass

        return "string"

    def _merge_operation(
        self, existing_operation: Dict[str, Any], interaction: APIInteraction
    ) -> None:
        """Merge additional interaction data into existing operation."""
        # Add additional response status codes
        new_responses = self._extract_responses(interaction)
        existing_operation["responses"].update(new_responses)

        # Could add more merging logic here for parameters, examples, etc.

    def _validate_openapi_spec(self, spec: Dict[str, Any]) -> None:
        """Validate the generated OpenAPI specification."""
        try:
            validate(spec)
            logger.info("Generated OpenAPI specification is valid")
        except OpenAPISpecValidatorError as e:
            logger.error(f"Generated OpenAPI specification is invalid: {e}")
            raise

    def save_openapi_spec(self, spec: Dict[str, Any], file_path: str) -> None:
        """
        Save OpenAPI specification to a file.

        Args:
            spec: OpenAPI specification dictionary
            file_path: Path to save the file
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
            logger.info(f"OpenAPI specification saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save OpenAPI specification: {e}")
            raise
