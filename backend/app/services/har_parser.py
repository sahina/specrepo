import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


@dataclass
class APIRequest:
    """Represents an extracted API request from HAR."""

    method: str
    url: str
    domain: str
    path: str
    query_params: Dict[str, List[str]]
    headers: Dict[str, str]
    body: Optional[str]
    content_type: Optional[str]
    timestamp: str


@dataclass
class APIResponse:
    """Represents an extracted API response from HAR."""

    status: int
    status_text: str
    headers: Dict[str, str]
    body: Optional[str]
    content_type: Optional[str]
    size: int


@dataclass
class APIInteraction:
    """Represents a complete API request-response interaction."""

    request: APIRequest
    response: APIResponse
    duration: float
    entry_id: str


@dataclass
class EndpointGroup:
    """Represents a group of related API endpoints."""

    domain: str
    base_path: str
    interactions: List[APIInteraction]
    methods: Set[str]
    content_types: Set[str]


class HARParser:
    """
    HAR file parser for extracting API interactions.

    This class provides functionality to parse HAR files and extract
    meaningful API interactions, filtering out non-API requests and
    grouping related endpoints.
    """

    # Content types that indicate API requests
    API_CONTENT_TYPES = {
        "application/json",
        "application/xml",
        "application/x-www-form-urlencoded",
        "text/xml",
        "text/json",
        "multipart/form-data",
    }

    # URL patterns that typically indicate non-API requests
    NON_API_PATTERNS = [
        r"\.css$",
        r"\.js$",
        r"\.png$",
        r"\.jpg$",
        r"\.jpeg$",
        r"\.gif$",
        r"\.svg$",
        r"\.ico$",
        r"\.woff$",
        r"\.woff2$",
        r"\.ttf$",
        r"\.eot$",
        r"\.map$",
        r"/static/",
        r"/assets/",
        r"/public/",
        r"\.html$",
        r"\.htm$",
    ]

    # Common API path patterns
    API_PATH_PATTERNS = [
        r"/api/",
        r"/v\d+/",
        r"/rest/",
        r"/graphql",
        r"/webhook",
        r"\.json$",
        r"\.xml$",
    ]

    def __init__(self):
        """Initialize the HAR parser."""
        self.non_api_regex = re.compile("|".join(self.NON_API_PATTERNS), re.IGNORECASE)
        self.api_path_regex = re.compile("|".join(self.API_PATH_PATTERNS), re.IGNORECASE)

    def parse_har_content(self, har_content: str) -> List[APIInteraction]:
        """
        Parse HAR content and extract API interactions.

        Args:
            har_content: Raw HAR file content as string

        Returns:
            List of APIInteraction objects

        Raises:
            ValueError: If HAR content is invalid
            json.JSONDecodeError: If HAR content is not valid JSON
        """
        try:
            har_data = json.loads(har_content)
            return self._extract_api_interactions(har_data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in HAR content: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing HAR content: {e}")
            raise ValueError(f"Failed to parse HAR content: {e}")

    def _extract_api_interactions(self, har_data: dict) -> List[APIInteraction]:
        """Extract API interactions from parsed HAR data."""
        if "log" not in har_data or "entries" not in har_data["log"]:
            raise ValueError("Invalid HAR structure: missing log.entries")

        interactions = []
        entries = har_data["log"]["entries"]

        for i, entry in enumerate(entries):
            try:
                if self._is_api_request(entry):
                    interaction = self._parse_entry(entry, str(i))
                    if interaction:
                        interactions.append(interaction)
            except Exception as e:
                logger.warning(f"Failed to parse entry {i}: {e}")
                continue

        logger.info(
            f"Extracted {len(interactions)} API interactions from {len(entries)} total entries"
        )
        return interactions

    def _is_api_request(self, entry: dict) -> bool:
        """
        Determine if an entry represents an API request.

        Args:
            entry: HAR entry dictionary

        Returns:
            True if the entry appears to be an API request
        """
        try:
            request = entry.get("request", {})
            response = entry.get("response", {})

            url = request.get("url", "")
            method = request.get("method", "").upper()

            # Skip non-HTTP methods
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                return False

            # Check if URL matches non-API patterns
            if self.non_api_regex.search(url):
                return False

            # Check for API-like patterns in URL
            if self.api_path_regex.search(url):
                return True

            # Check request content type
            request_content_type = self._get_content_type(request.get("headers", []))
            if request_content_type and any(
                api_type in request_content_type.lower() for api_type in self.API_CONTENT_TYPES
            ):
                return True

            # Check response content type
            response_content_type = self._get_content_type(response.get("headers", []))
            if response_content_type and any(
                api_type in response_content_type.lower() for api_type in self.API_CONTENT_TYPES
            ):
                return True

            # Check for JSON-like response body
            response_content = response.get("content", {})
            if response_content.get("mimeType", "").lower().startswith("application/json"):
                return True

            # Check for API-like status codes with structured responses
            status = response.get("status", 0)
            if status in [200, 201, 202, 204, 400, 401, 403, 404, 422, 500, 502, 503]:
                # If it's a structured response (JSON/XML), likely an API
                if response_content.get("text"):
                    try:
                        json.loads(response_content["text"])
                        return True
                    except (json.JSONDecodeError, TypeError):
                        pass

            return False

        except Exception as e:
            logger.warning(f"Error checking if entry is API request: {e}")
            return False

    def _parse_entry(self, entry: dict, entry_id: str) -> Optional[APIInteraction]:
        """Parse a single HAR entry into an APIInteraction."""
        try:
            request_data = entry["request"]
            response_data = entry["response"]

            # Parse request
            request = self._parse_request(request_data, entry.get("startedDateTime", ""))
            if not request:
                return None

            # Parse response
            response = self._parse_response(response_data)
            if not response:
                return None

            # Calculate duration
            duration = entry.get("time", 0)

            return APIInteraction(
                request=request, response=response, duration=duration, entry_id=entry_id
            )

        except Exception as e:
            logger.warning(f"Failed to parse entry {entry_id}: {e}")
            return None

    def _parse_request(self, request_data: dict, timestamp: str) -> Optional[APIRequest]:
        """Parse request data from HAR entry."""
        try:
            url = request_data.get("url", "")
            method = request_data.get("method", "").upper()

            # Parse URL components
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            # Parse headers
            headers = self._parse_headers(request_data.get("headers", []))

            # Get content type
            content_type = self._get_content_type(request_data.get("headers", []))

            # Parse body
            body = None
            post_data = request_data.get("postData", {})
            if post_data and "text" in post_data:
                body = post_data["text"]

            return APIRequest(
                method=method,
                url=url,
                domain=domain,
                path=path,
                query_params=query_params,
                headers=headers,
                body=body,
                content_type=content_type,
                timestamp=timestamp,
            )

        except Exception as e:
            logger.warning(f"Failed to parse request: {e}")
            return None

    def _parse_response(self, response_data: dict) -> Optional[APIResponse]:
        """Parse response data from HAR entry."""
        try:
            status = response_data.get("status", 0)
            status_text = response_data.get("statusText", "")

            # Parse headers
            headers = self._parse_headers(response_data.get("headers", []))

            # Get content type
            content_type = self._get_content_type(response_data.get("headers", []))

            # Parse body
            body = None
            content = response_data.get("content", {})
            if content and "text" in content:
                body = content["text"]

            # Get size
            size = response_data.get("bodySize", 0)
            if size < 0:  # HAR spec allows -1 for unknown size
                size = len(body) if body else 0

            return APIResponse(
                status=status,
                status_text=status_text,
                headers=headers,
                body=body,
                content_type=content_type,
                size=size,
            )

        except Exception as e:
            logger.warning(f"Failed to parse response: {e}")
            return None

    def _parse_headers(self, headers_list: List[dict]) -> Dict[str, str]:
        """Parse headers from HAR format to dictionary."""
        headers = {}
        for header in headers_list:
            if isinstance(header, dict) and "name" in header and "value" in header:
                headers[header["name"].lower()] = header["value"]
        return headers

    def _get_content_type(self, headers_list: List[dict]) -> Optional[str]:
        """Extract content-type from headers list."""
        for header in headers_list:
            if isinstance(header, dict) and header.get("name", "").lower() == "content-type":
                return header.get("value", "").split(";")[0].strip()
        return None

    def group_endpoints(self, interactions: List[APIInteraction]) -> List[EndpointGroup]:
        """
        Group API interactions by domain and base path.

        Args:
            interactions: List of API interactions

        Returns:
            List of EndpointGroup objects
        """
        groups = {}

        for interaction in interactions:
            domain = interaction.request.domain
            path = interaction.request.path

            # Extract base path (remove specific IDs and parameters)
            base_path = self._extract_base_path(path)

            # Create group key
            group_key = f"{domain}:{base_path}"

            if group_key not in groups:
                groups[group_key] = EndpointGroup(
                    domain=domain,
                    base_path=base_path,
                    interactions=[],
                    methods=set(),
                    content_types=set(),
                )

            group = groups[group_key]
            group.interactions.append(interaction)
            group.methods.add(interaction.request.method)

            if interaction.request.content_type:
                group.content_types.add(interaction.request.content_type)
            if interaction.response.content_type:
                group.content_types.add(interaction.response.content_type)

        # Sort groups by domain and base path
        sorted_groups = sorted(groups.values(), key=lambda g: (g.domain, g.base_path))

        logger.info(
            f"Grouped {len(interactions)} interactions into {len(sorted_groups)} endpoint groups"
        )
        return sorted_groups

    def _extract_base_path(self, path: str) -> str:
        """
        Extract base path by removing specific IDs and parameters.

        Examples:
            /api/users/123 -> /api/users/{id}
            /api/orders/456/items/789 -> /api/orders/{id}/items/{id}
            /v1/products -> /v1/products
            /v1/users -> /v1/users/{id}  # Normalize collection endpoints
        """
        if not path:
            return "/"

        # Split path into segments
        segments = [seg for seg in path.split("/") if seg]

        # Replace numeric IDs and UUIDs with placeholders
        normalized_segments = []
        for segment in segments:
            # Check if segment is a numeric ID
            if segment.isdigit():
                normalized_segments.append("{id}")
            # Check if segment is a UUID
            elif re.match(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                segment,
                re.IGNORECASE,
            ):
                normalized_segments.append("{uuid}")
            # Check if segment looks like an ID (alphanumeric with certain patterns)
            elif re.match(r"^[a-zA-Z0-9_-]{8,}$", segment) and any(c.isdigit() for c in segment):
                normalized_segments.append("{id}")
            else:
                normalized_segments.append(segment)

        base_path = "/" + "/".join(normalized_segments)

        # For collection endpoints (like /users), add {id} to group with item endpoints
        # This helps group /users and /users/123 together as /users/{id}
        if base_path and not base_path.endswith("/{id}") and not base_path.endswith("/{uuid}"):
            # Check if this looks like a collection endpoint (plural noun)
            last_segment = normalized_segments[-1] if normalized_segments else ""
            if last_segment and (
                last_segment.endswith("s")  # plural nouns
                or last_segment
                in ["users", "products", "orders", "items", "posts", "comments", "files", "data"]
            ):
                base_path += "/{id}"

        return base_path

    def filter_interactions(
        self,
        interactions: List[APIInteraction],
        domains: Optional[List[str]] = None,
        methods: Optional[List[str]] = None,
        status_codes: Optional[List[int]] = None,
        content_types: Optional[List[str]] = None,
    ) -> List[APIInteraction]:
        """
        Filter API interactions based on various criteria.

        Args:
            interactions: List of API interactions to filter
            domains: List of domains to include (if None, include all)
            methods: List of HTTP methods to include (if None, include all)
            status_codes: List of status codes to include (if None, include all)
            content_types: List of content types to include (if None, include all)

        Returns:
            Filtered list of API interactions
        """
        filtered = interactions

        if domains:
            domains_lower = [d.lower() for d in domains]
            filtered = [i for i in filtered if i.request.domain.lower() in domains_lower]

        if methods:
            methods_upper = [m.upper() for m in methods]
            filtered = [i for i in filtered if i.request.method in methods_upper]

        if status_codes:
            filtered = [i for i in filtered if i.response.status in status_codes]

        if content_types:
            content_types_lower = [ct.lower() for ct in content_types]
            filtered = [
                i
                for i in filtered
                if (
                    i.request.content_type
                    and any(ct in i.request.content_type.lower() for ct in content_types_lower)
                )
                or (
                    i.response.content_type
                    and any(ct in i.response.content_type.lower() for ct in content_types_lower)
                )
            ]

        logger.info(
            f"Filtered {len(interactions)} interactions to {len(filtered)} based on criteria"
        )
        return filtered

    def get_summary_stats(self, interactions: List[APIInteraction]) -> Dict[str, any]:
        """
        Generate summary statistics for API interactions.

        Args:
            interactions: List of API interactions

        Returns:
            Dictionary containing summary statistics
        """
        if not interactions:
            return {
                "total_interactions": 0,
                "unique_domains": 0,
                "unique_paths": 0,
                "methods": {},
                "status_codes": {},
                "content_types": [],
                "avg_duration": 0,
                "total_response_size": 0,
            }

        domains = set()
        paths = set()
        methods = {}
        status_codes = {}
        content_types = set()
        total_duration = 0
        total_size = 0

        for interaction in interactions:
            domains.add(interaction.request.domain)
            paths.add(interaction.request.path)

            # Count methods
            method = interaction.request.method
            methods[method] = methods.get(method, 0) + 1

            # Count status codes
            status = interaction.response.status
            status_codes[status] = status_codes.get(status, 0) + 1

            # Collect content types
            if interaction.request.content_type:
                content_types.add(interaction.request.content_type)
            if interaction.response.content_type:
                content_types.add(interaction.response.content_type)

            total_duration += interaction.duration
            total_size += interaction.response.size

        return {
            "total_interactions": len(interactions),
            "unique_domains": len(domains),
            "unique_paths": len(paths),
            "methods": methods,
            "status_codes": status_codes,
            "content_types": list(content_types),
            "avg_duration": total_duration / len(interactions) if interactions else 0,
            "total_response_size": total_size,
        }
