import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.models import APISpecification, User, ValidationRun
from app.services.n8n_notifications import (
    N8nNotificationService,
    N8nValidationWebhookPayload,
    N8nWebhookPayload,
)
from main import app


class TestN8nWebhookPayload:
    """Test the N8nWebhookPayload Pydantic model."""

    def test_webhook_payload_creation(self):
        """Test creating a webhook payload with valid data."""
        payload = N8nWebhookPayload(
            event_type="created",
            specification_id=1,
            specification_name="Test API",
            version_string="v1.0",
            user_id=123,
            timestamp="2023-01-01T00:00:00",
            openapi_content={
                "openapi": "3.0.0",
                "info": {"title": "Test API"},
            },
        )

        assert payload.event_type == "created"
        assert payload.specification_id == 1
        assert payload.specification_name == "Test API"
        assert payload.version_string == "v1.0"
        assert payload.user_id == 123
        assert payload.timestamp == "2023-01-01T00:00:00"
        assert payload.openapi_content == {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
        }

    def test_webhook_payload_model_dump(self):
        """Test that the payload can be serialized to dict."""
        payload = N8nWebhookPayload(
            event_type="updated",
            specification_id=2,
            specification_name="Updated API",
            version_string="v2.0",
            user_id=456,
            timestamp="2023-01-02T00:00:00",
            openapi_content={"openapi": "3.0.0"},
        )

        data = payload.model_dump()
        expected = {
            "event_type": "updated",
            "specification_id": 2,
            "specification_name": "Updated API",
            "version_string": "v2.0",
            "user_id": 456,
            "timestamp": "2023-01-02T00:00:00",
            "openapi_content": {"openapi": "3.0.0"},
        }

        assert data == expected


class TestN8nValidationWebhookPayload:
    """Test the N8nValidationWebhookPayload Pydantic model."""

    def test_validation_webhook_payload_creation(self):
        """Test creating a validation webhook payload with valid data."""
        payload = N8nValidationWebhookPayload(
            event_type="validation_completed",
            validation_run_id=1,
            specification_id=2,
            specification_name="Test API",
            provider_url="https://api.example.com",
            user_id=123,
            status="completed",
            timestamp="2023-01-01T00:00:00",
            validation_results={
                "total_tests": 10,
                "passed_tests": 8,
                "failed_tests": 2,
            },
            validation_statistics={
                "success_rate": 80.0,
                "execution_time": 30.5,
                "error_count": 0,
            },
        )

        assert payload.event_type == "validation_completed"
        assert payload.validation_run_id == 1
        assert payload.specification_id == 2
        assert payload.specification_name == "Test API"
        assert payload.provider_url == "https://api.example.com"
        assert payload.user_id == 123
        assert payload.status == "completed"
        assert payload.timestamp == "2023-01-01T00:00:00"
        assert payload.validation_results["total_tests"] == 10
        assert payload.validation_statistics["success_rate"] == 80.0

    def test_validation_webhook_payload_with_none_results(self):
        """Test creating a validation webhook payload with None results."""
        payload = N8nValidationWebhookPayload(
            event_type="validation_failed",
            validation_run_id=2,
            specification_id=3,
            specification_name="Failed API",
            provider_url="https://api.failed.com",
            user_id=456,
            status="failed",
            timestamp="2023-01-02T00:00:00",
            validation_results=None,
            validation_statistics={
                "error_count": 1,
                "error_message": "Connection failed",
            },
        )

        assert payload.event_type == "validation_failed"
        assert payload.validation_run_id == 2
        assert payload.validation_results is None
        assert payload.validation_statistics["error_count"] == 1

    def test_validation_webhook_payload_model_dump(self):
        """Test that the validation payload can be serialized to dict."""
        payload = N8nValidationWebhookPayload(
            event_type="validation_completed",
            validation_run_id=1,
            specification_id=2,
            specification_name="Test API",
            provider_url="https://api.example.com",
            user_id=123,
            status="completed",
            timestamp="2023-01-01T00:00:00",
            validation_results={"total_tests": 5},
            validation_statistics={"success_rate": 100.0},
        )

        data = payload.model_dump()
        expected = {
            "event_type": "validation_completed",
            "validation_run_id": 1,
            "specification_id": 2,
            "specification_name": "Test API",
            "provider_url": "https://api.example.com",
            "user_id": 123,
            "status": "completed",
            "timestamp": "2023-01-01T00:00:00",
            "validation_results": {"total_tests": 5},
            "validation_statistics": {"success_rate": 100.0},
        }

        assert data == expected


class TestN8nNotificationService:
    """Test the N8nNotificationService class."""

    def setup_method(self):
        """Set up test environment variables."""
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """Restore original environment variables."""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_service_initialization_with_defaults(self):
        """Test service initialization with default values."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        os.environ.pop("N8N_WEBHOOK_SECRET", None)
        os.environ.pop("N8N_MAX_RETRIES", None)
        os.environ.pop("N8N_RETRY_DELAY_SECONDS", None)
        os.environ.pop("N8N_TIMEOUT_SECONDS", None)

        service = N8nNotificationService()

        assert service.webhook_url is None
        assert service.webhook_secret is None
        assert service.max_retries == 3
        assert service.retry_delay == 5
        assert service.timeout == 30

    def test_service_initialization_with_env_vars(self):
        """Test service initialization with environment variables."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_WEBHOOK_SECRET"] = "test-secret"
        os.environ["N8N_MAX_RETRIES"] = "5"
        os.environ["N8N_RETRY_DELAY_SECONDS"] = "10"
        os.environ["N8N_TIMEOUT_SECONDS"] = "60"

        service = N8nNotificationService()

        assert service.webhook_url == "https://test.webhook.url"
        assert service.webhook_secret == "test-secret"
        assert service.max_retries == 5
        assert service.retry_delay == 10
        assert service.timeout == 60

    def test_is_enabled_with_webhook_url(self):
        """Test is_enabled returns True when webhook URL is set."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        service = N8nNotificationService()
        assert service.is_enabled() is True

    def test_is_enabled_without_webhook_url(self):
        """Test is_enabled returns False when webhook URL is not set."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        service = N8nNotificationService()
        assert service.is_enabled() is False

    def test_is_enabled_with_empty_webhook_url(self):
        """Test is_enabled returns False when webhook URL is empty."""
        os.environ["N8N_WEBHOOK_URL"] = ""
        service = N8nNotificationService()
        assert service.is_enabled() is False

    def create_mock_specification(self, spec_id=1, event_type="created"):
        """Helper to create a mock API specification."""
        spec = MagicMock(spec=APISpecification)
        spec.id = spec_id
        spec.name = "Test API"
        spec.version_string = "v1.0"
        spec.user_id = 123
        spec.openapi_content = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
        }

        if event_type == "created":
            spec.created_at = datetime(2023, 1, 1, 0, 0, 0)
            spec.updated_at = datetime(2023, 1, 1, 0, 0, 0)
        else:
            spec.created_at = datetime(2023, 1, 1, 0, 0, 0)
            spec.updated_at = datetime(2023, 1, 2, 0, 0, 0)

        return spec

    def create_mock_validation_run(self, run_id=1, status="completed"):
        """Helper to create a mock validation run."""
        validation_run = MagicMock(spec=ValidationRun)
        validation_run.id = run_id
        validation_run.api_specification_id = 1
        validation_run.provider_url = "https://api.example.com"
        validation_run.user_id = 123
        validation_run.status = status
        validation_run.triggered_at = datetime(2023, 1, 1, 0, 0, 0)

        if status == "completed":
            validation_run.schemathesis_results = {
                "total_tests": 10,
                "passed_tests": 8,
                "failed_tests": 2,
                "execution_time": 30.5,
                "errors": [],
                "test_results": [{"test": "result1"}, {"test": "result2"}],
                "summary": {
                    "success_rate": 80.0,
                    "total_tests": 10,
                    "passed_tests": 8,
                    "failed_tests": 2,
                    "error_count": 0,
                    "execution_time": 30.5,
                },
            }
        elif status == "failed":
            validation_run.schemathesis_results = {
                "error": "Connection failed",
                "timestamp": "2023-01-01T00:00:00",
            }
        else:
            validation_run.schemathesis_results = None

        return validation_run

    @pytest.mark.asyncio
    async def test_send_specification_created_disabled(self):
        """Test send_specification_created when notifications are disabled."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        service = N8nNotificationService()
        spec = self.create_mock_specification()

        result = await service.send_specification_created(spec)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_specification_updated_disabled(self):
        """Test send_specification_updated when notifications are disabled."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        service = N8nNotificationService()
        spec = self.create_mock_specification(event_type="updated")

        result = await service.send_specification_updated(spec)

        assert result is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_specification_created_success(self, mock_client_class):
        """Test successful send_specification_created."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_WEBHOOK_SECRET"] = "test-secret"

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        spec = self.create_mock_specification()

        result = await service.send_specification_created(spec)

        assert result is True
        mock_client.post.assert_called_once()

        # Verify the call arguments
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://test.webhook.url"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        assert call_args[1]["headers"]["X-N8N-Webhook-Secret"] == "test-secret"

        # Verify payload structure
        payload_data = call_args[1]["json"]
        assert payload_data["event_type"] == "created"
        assert payload_data["specification_id"] == 1
        assert payload_data["specification_name"] == "Test API"
        assert payload_data["version_string"] == "v1.0"
        assert payload_data["user_id"] == 123

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_specification_updated_success(self, mock_client_class):
        """Test successful send_specification_updated."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        spec = self.create_mock_specification(event_type="updated")

        result = await service.send_specification_updated(spec)

        assert result is True
        mock_client.post.assert_called_once()

        # Verify payload has updated event type and timestamp
        call_args = mock_client.post.call_args
        payload_data = call_args[1]["json"]
        assert payload_data["event_type"] == "updated"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_webhook_without_secret(self, mock_client_class):
        """Test sending webhook without secret header."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ.pop("N8N_WEBHOOK_SECRET", None)

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        spec = self.create_mock_specification()

        result = await service.send_specification_created(spec)

        assert result is True

        # Verify no secret header is sent
        call_args = mock_client.post.call_args
        headers = call_args[1]["headers"]
        assert "X-N8N-Webhook-Secret" not in headers
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_webhook_http_error(self, mock_client_class):
        """Test webhook sending with HTTP error response."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_MAX_RETRIES"] = "2"

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        spec = self.create_mock_specification()

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = await service.send_specification_created(spec)

        assert result is False
        assert mock_client.post.call_count == 2  # Should retry

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_webhook_timeout_error(self, mock_client_class):
        """Test webhook sending with timeout error."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_MAX_RETRIES"] = "2"

        # Mock timeout exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        spec = self.create_mock_specification()

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = await service.send_specification_created(spec)

        assert result is False
        assert mock_client.post.call_count == 2  # Should retry

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_webhook_request_error(self, mock_client_class):
        """Test webhook sending with request error."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_MAX_RETRIES"] = "1"

        # Mock request exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        spec = self.create_mock_specification()

        result = await service.send_specification_created(spec)

        assert result is False
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_webhook_unexpected_error(self, mock_client_class):
        """Test webhook sending with unexpected error."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_MAX_RETRIES"] = "1"

        # Mock unexpected exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Unexpected error")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        spec = self.create_mock_specification()

        result = await service.send_specification_created(spec)

        assert result is False
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_webhook_success_status_codes(self, mock_client_class):
        """Test webhook sending with various success status codes."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"

        success_codes = [200, 201, 202, 204]

        for status_code in success_codes:
            # Mock the response
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            service = N8nNotificationService()
            spec = self.create_mock_specification()

            result = await service.send_specification_created(spec)

            assert result is True, f"Status code {status_code} should be successful"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_webhook_retry_then_success(self, mock_client_class):
        """Test webhook sending that fails then succeeds on retry."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_MAX_RETRIES"] = "3"

        # Mock responses: first call fails, second succeeds
        mock_client = AsyncMock()
        mock_responses = [
            MagicMock(status_code=500, text="Error"),
            MagicMock(status_code=200),
        ]
        mock_client.post.side_effect = mock_responses
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        spec = self.create_mock_specification()

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = await service.send_specification_created(spec)

        assert result is True
        assert mock_client.post.call_count == 2  # First failure, then success

    @pytest.mark.asyncio
    async def test_send_validation_completed_disabled(self):
        """Test send_validation_completed when notifications are disabled."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        service = N8nNotificationService()
        validation_run = self.create_mock_validation_run()
        api_spec = self.create_mock_specification()

        result = await service.send_validation_completed(validation_run, api_spec)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_validation_failed_disabled(self):
        """Test send_validation_failed when notifications are disabled."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        service = N8nNotificationService()
        validation_run = self.create_mock_validation_run(status="failed")
        api_spec = self.create_mock_specification()

        result = await service.send_validation_failed(validation_run, api_spec)

        assert result is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_validation_completed_success(self, mock_client_class):
        """Test successful send_validation_completed."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_WEBHOOK_SECRET"] = "test-secret"

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        validation_run = self.create_mock_validation_run()
        api_spec = self.create_mock_specification()

        result = await service.send_validation_completed(validation_run, api_spec)

        assert result is True
        mock_client.post.assert_called_once()

        # Verify the call arguments
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["event_type"] == "validation_completed"
        assert call_args[1]["json"]["validation_run_id"] == 1
        assert call_args[1]["json"]["specification_id"] == 1
        assert call_args[1]["json"]["provider_url"] == "https://api.example.com"
        assert call_args[1]["headers"]["X-N8N-Webhook-Secret"] == "test-secret"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_validation_failed_success(self, mock_client_class):
        """Test successful send_validation_failed."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        validation_run = self.create_mock_validation_run(status="failed")
        api_spec = self.create_mock_specification()

        result = await service.send_validation_failed(validation_run, api_spec)

        assert result is True
        mock_client.post.assert_called_once()

        # Verify the call arguments
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["event_type"] == "validation_failed"
        assert call_args[1]["json"]["status"] == "failed"

    def test_extract_validation_statistics_with_complete_results(self):
        """Test extracting statistics from complete validation results."""
        service = N8nNotificationService()
        results = {
            "total_tests": 10,
            "passed_tests": 8,
            "failed_tests": 2,
            "execution_time": 30.5,
            "errors": ["error1"],
            "test_results": [{"test": "result1"}, {"test": "result2"}],
            "summary": {
                "success_rate": 80.0,
                "total_tests": 10,
                "passed_tests": 8,
                "failed_tests": 2,
                "error_count": 1,
                "execution_time": 30.5,
            },
        }

        stats = service._extract_validation_statistics(results)

        assert stats["total_tests"] == 10
        assert stats["passed_tests"] == 8
        assert stats["failed_tests"] == 2
        assert stats["success_rate"] == 80.0
        assert stats["execution_time"] == 30.5
        assert stats["error_count"] == 1
        assert stats["test_results_count"] == 2

    def test_extract_validation_statistics_with_error(self):
        """Test extracting statistics from error results."""
        service = N8nNotificationService()
        results = {
            "error": "Connection failed",
            "timestamp": "2023-01-01T00:00:00",
        }

        stats = service._extract_validation_statistics(results)

        assert stats["total_tests"] == 0
        assert stats["passed_tests"] == 0
        assert stats["failed_tests"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["execution_time"] == 0.0
        assert stats["error_count"] == 1
        assert stats["error_message"] == "Connection failed"

    def test_extract_validation_statistics_with_none(self):
        """Test extracting statistics from None results."""
        service = N8nNotificationService()

        stats = service._extract_validation_statistics(None)

        assert stats["total_tests"] == 0
        assert stats["passed_tests"] == 0
        assert stats["failed_tests"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["execution_time"] == 0.0
        assert stats["error_count"] == 0

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_validation_webhook_retry_logic(self, mock_client_class):
        """Test validation webhook retry logic on failure."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_MAX_RETRIES"] = "2"
        os.environ["N8N_RETRY_DELAY_SECONDS"] = "1"

        # Mock failed responses
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        validation_run = self.create_mock_validation_run()
        api_spec = self.create_mock_specification()

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = await service.send_validation_completed(validation_run, api_spec)

        assert result is False
        assert mock_client.post.call_count == 2  # Should retry once


class TestN8nIntegrationWithAPI:
    """Test n8n integration with API endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = 1
        user.api_key = "test-api-key"
        user.username = "testuser"
        return user

    @pytest.fixture
    def mock_specification(self):
        """Create a mock specification."""
        spec = MagicMock(spec=APISpecification)
        spec.id = 1
        spec.name = "Test API"
        spec.version_string = "v1.0"
        spec.user_id = 1
        spec.openapi_content = {
            "openapi": "3.0.0",
            "info": {"title": "Test API"},
        }
        spec.created_at = datetime(2023, 1, 1, 0, 0, 0)
        spec.updated_at = datetime(2023, 1, 1, 0, 0, 0)
        return spec

    @pytest.fixture
    def client(self, mock_user):
        """Create a test client with mocked dependencies."""
        from app.db.session import get_db
        from app.dependencies import get_current_user

        def override_get_current_user():
            return mock_user

        def override_get_db():
            return MagicMock()

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)
        yield client

        # Clean up overrides
        app.dependency_overrides.clear()

    def setup_method(self):
        """Set up test environment."""
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch("app.services.n8n_notifications.n8n_service.send_specification_created")
    @patch("app.services.api_specifications.APISpecificationService.create_specification")
    @patch(
        "app.services.api_specifications.APISpecificationService.check_name_version_exists"
    )
    def test_create_specification_triggers_n8n_notification(
        self,
        mock_check_exists,
        mock_create_spec,
        mock_n8n_send,
        client,
        mock_user,
        mock_specification,
    ):
        """Test that creating a specification triggers n8n notification."""
        # Setup mocks
        mock_check_exists.return_value = False
        mock_create_spec.return_value = mock_specification
        mock_n8n_send.return_value = True

        # Make request
        response = client.post(
            "/api/specifications",
            json={
                "name": "Test API",
                "version_string": "v1.0",
                "openapi_content": {
                    "openapi": "3.0.0",
                    "info": {"title": "Test API"},
                },
            },
        )

        # Verify response
        assert response.status_code == 201

        # Verify n8n notification was called
        # Note: BackgroundTasks runs the task immediately in tests
        mock_n8n_send.assert_called_once_with(mock_specification)

    @patch("app.services.n8n_notifications.n8n_service.send_specification_updated")
    @patch("app.services.api_specifications.APISpecificationService.update_specification")
    @patch("app.services.api_specifications.APISpecificationService.get_specification")
    @patch(
        "app.services.api_specifications.APISpecificationService.check_name_version_exists"
    )
    def test_update_specification_triggers_n8n_notification(
        self,
        mock_check_exists,
        mock_get_spec,
        mock_update_spec,
        mock_n8n_send,
        client,
        mock_user,
        mock_specification,
    ):
        """Test that updating a specification triggers n8n notification."""
        # Setup mocks
        mock_get_spec.return_value = mock_specification
        mock_check_exists.return_value = False
        mock_update_spec.return_value = mock_specification
        mock_n8n_send.return_value = True

        # Make request
        response = client.put(
            "/api/specifications/1",
            json={"name": "Updated API"},
        )

        # Verify response
        assert response.status_code == 200

        # Verify n8n notification was called
        mock_n8n_send.assert_called_once_with(mock_specification)

    @patch("app.services.n8n_notifications.n8n_service.send_specification_created")
    @patch("app.services.api_specifications.APISpecificationService.create_specification")
    @patch(
        "app.services.api_specifications.APISpecificationService.check_name_version_exists"
    )
    @patch("app.dependencies.get_current_user")
    @patch("app.db.session.get_db")
    def test_create_specification_continues_on_n8n_failure(
        self,
        mock_get_db,
        mock_get_user,
        mock_check_exists,
        mock_create_spec,
        mock_n8n_send,
        client,
        mock_user,
        mock_specification,
    ):
        """Test that API continues to work even if n8n notification fails."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_check_exists.return_value = False
        mock_create_spec.return_value = mock_specification
        mock_n8n_send.return_value = False  # Simulate n8n failure

        # Make request
        response = client.post(
            "/api/specifications",
            json={
                "name": "Test API",
                "version_string": "v1.0",
                "openapi_content": {
                    "openapi": "3.0.0",
                    "info": {"title": "Test API"},
                },
            },
            headers={"X-API-Key": "test-api-key"},
        )

        # Verify response is still successful
        assert response.status_code == 201

        # Verify n8n notification was attempted
        mock_n8n_send.assert_called_once_with(mock_specification)
