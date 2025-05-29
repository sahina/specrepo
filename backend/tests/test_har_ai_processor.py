import json
from unittest.mock import Mock

import pytest

from app.services.har_ai_processor import (
    DataPattern,
    GeneralizedData,
    HARDataGeneralizer,
    HARDataPatternRecognizer,
    HARDataProcessor,
    HARTypeInferencer,
    SensitiveDataMatch,
)
from app.services.har_parser import APIInteraction, APIRequest, APIResponse


class TestHARDataPatternRecognizer:
    """Test the pattern recognition functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.recognizer = HARDataPatternRecognizer()

    def test_detect_email_patterns(self):
        """Test email pattern detection."""
        text = "Contact us at support@example.com or admin@test.org"
        patterns = self.recognizer.detect_patterns(text)

        email_patterns = [p for p in patterns if p.pattern_type == "email"]
        assert len(email_patterns) == 2
        assert email_patterns[0].original_value == "support@example.com"
        assert email_patterns[0].generalized_value == "user@example.com"
        assert email_patterns[0].confidence >= 0.7

    def test_detect_uuid_patterns(self):
        """Test UUID pattern detection."""
        text = "User ID: 550e8400-e29b-41d4-a716-446655440000"
        patterns = self.recognizer.detect_patterns(text)

        uuid_patterns = [p for p in patterns if p.pattern_type == "uuid"]
        assert len(uuid_patterns) == 1
        assert uuid_patterns[0].original_value == "550e8400-e29b-41d4-a716-446655440000"
        assert uuid_patterns[0].generalized_value == "{{uuid}}"
        assert uuid_patterns[0].confidence == 0.95

    def test_detect_phone_patterns(self):
        """Test phone number pattern detection."""
        text = "Call us at +1-555-123-4567 or (555) 987-6543"
        patterns = self.recognizer.detect_patterns(text)

        phone_patterns = [p for p in patterns if p.pattern_type == "phone"]
        assert len(phone_patterns) >= 1
        assert phone_patterns[0].generalized_value == "+1-555-123-4567"

    def test_detect_date_patterns(self):
        """Test date pattern detection."""
        text = "Created on 2023-12-25 at 2023-12-25T10:30:00Z"
        patterns = self.recognizer.detect_patterns(text)

        date_patterns = [p for p in patterns if "date" in p.pattern_type]
        assert len(date_patterns) >= 1

    def test_detect_sensitive_api_key(self):
        """Test API key detection."""
        text = "api_key: sk-1234567890abcdef1234567890abcdef"
        matches = self.recognizer.detect_sensitive_data(text, "header")

        api_key_matches = [m for m in matches if m.data_type == "api_key"]
        assert len(api_key_matches) >= 1
        assert api_key_matches[0].confidence >= 0.8
        assert api_key_matches[0].suggested_replacement == "[REDACTED_API_KEY]"

    def test_detect_sensitive_bearer_token(self):
        """Test bearer token detection."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        matches = self.recognizer.detect_sensitive_data(text, "header")

        bearer_matches = [m for m in matches if m.data_type == "bearer_token"]
        assert len(bearer_matches) >= 1
        assert bearer_matches[0].confidence >= 0.9

    def test_detect_sensitive_jwt_token(self):
        """Test JWT token detection."""
        text = "token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        matches = self.recognizer.detect_sensitive_data(text, "body")

        jwt_matches = [m for m in matches if m.data_type == "jwt_token"]
        assert len(jwt_matches) >= 1
        assert jwt_matches[0].confidence >= 0.9

    def test_confidence_calculation(self):
        """Test confidence calculation for different patterns."""
        # High confidence for UUID
        uuid_patterns = self.recognizer.detect_patterns("550e8400-e29b-41d4-a716-446655440000")
        assert uuid_patterns[0].confidence == 0.95

        # Lower confidence for numeric IDs
        numeric_patterns = self.recognizer.detect_patterns("123456789")
        numeric_id_patterns = [p for p in numeric_patterns if p.pattern_type == "numeric_id"]
        if numeric_id_patterns:
            assert numeric_id_patterns[0].confidence == 0.6


class TestHARDataGeneralizer:
    """Test the data generalization functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generalizer = HARDataGeneralizer()

    def test_generalize_json_data_with_patterns(self):
        """Test JSON data generalization with pattern detection."""
        data = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "created_at": "2023-12-25T10:30:00Z",
            "phone": "+1-555-123-4567",
        }

        result = self.generalizer.generalize_json_data(data)

        assert isinstance(result, GeneralizedData)
        assert result.original == data
        assert len(result.patterns) > 0

        # Check that patterns were detected
        pattern_types = [p.pattern_type for p in result.patterns]
        assert "uuid" in pattern_types
        assert "email" in pattern_types

    def test_generalize_headers_with_sensitive_data(self):
        """Test header generalization with sensitive data."""
        headers = {
            "authorization": "Bearer sk-1234567890abcdef1234567890abcdef",
            "content-type": "application/json",
            "x-api-key": "secret123456789",
        }

        result = self.generalizer.generalize_headers(headers)

        assert isinstance(result, GeneralizedData)
        assert len(result.sensitive_matches) > 0

        # Check that sensitive data was replaced
        generalized_auth = result.generalized.get("authorization", "")
        assert "[REDACTED" in generalized_auth or "Bearer [REDACTED" in generalized_auth

    def test_generalize_url_with_path_parameters(self):
        """Test URL generalization with path parameters."""
        url = "https://api.example.com/users/123456/orders/550e8400-e29b-41d4-a716-446655440000"

        result = self.generalizer.generalize_url(url)

        assert isinstance(result, GeneralizedData)
        assert result.original == url

        # Check that path parameters were generalized
        generalized_url = result.generalized
        assert "/users/{id}/orders/{uuid}" in generalized_url

    def test_generalize_nested_json_data(self):
        """Test generalization of nested JSON structures."""
        data = {
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "profile": {
                    "email": "user@example.com",
                    "contacts": [{"phone": "+1-555-123-4567"}, {"phone": "+1-555-987-6543"}],
                },
            },
            "metadata": {"created": "2023-12-25T10:30:00Z"},
        }

        result = self.generalizer.generalize_json_data(data)

        assert isinstance(result, GeneralizedData)
        assert len(result.patterns) > 0

        # Verify nested structure is preserved
        assert "user" in result.generalized
        assert "profile" in result.generalized["user"]


class TestHARTypeInferencer:
    """Test the type inference functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.inferencer = HARTypeInferencer()

    def test_infer_basic_types(self):
        """Test inference of basic data types."""
        # Test null
        assert self.inferencer.infer_type(None) == {"type": "null"}

        # Test boolean
        assert self.inferencer.infer_type(True) == {"type": "boolean"}

        # Test integer
        result = self.inferencer.infer_type(42)
        assert result["type"] == "integer"
        assert result["format"] == "int64"

        # Test float
        result = self.inferencer.infer_type(3.14)
        assert result["type"] == "number"
        assert result["format"] == "double"

    def test_infer_string_formats(self):
        """Test inference of string formats."""
        # Test email
        result = self.inferencer.infer_type("user@example.com")
        assert result["type"] == "string"
        assert result["format"] == "email"

        # Test UUID
        result = self.inferencer.infer_type("550e8400-e29b-41d4-a716-446655440000")
        assert result["type"] == "string"
        assert result["format"] == "uuid"

        # Test date-time
        result = self.inferencer.infer_type("2023-12-25T10:30:00Z")
        assert result["type"] == "string"
        assert result["format"] == "date-time"

        # Test date
        result = self.inferencer.infer_type("2023-12-25")
        assert result["type"] == "string"
        assert result["format"] == "date"

    def test_infer_array_types(self):
        """Test inference of array types."""
        # Test empty array
        result = self.inferencer.infer_type([])
        assert result["type"] == "array"
        assert result["items"] == {}

        # Test homogeneous array
        result = self.inferencer.infer_type([1, 2, 3])
        assert result["type"] == "array"
        assert result["items"]["type"] == "integer"

        # Test mixed array
        result = self.inferencer.infer_type([1, "hello", True])
        assert result["type"] == "array"
        assert "oneOf" in result["items"]

    def test_infer_object_types(self):
        """Test inference of object types."""
        data = {
            "id": 123,
            "name": "John Doe",
            "email": "john@example.com",
            "active": True,
            "metadata": None,
        }

        result = self.inferencer.infer_type(data)

        assert result["type"] == "object"
        assert "properties" in result
        assert "required" in result

        # Check property types
        props = result["properties"]
        assert props["id"]["type"] == "integer"
        assert props["name"]["type"] == "string"
        assert props["email"]["format"] == "email"
        assert props["active"]["type"] == "boolean"
        assert props["metadata"]["type"] == "null"

        # Check required fields (non-null values)
        required = result["required"]
        assert "id" in required
        assert "name" in required
        assert "email" in required
        assert "active" in required
        assert "metadata" not in required


class TestHARDataProcessor:
    """Test the main HAR data processor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = HARDataProcessor()

    def create_mock_interaction(self):
        """Create a mock API interaction for testing."""
        request = Mock(spec=APIRequest)
        request.url = "https://api.example.com/users/123456"
        request.headers = {
            "authorization": "Bearer sk-1234567890abcdef1234567890abcdef",
            "content-type": "application/json",
        }
        request.body = json.dumps(
            {"email": "user@example.com", "user_id": "550e8400-e29b-41d4-a716-446655440000"}
        )
        request.content_type = "application/json"

        response = Mock(spec=APIResponse)
        response.headers = {"content-type": "application/json"}
        response.body = json.dumps(
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "created_at": "2023-12-25T10:30:00Z",
                "api_key": "secret123456789",
            }
        )
        response.content_type = "application/json"

        interaction = Mock(spec=APIInteraction)
        interaction.entry_id = "test_entry_1"
        interaction.request = request
        interaction.response = response

        return interaction

    def test_process_har_interaction(self):
        """Test processing a complete HAR interaction."""
        interaction = self.create_mock_interaction()

        result = self.processor.process_har_interaction(interaction)

        # Check result structure
        assert "interaction_id" in result
        assert "request_analysis" in result
        assert "response_analysis" in result
        assert "generalization_suggestions" in result
        assert "security_concerns" in result

        assert result["interaction_id"] == "test_entry_1"

    def test_request_analysis(self):
        """Test request analysis functionality."""
        interaction = self.create_mock_interaction()

        result = self.processor.process_har_interaction(interaction)
        request_analysis = result["request_analysis"]

        # Check analysis components
        assert "url_analysis" in request_analysis
        assert "headers_analysis" in request_analysis
        assert "body_analysis" in request_analysis
        assert "sensitive_data" in request_analysis
        assert "detected_patterns" in request_analysis
        assert "inferred_types" in request_analysis

        # Check that sensitive data was detected
        assert len(request_analysis["sensitive_data"]) > 0

    def test_response_analysis(self):
        """Test response analysis functionality."""
        interaction = self.create_mock_interaction()

        result = self.processor.process_har_interaction(interaction)
        response_analysis = result["response_analysis"]

        # Check analysis components
        assert "headers_analysis" in response_analysis
        assert "body_analysis" in response_analysis
        assert "sensitive_data" in response_analysis
        assert "detected_patterns" in response_analysis
        assert "inferred_types" in response_analysis

    def test_security_concerns_generation(self):
        """Test security concerns generation."""
        interaction = self.create_mock_interaction()

        result = self.processor.process_har_interaction(interaction)
        security_concerns = result["security_concerns"]

        # Should have security concerns due to sensitive data
        assert len(security_concerns) > 0

        # Check concern structure
        concern = security_concerns[0]
        assert "type" in concern
        assert "severity" in concern
        assert "count" in concern
        assert "locations" in concern
        assert "recommendation" in concern
        assert "examples" in concern

    def test_generalization_suggestions(self):
        """Test generalization suggestions generation."""
        interaction = self.create_mock_interaction()

        result = self.processor.process_har_interaction(interaction)
        suggestions = result["generalization_suggestions"]

        # Should have suggestions for URL parameterization
        url_suggestions = [s for s in suggestions if s["type"] == "url_parameterization"]
        assert len(url_suggestions) > 0

        # Check suggestion structure
        if url_suggestions:
            suggestion = url_suggestions[0]
            assert "description" in suggestion
            assert "original_url" in suggestion
            assert "suggested_url" in suggestion
            assert "patterns_found" in suggestion

    def test_severity_classification(self):
        """Test severity classification for different data types."""
        # Test high severity
        assert self.processor._get_severity("api_key") == "high"
        assert self.processor._get_severity("password") == "high"
        assert self.processor._get_severity("credit_card") == "high"

        # Test medium severity
        assert self.processor._get_severity("bearer_token") == "medium"
        assert self.processor._get_severity("jwt_token") == "medium"

        # Test low severity (default)
        assert self.processor._get_severity("unknown_type") == "low"

    def test_security_recommendations(self):
        """Test security recommendations for different data types."""
        # Test specific recommendations
        rec = self.processor._get_security_recommendation("api_key")
        assert "environment variables" in rec.lower() or "secure vaults" in rec.lower()

        rec = self.processor._get_security_recommendation("password")
        assert "never include" in rec.lower()

        # Test default recommendation
        rec = self.processor._get_security_recommendation("unknown_type")
        assert "review and sanitize" in rec.lower()


@pytest.mark.integration
class TestHARDataProcessorIntegration:
    """Integration tests for the HAR data processor."""

    def test_end_to_end_processing(self):
        """Test end-to-end processing with realistic data."""
        processor = HARDataProcessor()

        # Create realistic test data
        request = Mock(spec=APIRequest)
        request.url = "https://api.stripe.com/v1/customers/cus_1234567890/charges"
        request.headers = {
            "authorization": "Bearer sk_test_1234567890abcdef1234567890abcdef",
            "content-type": "application/json",
            "user-agent": "MyApp/1.0",
        }
        request.body = json.dumps(
            {
                "amount": 2000,
                "currency": "usd",
                "customer": "cus_1234567890",
                "description": "Payment for order #12345",
                "metadata": {
                    "order_id": "550e8400-e29b-41d4-a716-446655440000",
                    "customer_email": "customer@example.com",
                },
            }
        )
        request.content_type = "application/json"

        response = Mock(spec=APIResponse)
        response.headers = {"content-type": "application/json", "request-id": "req_1234567890"}
        response.body = json.dumps(
            {
                "id": "ch_1234567890",
                "object": "charge",
                "amount": 2000,
                "currency": "usd",
                "customer": "cus_1234567890",
                "created": 1640419800,
                "description": "Payment for order #12345",
                "metadata": {
                    "order_id": "550e8400-e29b-41d4-a716-446655440000",
                    "customer_email": "customer@example.com",
                },
                "receipt_url": "https://pay.stripe.com/receipts/payment/CAcQARoXChVhY2N0XzFCbEZKcUlxWWlPbkNhUmcQAg",
            }
        )
        response.content_type = "application/json"

        interaction = Mock(spec=APIInteraction)
        interaction.entry_id = "stripe_charge_test"
        interaction.request = request
        interaction.response = response

        # Process the interaction
        result = processor.process_har_interaction(interaction)

        # Verify comprehensive analysis
        assert result["interaction_id"] == "stripe_charge_test"

        # Should detect sensitive data (API key)
        assert len(result["security_concerns"]) > 0
        api_key_concerns = [
            c
            for c in result["security_concerns"]
            if "api_key" in c["type"] or "bearer_token" in c["type"]
        ]
        assert len(api_key_concerns) > 0

        # Should suggest URL parameterization
        url_suggestions = [
            s for s in result["generalization_suggestions"] if s["type"] == "url_parameterization"
        ]
        assert len(url_suggestions) > 0

        # Should detect patterns (UUID, email)
        all_patterns = []
        all_patterns.extend(result["request_analysis"]["detected_patterns"])
        all_patterns.extend(result["response_analysis"]["detected_patterns"])

        pattern_types = [p.pattern_type for p in all_patterns]
        assert "uuid" in pattern_types
        assert "email" in pattern_types

        # Should infer types correctly
        request_types = result["request_analysis"]["inferred_types"]
        response_types = result["response_analysis"]["inferred_types"]

        assert "body" in request_types
        assert "body" in response_types
        assert request_types["body"]["type"] == "object"
        assert response_types["body"]["type"] == "object"
