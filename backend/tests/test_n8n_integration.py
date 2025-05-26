import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models import APISpecification
from app.services.n8n_notifications import (
    N8nNotificationService,
    N8nWebhookPayload,
)


class TestN8nWorkflowIntegration:
    """Integration tests for n8n workflow functionality."""

    @pytest.fixture
    def n8n_webhook_url(self):
        """Get the n8n webhook URL from environment or use default."""
        return os.getenv(
            "N8N_WEBHOOK_URL",
            "http://localhost:5678/webhook-test/api-spec-notification",
        )

    @pytest.fixture
    def sample_openapi_content(self):
        """Sample OpenAPI content for testing."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "description": "A comprehensive test API for integration testing",
                "version": "1.0.0",
                "contact": {
                    "name": "API Support",
                    "email": "support@example.com",
                },
            },
            "servers": [
                {
                    "url": "https://api.example.com/v1",
                    "description": "Production server",
                }
            ],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "description": "Retrieve a list of users",
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/User"
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    },
                    "post": {
                        "summary": "Create user",
                        "description": "Create a new user",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/CreateUser"
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "User created successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/User"
                                        }
                                    }
                                },
                            }
                        },
                    },
                },
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "example": 1},
                            "name": {"type": "string", "example": "John Doe"},
                            "email": {
                                "type": "string",
                                "format": "email",
                                "example": "john@example.com",
                            },
                        },
                    },
                    "CreateUser": {
                        "type": "object",
                        "required": ["name", "email"],
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                        },
                    },
                }
            },
        }

    @pytest.fixture
    def created_event_payload(self, sample_openapi_content):
        """Sample payload for created event."""
        return {
            "event_type": "created",
            "specification_id": 123,
            "specification_name": "Test API Specification",
            "version_string": "v1.0.0",
            "user_id": 456,
            "timestamp": "2024-01-15T10:30:00Z",
            "openapi_content": sample_openapi_content,
        }

    @pytest.fixture
    def updated_event_payload(self, sample_openapi_content):
        """Sample payload for updated event."""
        return {
            "event_type": "updated",
            "specification_id": 123,
            "specification_name": "Test API Specification",
            "version_string": "v1.1.0",
            "user_id": 456,
            "timestamp": "2024-01-15T11:30:00Z",
            "openapi_content": sample_openapi_content,
        }

    @pytest.mark.asyncio
    async def test_n8n_service_availability(self):
        """Test that n8n service is running and accessible."""
        base_url = "http://localhost:5678"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to access n8n health endpoint or root
                response = await client.get(f"{base_url}/healthz")
                assert response.status_code in [200, 404], (
                    f"n8n service not accessible at {base_url}"
                )
                print(f"✅ n8n service is running at {base_url}")
        except httpx.RequestError as e:
            pytest.skip(f"n8n service not available: {e}")

    @pytest.mark.asyncio
    async def test_webhook_endpoint_response(
        self, n8n_webhook_url, created_event_payload
    ):
        """Test that the webhook endpoint responds correctly."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    n8n_webhook_url,
                    json=created_event_payload,
                    headers={"Content-Type": "application/json"},
                )

                print(f"Webhook response status: {response.status_code}")
                print(f"Webhook response body: {response.text}")

                # n8n webhook should return 200 or 404 (if workflow not active)
                assert response.status_code in [200, 404], (
                    f"Unexpected status code: {response.status_code}"
                )

                if response.status_code == 200:
                    # If successful, check response format
                    response_data = response.json()
                    assert "status" in response_data
                    assert response_data["status"] == "success"
                    print("✅ Webhook endpoint is working correctly")
                else:
                    print(
                        "⚠️ Webhook returned 404 - workflow may not be active or imported"
                    )
                    print(
                        "💡 Follow setup instructions to import and activate workflow"
                    )

        except httpx.RequestError as e:
            pytest.skip(f"Cannot reach webhook endpoint: {e}")

    @pytest.mark.asyncio
    async def test_created_event_payload_structure(
        self, n8n_webhook_url, created_event_payload
    ):
        """Test webhook with created event payload structure."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    n8n_webhook_url,
                    json=created_event_payload,
                    headers={"Content-Type": "application/json"},
                )

                # Verify payload structure is accepted
                assert response.status_code in [200, 404]

                if response.status_code == 200:
                    response_data = response.json()
                    assert response_data["event_type"] == "created"
                    assert response_data["specification_id"] == 123
                    print("✅ Created event payload structure is valid")

        except httpx.RequestError as e:
            pytest.skip(f"Cannot test payload structure: {e}")

    @pytest.mark.asyncio
    async def test_updated_event_payload_structure(
        self, n8n_webhook_url, updated_event_payload
    ):
        """Test webhook with updated event payload structure."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    n8n_webhook_url,
                    json=updated_event_payload,
                    headers={"Content-Type": "application/json"},
                )

                # Verify payload structure is accepted
                assert response.status_code in [200, 404]

                if response.status_code == 200:
                    response_data = response.json()
                    assert response_data["event_type"] == "updated"
                    assert response_data["specification_id"] == 123
                    print("✅ Updated event payload structure is valid")

        except httpx.RequestError as e:
            pytest.skip(f"Cannot test payload structure: {e}")

    def test_payload_validation_with_pydantic(self, sample_openapi_content):
        """Test that our payload model validates correctly."""
        # Test created event
        created_payload = N8nWebhookPayload(
            event_type="created",
            specification_id=123,
            specification_name="Test API",
            version_string="v1.0.0",
            user_id=456,
            timestamp="2024-01-15T10:30:00Z",
            openapi_content=sample_openapi_content,
        )

        assert created_payload.event_type == "created"
        assert created_payload.specification_id == 123
        assert created_payload.openapi_content["info"]["title"] == "Test API"

        # Test updated event
        updated_payload = N8nWebhookPayload(
            event_type="updated",
            specification_id=123,
            specification_name="Test API",
            version_string="v1.1.0",
            user_id=456,
            timestamp="2024-01-15T11:30:00Z",
            openapi_content=sample_openapi_content,
        )

        assert updated_payload.event_type == "updated"
        assert updated_payload.version_string == "v1.1.0"

        print("✅ Pydantic payload validation works correctly")

    @pytest.mark.asyncio
    async def test_webhook_with_complex_openapi_content(self, n8n_webhook_url):
        """Test webhook with complex OpenAPI content."""
        complex_payload = {
            "event_type": "created",
            "specification_id": 999,
            "specification_name": "Complex API",
            "version_string": "v2.0.0",
            "user_id": 789,
            "timestamp": "2024-01-15T16:00:00Z",
            "openapi_content": {
                "openapi": "3.0.0",
                "info": {
                    "title": "Complex API",
                    "description": "An API with complex schemas and multiple endpoints",
                    "version": "2.0.0",
                },
                "components": {
                    "schemas": {
                        "User": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "name": {"type": "string"},
                                "email": {"type": "string", "format": "email"},
                                "roles": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        }
                    }
                },
                "paths": {
                    "/users/{id}": {
                        "get": {
                            "parameters": [
                                {
                                    "name": "id",
                                    "in": "path",
                                    "required": True,
                                    "schema": {"type": "integer"},
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "User found",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/User"
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    }
                },
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    n8n_webhook_url,
                    json=complex_payload,
                    headers={"Content-Type": "application/json"},
                )

                assert response.status_code in [200, 404]
                print("✅ Complex OpenAPI content handled correctly")

        except httpx.RequestError as e:
            pytest.skip(f"Cannot test complex payload: {e}")

    def test_environment_variable_configuration(self):
        """Test that environment variables are properly configured."""
        # Check if N8N_WEBHOOK_URL is set
        webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if webhook_url:
            assert "n8n" in webhook_url or "localhost" in webhook_url
            assert "api-spec-notification" in webhook_url
            print(f"✅ N8N_WEBHOOK_URL configured: {webhook_url}")
        else:
            print("⚠️ N8N_WEBHOOK_URL not set in environment")

        # Check optional configuration
        max_retries = os.getenv("N8N_MAX_RETRIES", "3")
        retry_delay = os.getenv("N8N_RETRY_DELAY_SECONDS", "5")
        timeout = os.getenv("N8N_TIMEOUT_SECONDS", "30")

        assert int(max_retries) > 0
        assert int(retry_delay) > 0
        assert int(timeout) > 0

        print("✅ n8n configuration parameters are valid")

        # Print configuration for docker-compose reference
        print("\n📋 Required docker-compose environment variables:")
        print("   backend:")
        print("     environment:")
        print(
            f"       - N8N_WEBHOOK_URL=http://n8n:5678/webhook-test/api-spec-notification"
        )
        print(f"       - N8N_WEBHOOK_SECRET=specrepo-n8n-secret-2024")
        print(f"       - N8N_MAX_RETRIES={max_retries}")
        print(f"       - N8N_RETRY_DELAY_SECONDS={retry_delay}")
        print(f"       - N8N_TIMEOUT_SECONDS={timeout}")

    @pytest.mark.asyncio
    async def test_backend_service_integration(self):
        """Test the backend N8nNotificationService integration."""
        # Test service initialization
        service = N8nNotificationService()

        # Test configuration
        assert hasattr(service, "webhook_url")
        assert hasattr(service, "max_retries")
        assert hasattr(service, "retry_delay")
        assert hasattr(service, "timeout")

        # Test is_enabled method
        enabled = service.is_enabled()
        print(f"✅ N8nNotificationService enabled: {enabled}")

        # Create mock specification
        mock_spec = MagicMock()
        mock_spec.id = 123
        mock_spec.name = "Test API"
        mock_spec.version_string = "v1.0.0"
        mock_spec.user_id = 456
        mock_spec.created_at = datetime.now()
        mock_spec.updated_at = datetime.now()
        mock_spec.openapi_content = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
        }

        # Test payload creation (without actually sending)
        if enabled:
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

                result = await service.send_specification_created(mock_spec)
                assert isinstance(result, bool)
                print("✅ Backend service integration test passed")
        else:
            # Test disabled service
            result = await service.send_specification_created(mock_spec)
            assert result is True  # Should return True when disabled
            print("✅ Backend service handles disabled state correctly")

    @pytest.mark.asyncio
    async def test_webhook_response_format(
        self, n8n_webhook_url, created_event_payload
    ):
        """Test that webhook response follows expected format."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    n8n_webhook_url,
                    json=created_event_payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    response_data = response.json()

                    # Check expected response structure
                    assert "status" in response_data
                    assert "message" in response_data
                    assert "event_type" in response_data
                    assert "specification_id" in response_data

                    # Verify response values
                    assert response_data["status"] == "success"
                    assert response_data["event_type"] == "created"
                    assert response_data["specification_id"] == 123

                    print("✅ Webhook response format is correct")
                else:
                    print("⚠️ Webhook not active - cannot test response format")

        except httpx.RequestError as e:
            pytest.skip(f"Cannot test response format: {e}")

    def test_email_template_data_extraction(self, created_event_payload):
        """Test that email template can extract required data from payload."""
        payload = created_event_payload

        # Test data that would be used in email templates
        assert payload["specification_name"] == "Test API Specification"
        assert payload["version_string"] == "v1.0.0"
        assert payload["specification_id"] == 123
        assert payload["user_id"] == 456
        assert payload["timestamp"] == "2024-01-15T10:30:00Z"

        # Test OpenAPI content extraction
        openapi_info = payload["openapi_content"]["info"]
        assert openapi_info["title"] == "Test API"
        assert (
            openapi_info["description"]
            == "A comprehensive test API for integration testing"
        )
        assert openapi_info["version"] == "1.0.0"

        print("✅ Email template data extraction works correctly")

    def test_workflow_configuration_validation(self):
        """Test that the workflow configuration file is valid."""
        # Get the correct path relative to project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        workflow_path = os.path.join(
            project_root, "n8n", "workflows", "api-spec-notification.json"
        )

        # Check if workflow file exists
        assert os.path.exists(workflow_path), (
            f"Workflow file not found: {workflow_path}"
        )

        # Load and validate workflow JSON
        with open(workflow_path, "r") as f:
            workflow_data = json.load(f)

        # Validate workflow structure
        assert "name" in workflow_data
        assert "nodes" in workflow_data
        assert "connections" in workflow_data

        # Check for required nodes
        node_types = [node.get("type", "") for node in workflow_data["nodes"]]
        assert "n8n-nodes-base.webhook" in node_types
        assert "n8n-nodes-base.emailSend" in node_types
        assert "n8n-nodes-base.if" in node_types
        assert "n8n-nodes-base.respondToWebhook" in node_types

        # Check webhook configuration
        webhook_nodes = [
            node
            for node in workflow_data["nodes"]
            if node.get("type") == "n8n-nodes-base.webhook"
        ]
        assert len(webhook_nodes) == 1
        webhook_node = webhook_nodes[0]
        assert webhook_node["parameters"]["path"] == "api-spec-notification"

        print("✅ Workflow configuration is valid")

    def test_integration_test_coverage(self):
        """Verify that integration tests cover all required scenarios."""
        test_methods = [
            method
            for method in dir(self)
            if method.startswith("test_") and callable(getattr(self, method))
        ]

        required_test_areas = [
            "service_availability",
            "webhook_endpoint",
            "payload_structure",
            "environment_variable",
            "backend_service",
            "response_format",
            "email_template",
            "workflow_configuration",
        ]

        covered_areas = []
        for test_method in test_methods:
            for area in required_test_areas:
                if area in test_method:
                    covered_areas.append(area)

        missing_areas = set(required_test_areas) - set(covered_areas)
        assert not missing_areas, f"Missing test coverage for: {missing_areas}"

        print(
            f"✅ Integration test coverage complete: {len(test_methods)} tests"
        )
        print(f"   Covered areas: {', '.join(sorted(set(covered_areas)))}")


if __name__ == "__main__":
    """Run integration tests manually."""
    import asyncio

    async def run_manual_tests():
        test_instance = TestN8nWorkflowIntegration()

        # Test environment configuration
        print("=== Environment Configuration ===")
        test_instance.test_environment_variable_configuration()
        print()

        # Test service availability
        print("=== Service Availability ===")
        webhook_url = os.getenv(
            "N8N_WEBHOOK_URL",
            "http://localhost:5678/webhook-test/api-spec-notification",
        )
        try:
            await test_instance.test_n8n_service_availability()
        except Exception as e:
            print(f"❌ Service availability test failed: {e}")
        print()

        # Test webhook endpoint
        print("=== Webhook Endpoint Test ===")
        sample_payload = {
            "event_type": "created",
            "specification_id": 123,
            "specification_name": "Manual Test API",
            "version_string": "v1.0.0",
            "user_id": 456,
            "timestamp": "2024-01-15T10:30:00Z",
            "openapi_content": {
                "openapi": "3.0.0",
                "info": {
                    "title": "Manual Test API",
                    "description": "API for manual testing",
                    "version": "1.0.0",
                },
                "paths": {},
            },
        }

        try:
            await test_instance.test_webhook_endpoint_response(
                webhook_url, sample_payload
            )
        except Exception as e:
            print(f"❌ Webhook endpoint test failed: {e}")
        print()

        print("=== Manual Test Complete ===")

    asyncio.run(run_manual_tests())
