import logging
import os
import time
from typing import Dict, List, Optional

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


class N8nContractValidationWebhookPayload(BaseModel):
    """Pydantic model for n8n contract validation webhook payload."""

    event_type: str  # "contract_validation_completed" or "contract_validation_failed"
    contract_validation_id: int
    specification_id: int
    specification_name: str
    provider_url: str
    user_id: int
    status: str  # "completed", "failed", "cancelled"
    timestamp: str
    contract_health_status: str  # "HEALTHY", "DEGRADED", "BROKEN"
    health_score: float
    producer_validation_results: Optional[Dict]
    mock_alignment_results: Optional[Dict]
    validation_summary: Dict
    recommendations: List[str]


class N8nHARProcessingWebhookPayload(BaseModel):
    """Pydantic model for n8n HAR processing webhook payload."""

    event_type: str  # "har_processing_completed" or "har_processing_failed"
    upload_id: int
    file_name: str
    user_id: int
    timestamp: str
    processing_status: str  # "completed" or "failed"
    processing_statistics: Dict
    artifacts_summary: Optional[Dict]
    error_message: Optional[str] = None


class N8nHARReviewWebhookPayload(BaseModel):
    """Pydantic model for n8n HAR review request webhook payload."""

    event_type: str  # "har_review_requested"
    upload_id: int
    file_name: str
    user_id: int
    timestamp: str
    artifacts_summary: Dict
    review_url: str
    processing_statistics: Dict


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

    async def send_contract_validation_completed(
        self, contract_validation, api_specification: APISpecification
    ) -> bool:
        """
        Send notification when a contract validation completes successfully.

        Args:
            contract_validation: The completed contract validation
            api_specification: The API specification that was validated

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        # Extract recommendations from validation summary
        recommendations = contract_validation.validation_summary.get("recommendations", [])

        payload = N8nContractValidationWebhookPayload(
            event_type="contract_validation_completed",
            contract_validation_id=contract_validation.id,
            specification_id=api_specification.id,
            specification_name=api_specification.name,
            provider_url=contract_validation.provider_url,
            user_id=contract_validation.user_id,
            status=contract_validation.status,
            timestamp=contract_validation.triggered_at.isoformat(),
            contract_health_status=contract_validation.contract_health_status,
            health_score=contract_validation.health_score,
            producer_validation_results=contract_validation.producer_validation_results,
            mock_alignment_results=contract_validation.mock_alignment_results,
            validation_summary=contract_validation.validation_summary,
            recommendations=recommendations,
        )

        return await self._send_contract_validation_webhook(
            payload, "contract_validation_completed"
        )

    async def send_contract_validation_failed(
        self, contract_validation, api_specification: APISpecification
    ) -> bool:
        """
        Send notification when a contract validation fails.

        Args:
            contract_validation: The failed contract validation
            api_specification: The API specification that was validated

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        # Extract recommendations from validation summary (may be limited for failed runs)
        recommendations = contract_validation.validation_summary.get("recommendations", [])

        payload = N8nContractValidationWebhookPayload(
            event_type="contract_validation_failed",
            contract_validation_id=contract_validation.id,
            specification_id=api_specification.id,
            specification_name=api_specification.name,
            provider_url=contract_validation.provider_url,
            user_id=contract_validation.user_id,
            status=contract_validation.status,
            timestamp=contract_validation.triggered_at.isoformat(),
            contract_health_status=contract_validation.contract_health_status,
            health_score=contract_validation.health_score,
            producer_validation_results=contract_validation.producer_validation_results,
            mock_alignment_results=contract_validation.mock_alignment_results,
            validation_summary=contract_validation.validation_summary,
            recommendations=recommendations,
        )

        return await self._send_contract_validation_webhook(payload, "contract_validation_failed")

    async def send_har_processing_completed(
        self, upload_id: int, file_name: str, user_id: int, processing_result: Dict
    ) -> bool:
        """
        Send notification when HAR processing completes successfully.

        Args:
            upload_id: ID of the HAR upload
            file_name: Name of the processed HAR file
            user_id: ID of the user who owns the upload
            processing_result: Result dictionary from HAR processing

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        # Extract processing statistics and artifacts summary
        processing_statistics = self._extract_har_processing_statistics(processing_result)
        artifacts_summary = self._extract_har_artifacts_summary(processing_result)

        payload = N8nHARProcessingWebhookPayload(
            event_type="har_processing_completed",
            upload_id=upload_id,
            file_name=file_name,
            user_id=user_id,
            timestamp=processing_result.get("processing_status", {}).get("completed_at", ""),
            processing_status="completed",
            processing_statistics=processing_statistics,
            artifacts_summary=artifacts_summary,
        )

        return await self._send_har_webhook(payload, "har_processing_completed")

    async def send_har_processing_failed(
        self, upload_id: int, file_name: str, user_id: int, processing_result: Dict
    ) -> bool:
        """
        Send notification when HAR processing fails.

        Args:
            upload_id: ID of the HAR upload
            file_name: Name of the processed HAR file
            user_id: ID of the user who owns the upload
            processing_result: Result dictionary from HAR processing

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        # Extract processing statistics (may be limited for failed runs)
        processing_statistics = self._extract_har_processing_statistics(processing_result)

        payload = N8nHARProcessingWebhookPayload(
            event_type="har_processing_failed",
            upload_id=upload_id,
            file_name=file_name,
            user_id=user_id,
            timestamp=processing_result.get("processing_status", {}).get("failed_at", ""),
            processing_status="failed",
            processing_statistics=processing_statistics,
            artifacts_summary=None,
            error_message=processing_result.get("error", "Unknown error"),
        )

        return await self._send_har_webhook(payload, "har_processing_failed")

    async def send_har_review_requested(
        self, upload_id: int, file_name: str, user_id: int, processing_result: Dict, review_url: str
    ) -> bool:
        """
        Send notification requesting review of AI-generated HAR artifacts.

        Args:
            upload_id: ID of the HAR upload
            file_name: Name of the processed HAR file
            user_id: ID of the user who owns the upload
            processing_result: Result dictionary from HAR processing
            review_url: URL for reviewing the generated artifacts

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.debug("n8n notifications disabled - no webhook URL configured")
            return True

        # Extract processing statistics and artifacts summary
        processing_statistics = self._extract_har_processing_statistics(processing_result)
        artifacts_summary = self._extract_har_artifacts_summary(processing_result)

        payload = N8nHARReviewWebhookPayload(
            event_type="har_review_requested",
            upload_id=upload_id,
            file_name=file_name,
            user_id=user_id,
            timestamp=processing_result.get("processing_status", {}).get("completed_at", ""),
            artifacts_summary=artifacts_summary,
            review_url=review_url,
            processing_statistics=processing_statistics,
        )

        return await self._send_har_review_webhook(payload, "har_review_requested")

    def _extract_har_processing_statistics(self, processing_result: Dict) -> Dict:
        """
        Extract processing statistics from HAR processing result.

        Args:
            processing_result: Result dictionary from HAR processing

        Returns:
            Dictionary containing processing statistics
        """
        artifacts = processing_result.get("artifacts", {})
        metadata = artifacts.get("processing_metadata", {})
        processing_status = processing_result.get("processing_status", {})

        return {
            "interactions_count": metadata.get("interactions_count", 0),
            "processed_interactions_count": metadata.get("processed_interactions_count", 0),
            "openapi_paths_count": metadata.get("openapi_paths_count", 0),
            "wiremock_stubs_count": metadata.get("wiremock_stubs_count", 0),
            "processing_steps_completed": len(
                [
                    step
                    for step in processing_status.get("steps", {}).values()
                    if step.get("status") == "completed"
                ]
            ),
            "total_processing_steps": len(processing_status.get("steps", {})),
            "processing_progress": processing_status.get("progress", 0),
            "processing_options": metadata.get("processing_options", {}),
        }

    def _extract_har_artifacts_summary(self, processing_result: Dict) -> Dict:
        """
        Extract artifacts summary from HAR processing result.

        Args:
            processing_result: Result dictionary from HAR processing

        Returns:
            Dictionary containing artifacts summary
        """
        artifacts = processing_result.get("artifacts", {})
        openapi_spec = artifacts.get("openapi_specification", {})
        wiremock_mappings = artifacts.get("wiremock_mappings", [])

        return {
            "openapi_available": bool(openapi_spec),
            "openapi_title": openapi_spec.get("info", {}).get("title", ""),
            "openapi_version": openapi_spec.get("info", {}).get("version", ""),
            "openapi_paths_count": len(openapi_spec.get("paths", {})),
            "wiremock_available": bool(wiremock_mappings),
            "wiremock_stubs_count": len(wiremock_mappings),
            "artifacts_generated_at": artifacts.get("processing_metadata", {}).get(
                "processed_at", ""
            ),
        }

    def _extract_validation_statistics(self, validation_results: Optional[Dict]) -> Dict:
        """
        Extract validation statistics from Schemathesis results.

        Args:
            validation_results: Raw validation results from Schemathesis

        Returns:
            Dictionary containing validation statistics
        """
        if not validation_results:
            return {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0,
                "execution_time": 0.0,
                "error_count": 0,
                "test_results_count": 0,
            }

        # Handle error cases
        if "error" in validation_results:
            return {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0,
                "execution_time": 0.0,
                "error_count": 1,
                "error_message": validation_results["error"],
                "test_results_count": 0,
            }

        # Extract from summary if available, otherwise from top-level
        summary = validation_results.get("summary", validation_results)

        return {
            "total_tests": summary.get("total_tests", 0),
            "passed_tests": summary.get("passed_tests", 0),
            "failed_tests": summary.get("failed_tests", 0),
            "success_rate": summary.get("success_rate", 0.0),
            "execution_time": summary.get("execution_time", 0.0),
            "error_count": summary.get("error_count", len(validation_results.get("errors", []))),
            "test_results_count": len(validation_results.get("test_results", [])),
        }

    async def _send_har_webhook(
        self, payload: N8nHARProcessingWebhookPayload, event_name: str
    ) -> bool:
        """
        Send HAR processing webhook to n8n with retry logic.

        Args:
            payload: The HAR processing webhook payload
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
                            f"Successfully sent n8n HAR webhook for {event_name} "
                            f"(upload_id: {payload.upload_id}, "
                            f"user_id: {payload.user_id}, "
                            f"attempt: {attempt})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"n8n HAR webhook failed for {event_name} "
                            f"(upload_id: {payload.upload_id}, "
                            f"user_id: {payload.user_id}, "
                            f"attempt: {attempt}, "
                            f"status: {response.status_code}, "
                            f"response: {response.text})"
                        )

            except httpx.TimeoutException:
                logger.warning(
                    f"n8n HAR webhook timeout for {event_name} "
                    f"(upload_id: {payload.upload_id}, "
                    f"user_id: {payload.user_id}, "
                    f"attempt: {attempt})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"n8n HAR webhook request error for {event_name} "
                    f"(upload_id: {payload.upload_id}, "
                    f"user_id: {payload.user_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error sending n8n HAR webhook for {event_name} "
                    f"(upload_id: {payload.upload_id}, "
                    f"user_id: {payload.user_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )

            # Wait before retrying (except on last attempt)
            if attempt < self.max_retries:
                logger.info(
                    f"Retrying n8n HAR webhook for {event_name} "
                    f"in {self.retry_delay} seconds "
                    f"(upload_id: {payload.upload_id}, "
                    f"user_id: {payload.user_id}, "
                    f"attempt: {attempt + 1}/{self.max_retries})"
                )
                time.sleep(self.retry_delay)

        logger.error(
            f"Failed to send n8n HAR webhook for {event_name} "
            f"after {self.max_retries} attempts "
            f"(upload_id: {payload.upload_id}, "
            f"user_id: {payload.user_id})"
        )
        return False

    async def _send_har_review_webhook(
        self, payload: N8nHARReviewWebhookPayload, event_name: str
    ) -> bool:
        """
        Send HAR review request webhook to n8n with retry logic.

        Args:
            payload: The HAR review webhook payload
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
                            f"Successfully sent n8n HAR review webhook for {event_name} "
                            f"(upload_id: {payload.upload_id}, "
                            f"user_id: {payload.user_id}, "
                            f"attempt: {attempt})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"n8n HAR review webhook failed for {event_name} "
                            f"(upload_id: {payload.upload_id}, "
                            f"user_id: {payload.user_id}, "
                            f"attempt: {attempt}, "
                            f"status: {response.status_code}, "
                            f"response: {response.text})"
                        )

            except httpx.TimeoutException:
                logger.warning(
                    f"n8n HAR review webhook timeout for {event_name} "
                    f"(upload_id: {payload.upload_id}, "
                    f"user_id: {payload.user_id}, "
                    f"attempt: {attempt})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"n8n HAR review webhook request error for {event_name} "
                    f"(upload_id: {payload.upload_id}, "
                    f"user_id: {payload.user_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error sending n8n HAR review webhook for {event_name} "
                    f"(upload_id: {payload.upload_id}, "
                    f"user_id: {payload.user_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )

            # Wait before retrying (except on last attempt)
            if attempt < self.max_retries:
                logger.info(
                    f"Retrying n8n HAR review webhook for {event_name} "
                    f"in {self.retry_delay} seconds "
                    f"(upload_id: {payload.upload_id}, "
                    f"user_id: {payload.user_id}, "
                    f"attempt: {attempt + 1}/{self.max_retries})"
                )
                time.sleep(self.retry_delay)

        logger.error(
            f"Failed to send n8n HAR review webhook for {event_name} "
            f"after {self.max_retries} attempts "
            f"(upload_id: {payload.upload_id}, "
            f"user_id: {payload.user_id})"
        )
        return False

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

    async def _send_contract_validation_webhook(
        self, payload: N8nContractValidationWebhookPayload, event_name: str
    ) -> bool:
        """
        Send contract validation webhook to n8n with retry logic.

        Args:
            payload: The contract validation webhook payload
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
                            f"Successfully sent n8n contract validation webhook for {event_name} "
                            f"(contract_validation_id: {payload.contract_validation_id}, "
                            f"spec_id: {payload.specification_id}, "
                            f"health_status: {payload.contract_health_status}, "
                            f"attempt: {attempt})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"n8n contract validation webhook failed for {event_name} "
                            f"(contract_validation_id: {payload.contract_validation_id}, "
                            f"spec_id: {payload.specification_id}, "
                            f"attempt: {attempt}, "
                            f"status: {response.status_code}, "
                            f"response: {response.text})"
                        )

            except httpx.TimeoutException:
                logger.warning(
                    f"n8n contract validation webhook timeout for {event_name} "
                    f"(contract_validation_id: {payload.contract_validation_id}, "
                    f"spec_id: {payload.specification_id}, "
                    f"attempt: {attempt})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"n8n contract validation webhook request error for {event_name} "
                    f"(contract_validation_id: {payload.contract_validation_id}, "
                    f"spec_id: {payload.specification_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error sending n8n contract validation webhook for {event_name} "
                    f"(contract_validation_id: {payload.contract_validation_id}, "
                    f"spec_id: {payload.specification_id}, "
                    f"attempt: {attempt}, error: {str(e)})"
                )

            # Wait before retrying (except on last attempt)
            if attempt < self.max_retries:
                logger.info(
                    f"Retrying n8n contract validation webhook for {event_name} "
                    f"in {self.retry_delay} seconds "
                    f"(contract_validation_id: {payload.contract_validation_id}, "
                    f"spec_id: {payload.specification_id}, "
                    f"attempt: {attempt + 1}/{self.max_retries})"
                )
                time.sleep(self.retry_delay)

        logger.error(
            f"Failed to send n8n contract validation webhook for {event_name} "
            f"after {self.max_retries} attempts "
            f"(contract_validation_id: {payload.contract_validation_id}, "
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
