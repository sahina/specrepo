import logging
import os
import time
from typing import Dict, Optional

import httpx
from pydantic import BaseModel

from app.models import APISpecification, ValidationRun

logger = logging.getLogger(__name__)


class N8nWebhookPayload(BaseModel):
    """Pydantic model for n8n webhook payload."""

    event_type: str  # "created" or "updated"
    specification_id: int
    specification_name: str
    version_string: str
    user_id: int
    timestamp: str
    openapi_content: Dict


class N8nValidationWebhookPayload(BaseModel):
    """Pydantic model for n8n validation webhook payload."""

    event_type: str  # "validation_completed" or "validation_failed"
    validation_run_id: int
    specification_id: int
    specification_name: str
    provider_url: str
    user_id: int
    status: str  # "completed", "failed", "cancelled"
    timestamp: str
    validation_results: Optional[Dict]
    validation_statistics: Dict


class N8nNotificationService:
    """Service for sending notifications to n8n webhooks."""

    def __init__(self):
        self.webhook_url = os.getenv("N8N_WEBHOOK_URL")
        self.webhook_secret = os.getenv("N8N_WEBHOOK_SECRET")
        self.max_retries = int(os.getenv("N8N_MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("N8N_RETRY_DELAY_SECONDS", "5"))
        self.timeout = int(os.getenv("N8N_TIMEOUT_SECONDS", "30"))

    def is_enabled(self) -> bool:
        """Check if n8n notifications are enabled."""
        return bool(self.webhook_url)

    async def send_specification_created(self, specification: APISpecification) -> bool:
        """
        Send notification when an API specification is created.

        Args:
            specification: The created API specification

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        payload = N8nWebhookPayload(
            event_type="created",
            specification_id=specification.id,
            specification_name=specification.name,
            version_string=specification.version_string,
            user_id=specification.user_id,
            timestamp=specification.created_at.isoformat(),
            openapi_content=specification.openapi_content,
        )

        return await self._send_webhook(payload, "specification_created")

    async def send_specification_updated(self, specification: APISpecification) -> bool:
        """
        Send notification when an API specification is updated.

        Args:
            specification: The updated API specification

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        payload = N8nWebhookPayload(
            event_type="updated",
            specification_id=specification.id,
            specification_name=specification.name,
            version_string=specification.version_string,
            user_id=specification.user_id,
            timestamp=specification.updated_at.isoformat(),
            openapi_content=specification.openapi_content,
        )

        return await self._send_webhook(payload, "specification_updated")

    async def send_validation_completed(
        self, validation_run: ValidationRun, api_specification: APISpecification
    ) -> bool:
        """
        Send notification when a validation run completes successfully.

        Args:
            validation_run: The completed validation run
            api_specification: The API specification that was validated

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        # Extract validation statistics from results
        validation_statistics = self._extract_validation_statistics(
            validation_run.schemathesis_results
        )

        payload = N8nValidationWebhookPayload(
            event_type="validation_completed",
            validation_run_id=validation_run.id,
            specification_id=api_specification.id,
            specification_name=api_specification.name,
            provider_url=validation_run.provider_url,
            user_id=validation_run.user_id,
            status=validation_run.status,
            timestamp=validation_run.triggered_at.isoformat(),
            validation_results=validation_run.schemathesis_results,
            validation_statistics=validation_statistics,
        )

        return await self._send_validation_webhook(payload, "validation_completed")

    async def send_validation_failed(
        self, validation_run: ValidationRun, api_specification: APISpecification
    ) -> bool:
        """
        Send notification when a validation run fails.

        Args:
            validation_run: The failed validation run
            api_specification: The API specification that was validated

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        # Extract validation statistics from results (may be limited for failed runs)
        validation_statistics = self._extract_validation_statistics(
            validation_run.schemathesis_results
        )

        payload = N8nValidationWebhookPayload(
            event_type="validation_failed",
            validation_run_id=validation_run.id,
            specification_id=api_specification.id,
            specification_name=api_specification.name,
            provider_url=validation_run.provider_url,
            user_id=validation_run.user_id,
            status=validation_run.status,
            timestamp=validation_run.triggered_at.isoformat(),
            validation_results=validation_run.schemathesis_results,
            validation_statistics=validation_statistics,
        )

        return await self._send_validation_webhook(payload, "validation_failed")

    def _extract_validation_statistics(
        self, schemathesis_results: Optional[Dict]
    ) -> Dict:
        """
        Extract key validation statistics from Schemathesis results.

        Args:
            schemathesis_results: The raw Schemathesis results

        Returns:
            Dictionary containing key validation statistics
        """
        if not schemathesis_results:
            return {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0,
                "execution_time": 0.0,
                "error_count": 0,
            }

        # Handle error case
        if "error" in schemathesis_results:
            return {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0,
                "execution_time": 0.0,
                "error_count": 1,
                "error_message": schemathesis_results.get("error", "Unknown error"),
            }

        # Extract statistics from summary if available
        summary = schemathesis_results.get("summary", {})

        return {
            "total_tests": schemathesis_results.get("total_tests", 0),
            "passed_tests": schemathesis_results.get("passed_tests", 0),
            "failed_tests": schemathesis_results.get("failed_tests", 0),
            "success_rate": summary.get("success_rate", 0.0),
            "execution_time": schemathesis_results.get("execution_time", 0.0),
            "error_count": len(schemathesis_results.get("errors", [])),
            "test_results_count": len(schemathesis_results.get("test_results", [])),
        }

    async def _send_validation_webhook(
        self, payload: N8nValidationWebhookPayload, event_name: str
    ) -> bool:
        """
        Send validation webhook to n8n with retry logic.

        Args:
            payload: The validation webhook payload
            event_name: Name of the event for logging

        Returns:
            True if webhook was sent successfully, False otherwise
        """
        headers = {"Content-Type": "application/json"}
        if self.webhook_secret:
            headers["X-N8N-Webhook-Secret"] = self.webhook_secret

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,
                        json=payload.model_dump(),
                        headers=headers,
                    )

                    if response.status_code in [200, 201, 202, 204]:
                        logger.info(
                            f"Successfully sent n8n validation webhook for {event_name} "
                            f"(validation_run_id: {payload.validation_run_id}, "
                            f"spec_id: {payload.specification_id}, "
                            f"attempt: {attempt})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"n8n validation webhook failed for {event_name} "
                            f"(validation_run_id: {payload.validation_run_id}, "
                            f"spec_id: {payload.specification_id}, "
                            f"attempt: {attempt}, "
                            f"status: {response.status_code}, "
                            f"response: {response.text})"
                        )

            except httpx.TimeoutException:
                logger.warning(
                    f"n8n validation webhook timeout for {event_name} "
                    f"(validation_run_id: {payload.validation_run_id}, "
                    f"spec_id: {payload.specification_id}, "
                    f"attempt: {attempt})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"n8n validation webhook request error for {event_name} "
                    f"(validation_run_id: {payload.validation_run_id}, "
                    f"spec_id: {payload.specification_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error sending n8n validation webhook for {event_name} "
                    f"(validation_run_id: {payload.validation_run_id}, "
                    f"spec_id: {payload.specification_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )

            # Wait before retrying (except on last attempt)
            if attempt < self.max_retries:
                logger.info(
                    f"Retrying n8n validation webhook for {event_name} "
                    f"in {self.retry_delay} seconds "
                    f"(validation_run_id: {payload.validation_run_id}, "
                    f"spec_id: {payload.specification_id}, "
                    f"attempt: {attempt + 1}/{self.max_retries})"
                )
                time.sleep(self.retry_delay)

        logger.error(
            f"Failed to send n8n validation webhook for {event_name} "
            f"after {self.max_retries} attempts "
            f"(validation_run_id: {payload.validation_run_id}, "
            f"spec_id: {payload.specification_id})"
        )
        return False

    async def _send_webhook(self, payload: N8nWebhookPayload, event_name: str) -> bool:
        """
        Send webhook to n8n with retry logic.

        Args:
            payload: The webhook payload
            event_name: Name of the event for logging

        Returns:
            True if webhook was sent successfully, False otherwise
        """
        headers = {"Content-Type": "application/json"}
        if self.webhook_secret:
            headers["X-N8N-Webhook-Secret"] = self.webhook_secret

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,
                        json=payload.model_dump(),
                        headers=headers,
                    )

                    if response.status_code in [200, 201, 202, 204]:
                        logger.info(
                            f"Successfully sent n8n webhook for {event_name} "
                            f"(spec_id: {payload.specification_id}, "
                            f"attempt: {attempt})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"n8n webhook failed for {event_name} "
                            f"(spec_id: {payload.specification_id}, "
                            f"attempt: {attempt}, "
                            f"status: {response.status_code}, "
                            f"response: {response.text})"
                        )

            except httpx.TimeoutException:
                logger.warning(
                    f"n8n webhook timeout for {event_name} "
                    f"(spec_id: {payload.specification_id}, "
                    f"attempt: {attempt})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"n8n webhook request error for {event_name} "
                    f"(spec_id: {payload.specification_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error sending n8n webhook for {event_name} "
                    f"(spec_id: {payload.specification_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )

            # Wait before retrying (except on last attempt)
            if attempt < self.max_retries:
                logger.info(
                    f"Retrying n8n webhook for {event_name} "
                    f"in {self.retry_delay} seconds "
                    f"(spec_id: {payload.specification_id}, "
                    f"attempt: {attempt + 1}/{self.max_retries})"
                )
                time.sleep(self.retry_delay)

        logger.error(
            f"Failed to send n8n webhook for {event_name} "
            f"after {self.max_retries} attempts "
            f"(spec_id: {payload.specification_id})"
        )
        return False


# Global instance
n8n_service = N8nNotificationService()
