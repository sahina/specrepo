import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.n8n_notifications import (
    N8nHARProcessingWebhookPayload,
    N8nHARReviewWebhookPayload,
    N8nNotificationService,
)


class TestN8nHARProcessingWebhookPayload:
    """Test the N8nHARProcessingWebhookPayload Pydantic model."""

    def test_har_processing_payload_creation_completed(self):
        """Test creating a HAR processing completed payload with valid data."""
        payload = N8nHARProcessingWebhookPayload(
            event_type="har_processing_completed",
            upload_id=123,
            file_name="test.har",
            user_id=456,
            timestamp="2023-01-01T00:00:00",
            processing_status="completed",
            processing_statistics={
                "interactions_count": 10,
                "processed_interactions_count": 8,
                "openapi_paths_count": 5,
                "wiremock_stubs_count": 8,
            },
            artifacts_summary={
                "openapi_available": True,
                "wiremock_available": True,
                "openapi_title": "Test API",
            },
        )

        assert payload.event_type == "har_processing_completed"
        assert payload.upload_id == 123
        assert payload.file_name == "test.har"
        assert payload.user_id == 456
        assert payload.timestamp == "2023-01-01T00:00:00"
        assert payload.processing_status == "completed"
        assert payload.processing_statistics["interactions_count"] == 10
        assert payload.artifacts_summary["openapi_available"] is True
        assert payload.error_message is None

    def test_har_processing_payload_creation_failed(self):
        """Test creating a HAR processing failed payload with valid data."""
        payload = N8nHARProcessingWebhookPayload(
            event_type="har_processing_failed",
            upload_id=123,
            file_name="test.har",
            user_id=456,
            timestamp="2023-01-01T00:00:00",
            processing_status="failed",
            processing_statistics={
                "interactions_count": 0,
                "processing_progress": 25,
            },
            artifacts_summary=None,
            error_message="Invalid HAR format",
        )

        assert payload.event_type == "har_processing_failed"
        assert payload.upload_id == 123
        assert payload.file_name == "test.har"
        assert payload.user_id == 456
        assert payload.processing_status == "failed"
        assert payload.artifacts_summary is None
        assert payload.error_message == "Invalid HAR format"


class TestN8nHARReviewWebhookPayload:
    """Test the N8nHARReviewWebhookPayload Pydantic model."""

    def test_har_review_payload_creation(self):
        """Test creating a HAR review request payload with valid data."""
        payload = N8nHARReviewWebhookPayload(
            event_type="har_review_requested",
            upload_id=123,
            file_name="test.har",
            user_id=456,
            timestamp="2023-01-01T00:00:00",
            artifacts_summary={
                "openapi_available": True,
                "wiremock_available": True,
                "openapi_title": "Test API",
                "openapi_paths_count": 5,
                "wiremock_stubs_count": 8,
            },
            review_url="http://localhost:5173/har-uploads/123/review",
            processing_statistics={
                "interactions_count": 10,
                "processed_interactions_count": 8,
            },
        )

        assert payload.event_type == "har_review_requested"
        assert payload.upload_id == 123
        assert payload.file_name == "test.har"
        assert payload.user_id == 456
        assert payload.timestamp == "2023-01-01T00:00:00"
        assert payload.review_url == "http://localhost:5173/har-uploads/123/review"
        assert payload.artifacts_summary["openapi_available"] is True
        assert payload.processing_statistics["interactions_count"] == 10


class TestN8nNotificationServiceHARMethods:
    """Test the HAR processing methods in N8nNotificationService."""

    def setup_method(self):
        """Set up test environment variables."""
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """Restore original environment variables."""
        os.environ.clear()
        os.environ.update(self.original_env)

    def create_mock_processing_result_success(self):
        """Helper to create a mock successful processing result."""
        return {
            "success": True,
            "upload_id": 123,
            "processing_status": {
                "status": "completed",
                "progress": 100,
                "completed_at": "2023-01-01T00:00:00",
                "steps": {
                    "parsing": {"status": "completed"},
                    "ai_processing": {"status": "completed"},
                    "openapi_generation": {"status": "completed"},
                    "wiremock_generation": {"status": "completed"},
                    "storing_artifacts": {"status": "completed"},
                },
            },
            "artifacts": {
                "openapi_specification": {
                    "openapi": "3.0.0",
                    "info": {"title": "Test API", "version": "1.0.0"},
                    "paths": {"/users": {}, "/posts": {}},
                },
                "wiremock_mappings": [
                    {"request": {}, "response": {}},
                    {"request": {}, "response": {}},
                ],
                "processing_metadata": {
                    "interactions_count": 10,
                    "processed_interactions_count": 8,
                    "openapi_paths_count": 2,
                    "wiremock_stubs_count": 2,
                    "processed_at": "2023-01-01T00:00:00",
                    "processing_options": {
                        "enable_ai_processing": True,
                        "enable_data_generalization": True,
                    },
                },
            },
        }

    def create_mock_processing_result_failure(self):
        """Helper to create a mock failed processing result."""
        return {
            "success": False,
            "upload_id": 123,
            "processing_status": {
                "status": "failed",
                "progress": 25,
                "failed_at": "2023-01-01T00:00:00",
                "error": "Invalid HAR format",
                "steps": {
                    "parsing": {"status": "completed"},
                    "ai_processing": {"status": "failed"},
                },
            },
            "error": "Invalid HAR format",
        }

    @pytest.mark.asyncio
    async def test_send_har_processing_completed_disabled(self):
        """Test send_har_processing_completed when notifications are disabled."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_success()

        result = await service.send_har_processing_completed(
            upload_id=123,
            file_name="test.har",
            user_id=456,
            processing_result=processing_result,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_har_processing_failed_disabled(self):
        """Test send_har_processing_failed when notifications are disabled."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_failure()

        result = await service.send_har_processing_failed(
            upload_id=123,
            file_name="test.har",
            user_id=456,
            processing_result=processing_result,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_har_review_requested_disabled(self):
        """Test send_har_review_requested when notifications are disabled."""
        os.environ.pop("N8N_WEBHOOK_URL", None)
        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_success()

        result = await service.send_har_review_requested(
            upload_id=123,
            file_name="test.har",
            user_id=456,
            processing_result=processing_result,
            review_url="http://localhost:5173/har-uploads/123/review",
        )

        assert result is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_har_processing_completed_success(self, mock_client_class):
        """Test successful send_har_processing_completed."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_WEBHOOK_SECRET"] = "test-secret"

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_success()

        result = await service.send_har_processing_completed(
            upload_id=123,
            file_name="test.har",
            user_id=456,
            processing_result=processing_result,
        )

        assert result is True
        mock_client.post.assert_called_once()

        # Verify the call arguments
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://test.webhook.url"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        assert call_args[1]["headers"]["X-N8N-Webhook-Secret"] == "test-secret"

        # Verify payload structure
        payload_data = call_args[1]["json"]
        assert payload_data["event_type"] == "har_processing_completed"
        assert payload_data["upload_id"] == 123
        assert payload_data["file_name"] == "test.har"
        assert payload_data["user_id"] == 456
        assert payload_data["processing_status"] == "completed"
        assert payload_data["processing_statistics"]["interactions_count"] == 10
        assert payload_data["artifacts_summary"]["openapi_available"] is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_har_processing_failed_success(self, mock_client_class):
        """Test successful send_har_processing_failed."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_failure()

        result = await service.send_har_processing_failed(
            upload_id=123,
            file_name="test.har",
            user_id=456,
            processing_result=processing_result,
        )

        assert result is True
        mock_client.post.assert_called_once()

        # Verify payload structure
        call_args = mock_client.post.call_args
        payload_data = call_args[1]["json"]
        assert payload_data["event_type"] == "har_processing_failed"
        assert payload_data["upload_id"] == 123
        assert payload_data["processing_status"] == "failed"
        assert payload_data["error_message"] == "Invalid HAR format"
        assert payload_data["artifacts_summary"] is None

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_har_review_requested_success(self, mock_client_class):
        """Test successful send_har_review_requested."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"

        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_success()

        result = await service.send_har_review_requested(
            upload_id=123,
            file_name="test.har",
            user_id=456,
            processing_result=processing_result,
            review_url="http://localhost:5173/har-uploads/123/review",
        )

        assert result is True
        mock_client.post.assert_called_once()

        # Verify payload structure
        call_args = mock_client.post.call_args
        payload_data = call_args[1]["json"]
        assert payload_data["event_type"] == "har_review_requested"
        assert payload_data["upload_id"] == 123
        assert payload_data["review_url"] == "http://localhost:5173/har-uploads/123/review"
        assert payload_data["artifacts_summary"]["openapi_available"] is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_har_webhook_failure_with_retry(self, mock_client_class):
        """Test HAR webhook sending with failure and retry."""
        os.environ["N8N_WEBHOOK_URL"] = "https://test.webhook.url"
        os.environ["N8N_MAX_RETRIES"] = "2"

        # Mock responses: first call fails, second succeeds
        mock_client = AsyncMock()
        mock_responses = [
            MagicMock(status_code=500, text="Server Error"),
            MagicMock(status_code=200),
        ]
        mock_client.post.side_effect = mock_responses
        mock_client_class.return_value.__aenter__.return_value = mock_client

        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_success()

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = await service.send_har_processing_completed(
                upload_id=123,
                file_name="test.har",
                user_id=456,
                processing_result=processing_result,
            )

        assert result is True
        assert mock_client.post.call_count == 2  # First failure, then success

    def test_extract_har_processing_statistics(self):
        """Test extracting processing statistics from HAR processing result."""
        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_success()

        stats = service._extract_har_processing_statistics(processing_result)

        assert stats["interactions_count"] == 10
        assert stats["processed_interactions_count"] == 8
        assert stats["openapi_paths_count"] == 2
        assert stats["wiremock_stubs_count"] == 2
        assert stats["processing_steps_completed"] == 5
        assert stats["total_processing_steps"] == 5
        assert stats["processing_progress"] == 100
        assert stats["processing_options"]["enable_ai_processing"] is True

    def test_extract_har_processing_statistics_failure(self):
        """Test extracting processing statistics from failed HAR processing result."""
        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_failure()

        stats = service._extract_har_processing_statistics(processing_result)

        assert stats["interactions_count"] == 0
        assert stats["processed_interactions_count"] == 0
        assert stats["openapi_paths_count"] == 0
        assert stats["wiremock_stubs_count"] == 0
        assert stats["processing_steps_completed"] == 1  # Only parsing completed
        assert stats["total_processing_steps"] == 2
        assert stats["processing_progress"] == 25

    def test_extract_har_artifacts_summary(self):
        """Test extracting artifacts summary from HAR processing result."""
        service = N8nNotificationService()
        processing_result = self.create_mock_processing_result_success()

        summary = service._extract_har_artifacts_summary(processing_result)

        assert summary["openapi_available"] is True
        assert summary["openapi_title"] == "Test API"
        assert summary["openapi_version"] == "1.0.0"
        assert summary["openapi_paths_count"] == 2
        assert summary["wiremock_available"] is True
        assert summary["wiremock_stubs_count"] == 2
        assert summary["artifacts_generated_at"] == "2023-01-01T00:00:00"

    def test_extract_har_artifacts_summary_no_artifacts(self):
        """Test extracting artifacts summary when no artifacts are available."""
        service = N8nNotificationService()
        processing_result = {"artifacts": {}}

        summary = service._extract_har_artifacts_summary(processing_result)

        assert summary["openapi_available"] is False
        assert summary["openapi_title"] == ""
        assert summary["openapi_version"] == ""
        assert summary["openapi_paths_count"] == 0
        assert summary["wiremock_available"] is False
        assert summary["wiremock_stubs_count"] == 0
        assert summary["artifacts_generated_at"] == ""
