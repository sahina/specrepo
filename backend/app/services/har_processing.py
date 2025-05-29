import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import User
from app.services.har_ai_processor import HARDataProcessor
from app.services.har_parser import HARParser
from app.services.har_to_openapi import HARToOpenAPITransformer
from app.services.har_to_wiremock import HARToWireMockTransformer
from app.services.har_uploads import HARUploadService
from app.services.n8n_notifications import n8n_service

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Status of HAR processing."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStep(Enum):
    """Steps in the HAR processing pipeline."""

    PARSING = "parsing"
    AI_PROCESSING = "ai_processing"
    OPENAPI_GENERATION = "openapi_generation"
    WIREMOCK_GENERATION = "wiremock_generation"
    STORING_ARTIFACTS = "storing_artifacts"


class HARProcessingService:
    """Service for orchestrating HAR file processing and artifact generation."""

    def __init__(self):
        """Initialize the HAR processing service."""
        self.har_parser = HARParser()
        self.ai_processor = HARDataProcessor()
        self.openapi_transformer = HARToOpenAPITransformer()
        self.wiremock_transformer = HARToWireMockTransformer()

    async def process_har_upload(
        self,
        db: Session,
        upload_id: int,
        user: User,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a HAR upload and generate artifacts.

        Args:
            db: Database session
            upload_id: ID of the HAR upload to process
            user: User who owns the upload
            options: Optional processing options

        Returns:
            Dictionary with processing results and artifacts

        Raises:
            ValueError: If upload not found or processing fails
        """
        # Get the HAR upload
        upload = HARUploadService.get_har_upload(db, upload_id, user)
        if not upload:
            raise ValueError(f"HAR upload with ID {upload_id} not found")

        logger.info(f"Starting HAR processing for upload {upload_id}")

        try:
            # Initialize processing status
            processing_status = {
                "status": ProcessingStatus.RUNNING.value,
                "current_step": ProcessingStep.PARSING.value,
                "progress": 0,
                "started_at": datetime.now().isoformat(),
                "steps": {
                    ProcessingStep.PARSING.value: {"status": "running", "progress": 0},
                    ProcessingStep.AI_PROCESSING.value: {"status": "pending", "progress": 0},
                    ProcessingStep.OPENAPI_GENERATION.value: {"status": "pending", "progress": 0},
                    ProcessingStep.WIREMOCK_GENERATION.value: {"status": "pending", "progress": 0},
                    ProcessingStep.STORING_ARTIFACTS.value: {"status": "pending", "progress": 0},
                },
            }

            # Step 1: Parse HAR content
            logger.info(f"Step 1: Parsing HAR content for upload {upload_id}")
            processing_status["current_step"] = ProcessingStep.PARSING.value
            processing_status["progress"] = 10

            interactions = self.har_parser.parse_har_content(upload.raw_content)
            if not interactions:
                raise ValueError("No API interactions found in HAR file")

            processing_status["steps"][ProcessingStep.PARSING.value] = {
                "status": "completed",
                "progress": 100,
                "result": f"Found {len(interactions)} API interactions",
            }

            # Step 2: AI Processing and Data Generalization
            logger.info(f"Step 2: AI processing for upload {upload_id}")
            processing_status["current_step"] = ProcessingStep.AI_PROCESSING.value
            processing_status["progress"] = 30

            # Process interactions with AI for pattern recognition and data generalization
            processed_interactions = []
            for interaction in interactions:
                try:
                    # Apply AI processing to analyze and generalize data
                    analysis = self.ai_processor.process_har_interaction(interaction)

                    # Apply generalizations to request body if available
                    if interaction.request.body and analysis.get("request_analysis", {}).get(
                        "body_analysis"
                    ):
                        body_analysis = analysis["request_analysis"]["body_analysis"]
                        if hasattr(body_analysis, "generalized"):
                            # Convert generalized data back to string if it's JSON
                            if (
                                interaction.request.content_type
                                and "json" in interaction.request.content_type.lower()
                            ):
                                import json

                                interaction.request.body = json.dumps(body_analysis.generalized)
                            else:
                                interaction.request.body = str(body_analysis.generalized)

                    # Apply generalizations to response body if available
                    if interaction.response.body and analysis.get("response_analysis", {}).get(
                        "body_analysis"
                    ):
                        body_analysis = analysis["response_analysis"]["body_analysis"]
                        if hasattr(body_analysis, "generalized"):
                            # Convert generalized data back to string if it's JSON
                            if (
                                interaction.response.content_type
                                and "json" in interaction.response.content_type.lower()
                            ):
                                import json

                                interaction.response.body = json.dumps(body_analysis.generalized)
                            else:
                                interaction.response.body = str(body_analysis.generalized)

                    processed_interactions.append(interaction)
                except Exception as e:
                    logger.warning(f"AI processing failed for interaction: {e}")
                    # Use original interaction if AI processing fails
                    processed_interactions.append(interaction)

            processing_status["steps"][ProcessingStep.AI_PROCESSING.value] = {
                "status": "completed",
                "progress": 100,
                "result": f"Processed {len(processed_interactions)} interactions",
            }

            # Step 3: Generate OpenAPI specification
            logger.info(f"Step 3: Generating OpenAPI specification for upload {upload_id}")
            processing_status["current_step"] = ProcessingStep.OPENAPI_GENERATION.value
            processing_status["progress"] = 60

            # Convert interactions back to HAR content for the transformer
            har_content = self._interactions_to_har_content(processed_interactions)

            # Ensure options is not None
            safe_options = options or {}

            openapi_spec = self.openapi_transformer.transform_har_to_openapi(
                har_content,
                title=safe_options.get("api_title", f"API from {upload.file_name}"),
                version=safe_options.get("api_version", "1.0.0"),
                description=safe_options.get(
                    "api_description", f"Generated from HAR file: {upload.file_name}"
                ),
            )

            processing_status["steps"][ProcessingStep.OPENAPI_GENERATION.value] = {
                "status": "completed",
                "progress": 100,
                "result": f"Generated OpenAPI spec with {len(openapi_spec.get('paths', {}))} paths",
            }

            # Step 4: Generate WireMock stubs
            logger.info(f"Step 4: Generating WireMock stubs for upload {upload_id}")
            processing_status["current_step"] = ProcessingStep.WIREMOCK_GENERATION.value
            processing_status["progress"] = 80

            wiremock_stubs = self.wiremock_transformer.transform_interactions(
                processed_interactions
            )

            # Convert stubs to JSON format for storage
            wiremock_mappings = []
            for stub in wiremock_stubs:
                mapping = {
                    "request": stub.request,
                    "response": stub.response,
                }
                if stub.metadata:
                    mapping["metadata"] = stub.metadata
                wiremock_mappings.append(mapping)

            processing_status["steps"][ProcessingStep.WIREMOCK_GENERATION.value] = {
                "status": "completed",
                "progress": 100,
                "result": f"Generated {len(wiremock_mappings)} WireMock stubs",
            }

            # Step 5: Store artifacts
            logger.info(f"Step 5: Storing artifacts for upload {upload_id}")
            processing_status["current_step"] = ProcessingStep.STORING_ARTIFACTS.value
            processing_status["progress"] = 90

            artifacts = {
                "openapi_specification": openapi_spec,
                "wiremock_mappings": wiremock_mappings,
                "processing_metadata": {
                    "interactions_count": len(interactions),
                    "processed_interactions_count": len(processed_interactions),
                    "openapi_paths_count": len(openapi_spec.get("paths", {})),
                    "wiremock_stubs_count": len(wiremock_mappings),
                    "processed_at": datetime.now().isoformat(),
                    "processing_options": safe_options,
                },
            }

            # Update the HAR upload with artifacts
            updated_upload = HARUploadService.update_processed_artifacts(
                db, upload_id, user, artifacts
            )

            if not updated_upload:
                raise ValueError("Failed to store artifacts in database")

            processing_status["steps"][ProcessingStep.STORING_ARTIFACTS.value] = {
                "status": "completed",
                "progress": 100,
                "result": "Artifacts stored successfully",
            }

            # Final status
            processing_status["status"] = ProcessingStatus.COMPLETED.value
            processing_status["progress"] = 100
            processing_status["completed_at"] = datetime.now().isoformat()

            logger.info(f"HAR processing completed successfully for upload {upload_id}")

            # Prepare result for notifications
            result = {
                "success": True,
                "upload_id": upload_id,
                "processing_status": processing_status,
                "artifacts": artifacts,
            }

            # Send n8n notifications
            try:
                # Send user notification (HAR processed & sketches ready)
                await n8n_service.send_har_processing_completed(
                    upload_id=upload_id,
                    file_name=upload.file_name,
                    user_id=user.id,
                    processing_result=result,
                )

                # Send reviewer notification (review request for AI-generated artifacts)
                # Generate review URL for the artifacts
                review_url = f"http://localhost:5173/har-uploads/{upload_id}/review"
                await n8n_service.send_har_review_requested(
                    upload_id=upload_id,
                    file_name=upload.file_name,
                    user_id=user.id,
                    processing_result=result,
                    review_url=review_url,
                )

                logger.info(f"Successfully sent n8n notifications for HAR upload {upload_id}")
            except Exception as e:
                logger.warning(f"Failed to send n8n notifications for HAR upload {upload_id}: {e}")
                # Don't fail the entire processing if notifications fail

            return result

        except Exception as e:
            logger.error(f"HAR processing failed for upload {upload_id}: {e}")

            # Update processing status with error
            processing_status["status"] = ProcessingStatus.FAILED.value
            processing_status["error"] = str(e)
            processing_status["failed_at"] = datetime.now().isoformat()

            # Prepare result for notifications
            result = {
                "success": False,
                "upload_id": upload_id,
                "processing_status": processing_status,
                "error": str(e),
            }

            # Send failure notification
            try:
                await n8n_service.send_har_processing_failed(
                    upload_id=upload_id,
                    file_name=upload.file_name,
                    user_id=user.id,
                    processing_result=result,
                )
                logger.info(
                    f"Successfully sent n8n failure notification for HAR upload {upload_id}"
                )
            except Exception as notification_error:
                logger.warning(
                    f"Failed to send n8n failure notification for HAR upload {upload_id}: "
                    f"{notification_error}"
                )
                # Don't fail the entire processing if notifications fail

            return result

    def get_processing_status(
        self, db: Session, upload_id: int, user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Get the processing status for a HAR upload.

        Args:
            db: Database session
            upload_id: ID of the HAR upload
            user: User who owns the upload

        Returns:
            Processing status dictionary or None if not found
        """
        upload = HARUploadService.get_har_upload(db, upload_id, user)
        if not upload:
            return None

        # Check if artifacts exist to determine status
        if upload.processed_artifacts_references:
            artifacts = upload.processed_artifacts_references
            metadata = artifacts.get("processing_metadata", {})

            return {
                "status": ProcessingStatus.COMPLETED.value,
                "progress": 100,
                "completed_at": metadata.get("processed_at"),
                "artifacts_available": True,
                "interactions_count": metadata.get("interactions_count", 0),
                "openapi_paths_count": metadata.get("openapi_paths_count", 0),
                "wiremock_stubs_count": metadata.get("wiremock_stubs_count", 0),
            }
        else:
            return {
                "status": ProcessingStatus.PENDING.value,
                "progress": 0,
                "artifacts_available": False,
            }

    def get_artifacts(self, db: Session, upload_id: int, user: User) -> Optional[Dict[str, Any]]:
        """
        Get the generated artifacts for a HAR upload.

        Args:
            db: Database session
            upload_id: ID of the HAR upload
            user: User who owns the upload

        Returns:
            Artifacts dictionary or None if not found
        """
        upload = HARUploadService.get_har_upload(db, upload_id, user)
        if not upload or not upload.processed_artifacts_references:
            return None

        return upload.processed_artifacts_references

    def validate_processing_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize processing options.

        Args:
            options: Raw processing options

        Returns:
            Validated and normalized options
        """
        validated_options = {}

        # API title and description options
        if "api_title" in options:
            validated_options["api_title"] = str(options["api_title"])[:100]

        if "api_description" in options:
            validated_options["api_description"] = str(options["api_description"])[:500]

        if "api_version" in options:
            validated_options["api_version"] = str(options["api_version"])[:20]

        # Processing options
        if "enable_ai_processing" in options:
            validated_options["enable_ai_processing"] = bool(options["enable_ai_processing"])
        else:
            validated_options["enable_ai_processing"] = True

        if "enable_data_generalization" in options:
            validated_options["enable_data_generalization"] = bool(
                options["enable_data_generalization"]
            )
        else:
            validated_options["enable_data_generalization"] = True

        # WireMock options
        if "wiremock_stateful" in options:
            validated_options["wiremock_stateful"] = bool(options["wiremock_stateful"])
        else:
            validated_options["wiremock_stateful"] = True

        if "wiremock_templating" in options:
            validated_options["wiremock_templating"] = bool(options["wiremock_templating"])
        else:
            validated_options["wiremock_templating"] = True

        return validated_options

    def _interactions_to_har_content(self, interactions) -> str:
        """Convert processed interactions back to HAR format."""
        import json
        from datetime import datetime

        entries = []
        for interaction in interactions:
            entry = {
                "startedDateTime": interaction.request.timestamp or datetime.now().isoformat(),
                "time": interaction.duration or 0,
                "request": {
                    "method": interaction.request.method,
                    "url": interaction.request.url,
                    "httpVersion": "HTTP/1.1",
                    "headers": [
                        {"name": k, "value": v} for k, v in interaction.request.headers.items()
                    ],
                    "queryString": [
                        {"name": k, "value": v[0] if v else ""}
                        for k, v in interaction.request.query_params.items()
                    ],
                    "cookies": [],
                    "headersSize": -1,
                    "bodySize": len(interaction.request.body) if interaction.request.body else 0,
                },
                "response": {
                    "status": interaction.response.status,
                    "statusText": interaction.response.status_text or "",
                    "httpVersion": "HTTP/1.1",
                    "headers": [
                        {"name": k, "value": v} for k, v in interaction.response.headers.items()
                    ],
                    "cookies": [],
                    "content": {
                        "size": interaction.response.size or 0,
                        "mimeType": interaction.response.content_type or "application/json",
                        "text": interaction.response.body or "",
                    },
                    "redirectURL": "",
                    "headersSize": -1,
                    "bodySize": interaction.response.size or 0,
                },
                "cache": {},
                "timings": {
                    "blocked": -1,
                    "dns": -1,
                    "connect": -1,
                    "send": 0,
                    "wait": interaction.duration or 0,
                    "receive": 0,
                    "ssl": -1,
                },
            }

            # Add request body if present
            if interaction.request.body:
                entry["request"]["postData"] = {
                    "mimeType": interaction.request.content_type or "application/json",
                    "text": interaction.request.body,
                }

            entries.append(entry)

        har_data = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "SpecRepo HAR Processor",
                    "version": "1.0.0",
                },
                "entries": entries,
            }
        }

        return json.dumps(har_data)
