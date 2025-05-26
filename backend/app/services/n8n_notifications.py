import logging
import os
import time
from typing import Dict

import httpx
from pydantic import BaseModel

from app.models import APISpecification

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

    async def send_specification_created(
        self, specification: APISpecification
    ) -> bool:
        """
        Send notification when an API specification is created.

        Args:
            specification: The created API specification

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug(
                "n8n notifications disabled - no webhook URL configured"
            )
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

    async def send_specification_updated(
        self, specification: APISpecification
    ) -> bool:
        """
        Send notification when an API specification is updated.

        Args:
            specification: The updated API specification

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug(
                "n8n notifications disabled - no webhook URL configured"
            )
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

    async def _send_webhook(
        self, payload: N8nWebhookPayload, event_name: str
    ) -> bool:
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
