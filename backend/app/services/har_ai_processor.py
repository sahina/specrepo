import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlparse

from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


@dataclass
class DataPattern:
    """Represents a detected data pattern."""

    pattern_type: str
    confidence: float
    original_value: str
    generalized_value: str
    description: str


@dataclass
class SensitiveDataMatch:
    """Represents detected sensitive data."""

    data_type: str
    location: str  # header, body, url, etc.
    field_name: str
    value: str
    confidence: float
    suggested_replacement: str


@dataclass
class GeneralizedData:
    """Represents generalized data for mock responses."""

    original: Any
    generalized: Any
    patterns: List[DataPattern]
    sensitive_matches: List[SensitiveDataMatch]


class HARDataPatternRecognizer:
    """
    Recognizes patterns in HAR data for AI-powered generalization.

    This class implements pattern recognition for various data types including
    dates, emails, IDs, UUIDs, phone numbers, and other common API data patterns.
    """

    # Pattern definitions for common data types
    PATTERNS = {
        "email": {
            "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "placeholder": "user@example.com",
            "description": "Email address",
        },
        "uuid": {
            "regex": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            "placeholder": "{{uuid}}",
            "description": "UUID identifier",
        },
        "phone": {
            "regex": r"(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})",
            "placeholder": "+1-555-123-4567",
            "description": "Phone number",
        },
        "credit_card": {
            "regex": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "placeholder": "****-****-****-1234",
            "description": "Credit card number",
        },
        "ssn": {
            "regex": r"\b\d{3}-\d{2}-\d{4}\b",
            "placeholder": "XXX-XX-XXXX",
            "description": "Social Security Number",
        },
        "ip_address": {
            "regex": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
            "placeholder": "192.168.1.1",
            "description": "IP address",
        },
        "url": {
            "regex": r"https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?",
            "placeholder": "https://api.example.com/resource",
            "description": "URL",
        },
        "numeric_id": {
            "regex": r"\b\d{6,}\b",  # 6+ digit numbers likely to be IDs
            "placeholder": "{{integer}}",
            "description": "Numeric identifier",
        },
        "iso_date": {
            "regex": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})",
            "placeholder": "{{datetime}}",
            "description": "ISO 8601 datetime",
        },
        "simple_date": {
            "regex": r"\b\d{4}-\d{2}-\d{2}\b",
            "placeholder": "{{date}}",
            "description": "Date (YYYY-MM-DD)",
        },
    }

    # Sensitive data patterns
    SENSITIVE_PATTERNS = {
        "api_key": {
            "regex": (
                r"(?i)(api[_-]?key|apikey|access[_-]?token|secret[_-]?key)\s*[:=]\s*"
                r'["\']?([a-zA-Z0-9_-]{20,})["\']?'
            ),
            "replacement": "[REDACTED_API_KEY]",
            "confidence": 0.9,
        },
        "bearer_token": {
            "regex": r"(?i)bearer\s+([a-zA-Z0-9_-]{20,})",
            "replacement": "[REDACTED_BEARER_TOKEN]",
            "confidence": 0.95,
        },
        "jwt_token": {
            "regex": r"(?i)eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
            "replacement": "[REDACTED_JWT_TOKEN]",
            "confidence": 0.98,
        },
        "credit_card": {
            "regex": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "replacement": "[REDACTED_CREDIT_CARD]",
            "confidence": 0.9,
        },
        "ssn": {
            "regex": r"\b\d{3}-\d{2}-\d{4}\b",
            "replacement": "[REDACTED_SSN]",
            "confidence": 0.95,
        },
        "session_id": {
            "regex": (
                r"(?i)(session[_-]?id|sessionid|jsessionid)\s*[:=]\s*"
                r'["\']?([a-zA-Z0-9_-]{10,})["\']?'
            ),
            "replacement": "[REDACTED_SESSION]",
            "confidence": 0.85,
        },
    }

    def __init__(self):
        """Initialize the pattern recognizer."""
        self.compiled_patterns = {
            name: re.compile(pattern["regex"], re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }
        self.compiled_sensitive = {
            name: re.compile(pattern["regex"], re.IGNORECASE)
            for name, pattern in self.SENSITIVE_PATTERNS.items()
        }

    def detect_patterns(self, text: str) -> List[DataPattern]:
        """
        Detect data patterns in text.

        Args:
            text: Text to analyze

        Returns:
            List of detected patterns
        """
        patterns = []

        for pattern_name, regex in self.compiled_patterns.items():
            matches = regex.finditer(text)
            for match in matches:
                pattern_info = self.PATTERNS[pattern_name]
                confidence = self._calculate_confidence(pattern_name, match.group())

                pattern = DataPattern(
                    pattern_type=pattern_name,
                    confidence=confidence,
                    original_value=match.group(),
                    generalized_value=pattern_info["placeholder"],
                    description=pattern_info["description"],
                )
                patterns.append(pattern)

        return patterns

    def detect_sensitive_data(
        self, text: str, location: str = "unknown"
    ) -> List[SensitiveDataMatch]:
        """
        Detect sensitive data in text.

        Args:
            text: Text to analyze
            location: Location context (header, body, url, etc.)

        Returns:
            List of sensitive data matches
        """
        matches = []

        for pattern_name, pattern_info in self.SENSITIVE_PATTERNS.items():
            regex = self.compiled_sensitive[pattern_name]
            for match in regex.finditer(text):
                sensitive_match = SensitiveDataMatch(
                    data_type=pattern_name,
                    location=location,
                    field_name=match.group(1) if match.groups() else pattern_name,
                    value=match.group(),
                    confidence=pattern_info["confidence"],
                    suggested_replacement=pattern_info["replacement"],
                )
                matches.append(sensitive_match)

        return matches

    def _calculate_confidence(self, pattern_type: str, value: str) -> float:
        """Calculate confidence score for a pattern match."""
        base_confidence = 0.7

        # Adjust confidence based on pattern type and value characteristics
        if pattern_type == "email":
            # Higher confidence for common email domains
            if any(domain in value.lower() for domain in ["gmail.com", "yahoo.com", "outlook.com"]):
                return min(0.95, base_confidence + 0.2)
        elif pattern_type == "uuid":
            # UUIDs have very high confidence due to specific format
            return 0.95
        elif pattern_type == "numeric_id":
            # Lower confidence for numeric IDs as they could be other numbers
            return 0.6
        elif pattern_type in ["iso_date", "simple_date"]:
            # Check if it looks like a date
            if any(pattern in value.lower() for pattern in ["date", "time", "created", "updated"]):
                try:
                    date_parser.parse(value)
                    return 0.9
                except (ValueError, TypeError):
                    return 0.5

        return base_confidence


class HARDataGeneralizer:
    """
    Generalizes HAR data for creating reusable mock responses.

    This class processes HAR data to create generalized versions suitable
    for mock responses, replacing specific values with placeholders and
    templates.
    """

    def __init__(self):
        """Initialize the data generalizer."""
        self.pattern_recognizer = HARDataPatternRecognizer()

    def generalize_json_data(self, data: Any) -> GeneralizedData:
        """
        Generalize JSON data by replacing specific values with placeholders.

        Args:
            data: JSON data to generalize

        Returns:
            GeneralizedData object with original, generalized, and analysis
        """
        patterns = []
        sensitive_matches = []
        generalized = self._generalize_recursive(data, patterns, sensitive_matches)

        return GeneralizedData(
            original=data,
            generalized=generalized,
            patterns=patterns,
            sensitive_matches=sensitive_matches,
        )

    def generalize_headers(self, headers: Dict[str, str]) -> GeneralizedData:
        """
        Generalize HTTP headers by detecting and replacing sensitive data.

        Args:
            headers: Dictionary of HTTP headers

        Returns:
            GeneralizedData object with generalized headers
        """
        patterns = []
        sensitive_matches = []
        generalized_headers = {}

        for key, value in headers.items():
            # Check for sensitive data in header values
            header_sensitive = self.pattern_recognizer.detect_sensitive_data(
                f"{key}: {value}", location="header"
            )
            sensitive_matches.extend(header_sensitive)

            # Generalize header value
            generalized_value = value
            for match in header_sensitive:
                generalized_value = generalized_value.replace(
                    match.value, match.suggested_replacement
                )

            # Detect other patterns in header values
            header_patterns = self.pattern_recognizer.detect_patterns(value)
            patterns.extend(header_patterns)

            # Apply pattern generalizations
            for pattern in header_patterns:
                generalized_value = generalized_value.replace(
                    pattern.original_value, pattern.generalized_value
                )

            generalized_headers[key] = generalized_value

        return GeneralizedData(
            original=headers,
            generalized=generalized_headers,
            patterns=patterns,
            sensitive_matches=sensitive_matches,
        )

    def generalize_url(self, url: str) -> GeneralizedData:
        """
        Generalize URL by replacing specific values with placeholders.

        Args:
            url: URL to generalize

        Returns:
            GeneralizedData object with generalized URL
        """
        patterns = []
        sensitive_matches = []

        # Parse URL components
        parsed = urlparse(url)

        # Check for sensitive data in URL
        url_sensitive = self.pattern_recognizer.detect_sensitive_data(url, location="url")
        sensitive_matches.extend(url_sensitive)

        # Detect patterns in URL
        url_patterns = self.pattern_recognizer.detect_patterns(url)
        patterns.extend(url_patterns)

        # Generalize path parameters (numeric IDs, UUIDs)
        generalized_path = self._generalize_path_parameters(parsed.path)

        # Reconstruct URL
        generalized_url = f"{parsed.scheme}://{parsed.netloc}{generalized_path}"
        if parsed.query:
            generalized_url += f"?{parsed.query}"
        if parsed.fragment:
            generalized_url += f"#{parsed.fragment}"

        # Apply sensitive data replacements
        for match in sensitive_matches:
            generalized_url = generalized_url.replace(match.value, match.suggested_replacement)

        return GeneralizedData(
            original=url,
            generalized=generalized_url,
            patterns=patterns,
            sensitive_matches=sensitive_matches,
        )

    def _generalize_recursive(
        self, data: Any, patterns: List[DataPattern], sensitive_matches: List[SensitiveDataMatch]
    ) -> Any:
        """Recursively generalize data structures."""
        if isinstance(data, dict):
            generalized = {}
            for key, value in data.items():
                generalized[key] = self._generalize_recursive(value, patterns, sensitive_matches)
            return generalized
        elif isinstance(data, list):
            return [self._generalize_recursive(item, patterns, sensitive_matches) for item in data]
        elif isinstance(data, str):
            return self._generalize_string_value(data, patterns, sensitive_matches)
        else:
            return data

    def _generalize_string_value(
        self, value: str, patterns: List[DataPattern], sensitive_matches: List[SensitiveDataMatch]
    ) -> str:
        """Generalize a string value by detecting and replacing patterns."""
        # Check for sensitive data
        sensitive = self.pattern_recognizer.detect_sensitive_data(value, location="body")
        sensitive_matches.extend(sensitive)

        # Detect patterns
        detected_patterns = self.pattern_recognizer.detect_patterns(value)
        patterns.extend(detected_patterns)

        generalized_value = value

        # Apply sensitive data replacements first (higher priority)
        for match in sensitive:
            generalized_value = generalized_value.replace(match.value, match.suggested_replacement)

        # Apply pattern generalizations
        for pattern in detected_patterns:
            if pattern.original_value in generalized_value:
                generalized_value = generalized_value.replace(
                    pattern.original_value, pattern.generalized_value
                )

        return generalized_value

    def _generalize_path_parameters(self, path: str) -> str:
        """Generalize path parameters in URL paths."""
        # Replace numeric IDs with placeholders
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        # Replace UUIDs with placeholders
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)",
            "/{uuid}",
            path,
            flags=re.IGNORECASE,
        )

        return path


class HARTypeInferencer:
    """
    Infers data types from HAR data for API parameters and responses.

    This class analyzes HAR data to infer appropriate data types for
    OpenAPI schema generation and mock data creation.
    """

    def __init__(self):
        """Initialize the type inferencer."""
        self.pattern_recognizer = HARDataPatternRecognizer()

    def infer_type(self, value: Any) -> Dict[str, Any]:
        """
        Infer OpenAPI schema type from a value.

        Args:
            value: Value to analyze

        Returns:
            OpenAPI schema type definition
        """
        if value is None:
            return {"type": "null"}
        elif isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, int):
            return {"type": "integer", "format": "int64"}
        elif isinstance(value, float):
            return {"type": "number", "format": "double"}
        elif isinstance(value, str):
            return self._infer_string_type(value)
        elif isinstance(value, list):
            return self._infer_array_type(value)
        elif isinstance(value, dict):
            return self._infer_object_type(value)
        else:
            return {"type": "string"}

    def _infer_string_type(self, value: str) -> Dict[str, Any]:
        """Infer specific string type and format."""
        # Detect patterns in the string
        patterns = self.pattern_recognizer.detect_patterns(value)

        # Return specific format based on detected patterns
        for pattern in patterns:
            if pattern.pattern_type == "email":
                return {"type": "string", "format": "email"}
            elif pattern.pattern_type == "uuid":
                return {"type": "string", "format": "uuid"}
            elif pattern.pattern_type == "iso_date":
                return {"type": "string", "format": "date-time"}
            elif pattern.pattern_type == "simple_date":
                return {"type": "string", "format": "date"}
            elif pattern.pattern_type == "url":
                return {"type": "string", "format": "uri"}
            elif pattern.pattern_type == "ip_address":
                return {"type": "string", "format": "ipv4"}

        # Check if it's a numeric string
        try:
            int(value)
            return {"type": "string", "pattern": r"^\d+$", "description": "Numeric string"}
        except ValueError:
            pass

        # Default string type
        schema = {"type": "string"}

        # Add length constraints if reasonable
        if len(value) > 0:
            schema["minLength"] = 1
        if len(value) < 1000:  # Reasonable max length
            schema["maxLength"] = len(value) * 2  # Allow some flexibility

        return schema

    def _infer_array_type(self, value: List[Any]) -> Dict[str, Any]:
        """Infer array type and items schema."""
        if not value:
            return {"type": "array", "items": {}}

        # Analyze first few items to infer item type
        sample_size = min(5, len(value))
        item_schemas = [self.infer_type(item) for item in value[:sample_size]]

        # If all items have the same type, use that
        if len(set(schema.get("type") for schema in item_schemas)) == 1:
            # Use the first item's schema as the base
            items_schema = item_schemas[0]
        else:
            # Mixed types - use a more generic schema
            items_schema = {"oneOf": item_schemas[:3]}  # Limit to first 3 for simplicity

        return {
            "type": "array",
            "items": items_schema,
            "minItems": 0,
            "maxItems": len(value) * 2,  # Allow some flexibility
        }

    def _infer_object_type(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """Infer object type and properties schema."""
        properties = {}
        required = []

        for key, val in value.items():
            properties[key] = self.infer_type(val)
            if val is not None:
                required.append(key)

        schema = {"type": "object", "properties": properties}

        if required:
            schema["required"] = required

        return schema


class HARDataProcessor:
    """
    Main processor for AI-powered HAR data analysis and generalization.

    This class coordinates pattern recognition, sensitive data detection,
    data generalization, and type inference for HAR data processing.
    """

    def __init__(self):
        """Initialize the HAR data processor."""
        self.pattern_recognizer = HARDataPatternRecognizer()
        self.generalizer = HARDataGeneralizer()
        self.type_inferencer = HARTypeInferencer()

    def process_har_interaction(self, interaction) -> Dict[str, Any]:
        """
        Process a single HAR interaction with AI analysis.

        Args:
            interaction: APIInteraction object from HAR parser

        Returns:
            Dictionary containing analysis results
        """
        results = {
            "interaction_id": interaction.entry_id,
            "request_analysis": self._analyze_request(interaction.request),
            "response_analysis": self._analyze_response(interaction.response),
            "generalization_suggestions": [],
            "security_concerns": [],
        }

        # Collect all sensitive data matches
        all_sensitive = []
        all_sensitive.extend(results["request_analysis"]["sensitive_data"])
        all_sensitive.extend(results["response_analysis"]["sensitive_data"])

        # Generate security concerns
        if all_sensitive:
            results["security_concerns"] = self._generate_security_concerns(all_sensitive)

        # Generate generalization suggestions
        results["generalization_suggestions"] = self._generate_generalization_suggestions(
            results["request_analysis"], results["response_analysis"]
        )

        return results

    def _analyze_request(self, request) -> Dict[str, Any]:
        """Analyze API request data."""
        analysis = {
            "url_analysis": self.generalizer.generalize_url(request.url),
            "headers_analysis": self.generalizer.generalize_headers(request.headers),
            "body_analysis": None,
            "sensitive_data": [],
            "detected_patterns": [],
            "inferred_types": {},
        }

        # Analyze request body if present
        if request.body:
            try:
                if request.content_type and "json" in request.content_type.lower():
                    body_data = json.loads(request.body)
                    analysis["body_analysis"] = self.generalizer.generalize_json_data(body_data)
                    analysis["inferred_types"]["body"] = self.type_inferencer.infer_type(body_data)
                else:
                    # Treat as plain text
                    analysis["body_analysis"] = self.generalizer.generalize_json_data(request.body)
            except json.JSONDecodeError:
                # Handle non-JSON body
                analysis["body_analysis"] = self.generalizer.generalize_json_data(request.body)

        # Collect all sensitive data and patterns
        for key, generalized_data in analysis.items():
            if isinstance(generalized_data, GeneralizedData):
                analysis["sensitive_data"].extend(generalized_data.sensitive_matches)
                analysis["detected_patterns"].extend(generalized_data.patterns)

        return analysis

    def _analyze_response(self, response) -> Dict[str, Any]:
        """Analyze API response data."""
        analysis = {
            "headers_analysis": self.generalizer.generalize_headers(response.headers),
            "body_analysis": None,
            "sensitive_data": [],
            "detected_patterns": [],
            "inferred_types": {},
        }

        # Analyze response body if present
        if response.body:
            try:
                if response.content_type and "json" in response.content_type.lower():
                    body_data = json.loads(response.body)
                    analysis["body_analysis"] = self.generalizer.generalize_json_data(body_data)
                    analysis["inferred_types"]["body"] = self.type_inferencer.infer_type(body_data)
                else:
                    # Treat as plain text
                    analysis["body_analysis"] = self.generalizer.generalize_json_data(response.body)
            except json.JSONDecodeError:
                # Handle non-JSON body
                analysis["body_analysis"] = self.generalizer.generalize_json_data(response.body)

        # Collect all sensitive data and patterns
        for key, generalized_data in analysis.items():
            if isinstance(generalized_data, GeneralizedData):
                analysis["sensitive_data"].extend(generalized_data.sensitive_matches)
                analysis["detected_patterns"].extend(generalized_data.patterns)

        return analysis

    def _generate_security_concerns(
        self, sensitive_matches: List[SensitiveDataMatch]
    ) -> List[Dict[str, Any]]:
        """Generate security concern recommendations."""
        concerns = []

        # Group by data type
        by_type = {}
        for match in sensitive_matches:
            if match.data_type not in by_type:
                by_type[match.data_type] = []
            by_type[match.data_type].append(match)

        for data_type, matches in by_type.items():
            concern = {
                "type": data_type,
                "severity": self._get_severity(data_type),
                "count": len(matches),
                "locations": list(set(match.location for match in matches)),
                "recommendation": self._get_security_recommendation(data_type),
                "examples": [match.field_name for match in matches[:3]],  # First 3 examples
            }
            concerns.append(concern)

        return concerns

    def _generate_generalization_suggestions(
        self, request_analysis: Dict[str, Any], response_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for data generalization."""
        suggestions = []

        # URL path parameter suggestions
        if request_analysis["url_analysis"].patterns:
            suggestions.append(
                {
                    "type": "url_parameterization",
                    "description": "Convert specific URL values to path parameters",
                    "original_url": request_analysis["url_analysis"].original,
                    "suggested_url": request_analysis["url_analysis"].generalized,
                    "patterns_found": [
                        p.pattern_type for p in request_analysis["url_analysis"].patterns
                    ],
                }
            )

        # Response data templating suggestions
        if response_analysis["body_analysis"] and response_analysis["body_analysis"].patterns:
            suggestions.append(
                {
                    "type": "response_templating",
                    "description": "Use templated responses for dynamic data",
                    "patterns_found": [
                        p.pattern_type for p in response_analysis["body_analysis"].patterns
                    ],
                    "template_variables": [
                        p.generalized_value for p in response_analysis["body_analysis"].patterns
                    ],
                }
            )

        return suggestions

    def _get_severity(self, data_type: str) -> str:
        """Get severity level for sensitive data type."""
        high_severity = ["password", "credit_card", "ssn", "api_key"]
        medium_severity = ["bearer_token", "jwt_token", "authorization_header"]

        if data_type in high_severity:
            return "high"
        elif data_type in medium_severity:
            return "medium"
        else:
            return "low"

    def _get_security_recommendation(self, data_type: str) -> str:
        """Get security recommendation for data type."""
        recommendations = {
            "api_key": (
                "Remove API keys from HAR files and use environment variables or secure vaults"
            ),
            "bearer_token": ("Replace bearer tokens with placeholder values in mock responses"),
            "jwt_token": "Use mock JWT tokens for testing, never expose real tokens",
            "password": "Never include passwords in API documentation or mock data",
            "credit_card": "Use test credit card numbers for mock responses",
            "ssn": "Replace with fake SSNs or use format-preserving encryption",
            "authorization_header": "Use mock authorization headers for testing",
            "session_id": "Generate new session IDs for each test scenario",
        }

        return recommendations.get(data_type, "Review and sanitize this sensitive data type")
