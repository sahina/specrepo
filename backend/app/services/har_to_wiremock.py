import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .har_parser import APIInteraction, APIRequest, APIResponse
from .wiremock_integration import WireMockStub

logger = logging.getLogger(__name__)


class HARToWireMockTransformer:
    """
    Transforms HAR data into WireMock stub configurations.

    This class converts parsed HAR API interactions into WireMock-compatible
    stub configurations, supporting intelligent request matching, response
    generation, and stateful behavior.
    """

    # Headers to exclude from request matching (typically vary per request)
    EXCLUDED_REQUEST_HEADERS = {
        "accept-encoding",
        "connection",
        "content-length",
        "date",
        "host",
        "user-agent",
        "x-forwarded-for",
        "x-real-ip",
        "x-request-id",
        "x-correlation-id",
        "authorization",  # Often varies, handle separately
        "cookie",  # Often varies, handle separately
    }

    # Headers to exclude from response (WireMock handles these)
    EXCLUDED_RESPONSE_HEADERS = {
        "content-length",
        "date",
        "server",
        "transfer-encoding",
        "connection",
        "keep-alive",
    }

    # Content types that should be treated as JSON for templating
    JSON_CONTENT_TYPES = {
        "application/json",
        "application/vnd.api+json",
        "text/json",
    }

    def __init__(
        self,
        enable_stateful: bool = True,
        enable_templating: bool = True,
        strict_matching: bool = False,
    ):
        """
        Initialize the HAR to WireMock transformer.

        Args:
            enable_stateful: Enable stateful behavior for related requests
            enable_templating: Enable response templating for dynamic responses
            strict_matching: Use strict request matching (exact headers, etc.)
        """
        self.enable_stateful = enable_stateful
        self.enable_templating = enable_templating
        self.strict_matching = strict_matching

    def transform_interactions(
        self, interactions: List[APIInteraction], base_url: Optional[str] = None
    ) -> List[WireMockStub]:
        """
        Transform HAR API interactions into WireMock stubs.

        Args:
            interactions: List of HAR API interactions
            base_url: Optional base URL to strip from request URLs

        Returns:
            List of WireMock stub configurations
        """
        if not interactions:
            return []

        stubs = []

        # Group interactions by endpoint for stateful behavior
        if self.enable_stateful:
            endpoint_groups = self._group_by_endpoint(interactions)
            for endpoint, group_interactions in endpoint_groups.items():
                if len(group_interactions) > 1:
                    # Create stateful stubs for multiple interactions
                    stateful_stubs = self._create_stateful_stubs(group_interactions, base_url)
                    stubs.extend(stateful_stubs)
                else:
                    # Single interaction, create regular stub
                    stub = self._create_stub(group_interactions[0], base_url)
                    if stub:
                        stubs.append(stub)
        else:
            # Create individual stubs for each interaction
            for interaction in interactions:
                stub = self._create_stub(interaction, base_url)
                if stub:
                    stubs.append(stub)

        logger.info(
            f"Transformed {len(interactions)} HAR interactions into {len(stubs)} WireMock stubs"
        )
        return stubs

    def _group_by_endpoint(
        self, interactions: List[APIInteraction]
    ) -> Dict[str, List[APIInteraction]]:
        """Group interactions by endpoint (method + path pattern)."""
        groups = {}

        for interaction in interactions:
            # Create endpoint key from method and normalized path
            path = self._normalize_path(interaction.request.path)
            endpoint_key = f"{interaction.request.method}:{path}"

            if endpoint_key not in groups:
                groups[endpoint_key] = []
            groups[endpoint_key].append(interaction)

        return groups

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing IDs with patterns."""
        # Replace numeric IDs with patterns
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        # Replace UUID patterns
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)",
            "/{uuid}",
            path,
            flags=re.IGNORECASE,
        )
        return path

    def _create_stub(
        self,
        interaction: APIInteraction,
        base_url: Optional[str] = None,
        scenario_name: Optional[str] = None,
        required_state: Optional[str] = None,
        new_state: Optional[str] = None,
    ) -> Optional[WireMockStub]:
        """Create a WireMock stub from a single HAR interaction."""
        try:
            request_config = self._create_request_matcher(interaction.request, base_url)
            response_config = self._create_response_config(interaction.response)

            # Add scenario state if provided
            if scenario_name:
                request_config["scenario"] = scenario_name
                if required_state:
                    request_config["requiredScenarioState"] = required_state
                if new_state:
                    response_config["newScenarioState"] = new_state

            # Create metadata
            metadata = {
                "source": "har_transformation",
                "entry_id": interaction.entry_id,
                "timestamp": interaction.request.timestamp,
                "duration": interaction.duration,
                "domain": interaction.request.domain,
            }

            return WireMockStub(request=request_config, response=response_config, metadata=metadata)
        except Exception as e:
            logger.error(f"Failed to create stub for interaction {interaction.entry_id}: {e}")
            return None

    def _create_request_matcher(
        self, request: APIRequest, base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create WireMock request matcher configuration."""
        config = {"method": request.method}

        # Handle URL matching
        url = request.url
        if base_url and url.startswith(base_url):
            url = url[len(base_url) :]

        parsed_url = urlparse(url)
        path = parsed_url.path

        # Use URL pattern for flexible matching
        if self._has_dynamic_segments(path):
            config["urlPattern"] = self._create_url_pattern(path)
        else:
            config["url"] = path

        # Add query parameter matching
        if request.query_params:
            query_matchers = {}
            for param, values in request.query_params.items():
                if values:
                    # Use first value for matching, could be enhanced for multiple values
                    query_matchers[param] = {"equalTo": values[0]}
            if query_matchers:
                config["queryParameters"] = query_matchers

        # Add header matching (filtered)
        if request.headers and self.strict_matching:
            header_matchers = {}
            for header, value in request.headers.items():
                header_lower = header.lower()
                if header_lower not in self.EXCLUDED_REQUEST_HEADERS:
                    header_matchers[header] = {"equalTo": value}
            if header_matchers:
                config["headers"] = header_matchers
        elif request.headers:
            # Add only essential headers for loose matching
            essential_headers = {}
            for header, value in request.headers.items():
                header_lower = header.lower()
                if header_lower in ["content-type", "accept"]:
                    essential_headers[header] = {"equalTo": value}
            if essential_headers:
                config["headers"] = essential_headers

        # Add body matching for POST/PUT/PATCH requests
        if request.body and request.method in ["POST", "PUT", "PATCH"]:
            body_matcher = self._create_body_matcher(request.body, request.content_type)
            if body_matcher:
                config.update(body_matcher)

        return config

    def _create_response_config(self, response: APIResponse) -> Dict[str, Any]:
        """Create WireMock response configuration."""
        config = {"status": response.status}

        # Add response headers (filtered)
        if response.headers:
            filtered_headers = {}
            for header, value in response.headers.items():
                if header.lower() not in self.EXCLUDED_RESPONSE_HEADERS:
                    filtered_headers[header] = value
            if filtered_headers:
                config["headers"] = filtered_headers

        # Add response body
        if response.body:
            if self.enable_templating and self._is_json_response(response):
                # Try to create templated response for JSON
                templated_body = self._create_templated_response(response.body)
                if templated_body:
                    config["body"] = templated_body
                else:
                    config["body"] = response.body
            else:
                config["body"] = response.body

        return config

    def _create_stateful_stubs(
        self, interactions: List[APIInteraction], base_url: Optional[str] = None
    ) -> List[WireMockStub]:
        """Create stateful WireMock stubs for a sequence of interactions."""
        if len(interactions) <= 1:
            return [self._create_stub(interactions[0], base_url)] if interactions else []

        stubs = []
        scenario_name = f"scenario_{uuid.uuid4().hex[:8]}"

        # Sort interactions by timestamp
        sorted_interactions = sorted(interactions, key=lambda x: x.request.timestamp)

        for i, interaction in enumerate(sorted_interactions):
            required_state = f"state_{i}" if i > 0 else None
            new_state = f"state_{i + 1}" if i < len(sorted_interactions) - 1 else None

            stub = self._create_stub(
                interaction,
                base_url,
                scenario_name=scenario_name,
                required_state=required_state,
                new_state=new_state,
            )
            if stub:
                stubs.append(stub)

        return stubs

    def _has_dynamic_segments(self, path: str) -> bool:
        """Check if path contains dynamic segments (IDs, UUIDs, etc.)."""
        # Check for numeric IDs
        if re.search(r"/\d+(?=/|$)", path):
            return True
        # Check for UUIDs
        if re.search(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)",
            path,
            re.IGNORECASE,
        ):
            return True
        return False

    def _create_url_pattern(self, path: str) -> str:
        """Create URL pattern with regex for dynamic segments."""
        # Replace numeric IDs with regex pattern
        pattern = re.sub(r"/\d+(?=/|$)", r"/\\d+", path)
        # Replace UUIDs with regex pattern
        pattern = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)",
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            pattern,
            flags=re.IGNORECASE,
        )
        return pattern

    def _create_body_matcher(
        self, body: str, content_type: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Create body matcher configuration."""
        if not body:
            return None

        if content_type and any(ct in content_type.lower() for ct in self.JSON_CONTENT_TYPES):
            try:
                # Validate JSON and use JSON matching
                json.loads(body)
                return {"bodyPatterns": [{"equalToJson": body, "ignoreArrayOrder": True}]}
            except json.JSONDecodeError:
                # Fall back to text matching
                pass

        # Use text matching for non-JSON or invalid JSON
        return {"bodyPatterns": [{"equalTo": body}]}

    def _is_json_response(self, response: APIResponse) -> bool:
        """Check if response is JSON content type."""
        if not response.content_type:
            return False
        return any(ct in response.content_type.lower() for ct in self.JSON_CONTENT_TYPES)

    def _create_templated_response(self, body: str) -> Optional[str]:
        """Create templated response body for dynamic content."""
        try:
            data = json.loads(body)
            templated = self._apply_templates_to_json(data)
            return json.dumps(templated, indent=2) if templated != data else None
        except (json.JSONDecodeError, Exception):
            return None

    def _apply_templates_to_json(self, data: Any) -> Any:
        """Apply WireMock templates to JSON data."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key.lower() in ["id", "uuid"] and isinstance(value, str):
                    # Replace IDs with random UUID template
                    result[key] = "{{randomValue type='UUID'}}"
                elif key.lower().endswith("_id") and isinstance(value, (str, int)):
                    # Replace ID fields with random number template
                    result[key] = "{{randomValue type='NUMERIC' length=8}}"
                elif key.lower() in ["timestamp", "created_at", "updated_at"] and isinstance(
                    value, str
                ):
                    # Replace timestamps with current time template
                    result[key] = "{{now}}"
                elif key.lower() in ["email"] and isinstance(value, str):
                    # Replace emails with random email template
                    result[key] = "{{randomValue type='EMAIL'}}"
                else:
                    result[key] = self._apply_templates_to_json(value)
            return result
        elif isinstance(data, list):
            return [self._apply_templates_to_json(item) for item in data]
        else:
            return data

    def export_to_files(
        self, stubs: List[WireMockStub], output_dir: str = "wiremock/mappings"
    ) -> List[str]:
        """
        Export WireMock stubs to individual JSON files.

        Args:
            stubs: List of WireMock stubs to export
            output_dir: Directory to save the mapping files

        Returns:
            List of created file paths
        """
        import os

        os.makedirs(output_dir, exist_ok=True)
        created_files = []

        for i, stub in enumerate(stubs):
            # Create filename from request details
            method = stub.request.get("method", "unknown").lower()

            # Extract path from URL or urlPattern
            path = "unknown"
            if "url" in stub.request:
                path = stub.request["url"].strip("/").replace("/", "_")
            elif "urlPattern" in stub.request:
                path = stub.request["urlPattern"].strip("/").replace("/", "_")
                # Clean up regex patterns for filename
                path = re.sub(r"[\\{}()\[\].*+?^$|]", "", path)

            if not path or path == "unknown":
                path = f"endpoint_{i}"

            filename = f"{method}_{path}_{i}.json"
            # Clean filename
            filename = re.sub(r"[^\w\-_.]", "_", filename)

            filepath = os.path.join(output_dir, filename)

            # Convert stub to WireMock format
            wiremock_config = {"request": stub.request, "response": stub.response}

            # Add metadata as comment if present
            if stub.metadata:
                wiremock_config["metadata"] = stub.metadata

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(wiremock_config, f, indent=2, ensure_ascii=False)
                created_files.append(filepath)
                logger.info(f"Created WireMock mapping: {filepath}")
            except Exception as e:
                logger.error(f"Failed to write mapping file {filepath}: {e}")

        logger.info(f"Exported {len(created_files)} WireMock mapping files to {output_dir}")
        return created_files


class HARToWireMockService:
    """
    Service class for HAR to WireMock transformation operations.

    Provides high-level interface for transforming HAR data to WireMock
    configurations and managing the transformation process.
    """

    def __init__(
        self, transformer: Optional[HARToWireMockTransformer] = None, wiremock_client=None
    ):
        """
        Initialize the service.

        Args:
            transformer: Custom transformer instance (optional)
            wiremock_client: WireMock client for deployment (optional)
        """
        self.transformer = transformer or HARToWireMockTransformer()
        self.wiremock_client = wiremock_client

    async def transform_and_deploy(
        self,
        interactions: List[APIInteraction],
        base_url: Optional[str] = None,
        clear_existing: bool = False,
    ) -> Dict[str, Any]:
        """
        Transform HAR interactions and deploy to WireMock.

        Args:
            interactions: HAR API interactions to transform
            base_url: Base URL to strip from requests
            clear_existing: Whether to clear existing stubs first

        Returns:
            Dictionary with transformation and deployment results
        """
        if not self.wiremock_client:
            raise ValueError("WireMock client not configured")

        # Transform interactions to stubs
        stubs = self.transformer.transform_interactions(interactions, base_url)

        if not stubs:
            return {
                "success": True,
                "message": "No stubs generated from HAR data",
                "stubs_created": 0,
                "stubs_deployed": 0,
            }

        # Clear existing stubs if requested
        if clear_existing:
            await self.wiremock_client.clear_stubs()

        # Deploy stubs
        deployed_count = 0
        errors = []

        for stub in stubs:
            try:
                await self.wiremock_client.create_stub(stub)
                deployed_count += 1
            except Exception as e:
                errors.append(f"Failed to deploy stub: {e}")
                logger.error(f"Failed to deploy stub: {e}")

        return {
            "success": len(errors) == 0,
            "message": f"Transformed {len(stubs)} stubs, deployed {deployed_count}",
            "stubs_created": len(stubs),
            "stubs_deployed": deployed_count,
            "errors": errors,
        }

    def transform_to_files(
        self,
        interactions: List[APIInteraction],
        output_dir: str = "wiremock/mappings",
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transform HAR interactions and save to files.

        Args:
            interactions: HAR API interactions to transform
            output_dir: Directory to save mapping files
            base_url: Base URL to strip from requests

        Returns:
            Dictionary with transformation results
        """
        # Transform interactions to stubs
        stubs = self.transformer.transform_interactions(interactions, base_url)

        if not stubs:
            return {
                "success": True,
                "message": "No stubs generated from HAR data",
                "stubs_created": 0,
                "files_created": [],
            }

        # Export to files
        created_files = self.transformer.export_to_files(stubs, output_dir)

        return {
            "success": True,
            "message": f"Transformed {len(stubs)} stubs to {len(created_files)} files",
            "stubs_created": len(stubs),
            "files_created": created_files,
            "output_directory": output_dir,
        }
