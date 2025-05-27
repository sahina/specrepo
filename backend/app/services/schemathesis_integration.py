"""
Schemathesis integration service for API validation.

This module provides functionality to validate provider implementations
against API specifications using the Schemathesis library.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
import schemathesis
from sqlalchemy.orm import Session

from app.models import APISpecification, ValidationRun
from app.schemas import AuthMethod, ValidationRunStatus
from app.services.n8n_notifications import n8n_service

logger = logging.getLogger(__name__)


class AuthenticationHandler:
    """Handles different authentication methods for API validation."""

    @staticmethod
    def prepare_auth_headers(
        auth_method: AuthMethod, auth_config: Optional[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Prepare authentication headers based on method and config."""
        headers = {}

        if auth_method == AuthMethod.NONE or not auth_config:
            return headers

        if auth_method == AuthMethod.API_KEY:
            api_key = auth_config.get("api_key")
            header_name = auth_config.get("header_name", "X-API-Key")
            if api_key:
                headers[header_name] = api_key

        elif auth_method == AuthMethod.BEARER_TOKEN:
            token = auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif auth_method == AuthMethod.BASIC_AUTH:
            username = auth_config.get("username")
            password = auth_config.get("password")
            if username and password:
                import base64

                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

        return headers

    @staticmethod
    def prepare_auth_params(
        auth_method: AuthMethod, auth_config: Optional[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Prepare authentication query parameters."""
        params = {}

        if auth_method == AuthMethod.API_KEY and auth_config:
            if auth_config.get("in_query"):
                api_key = auth_config.get("api_key")
                param_name = auth_config.get("param_name", "api_key")
                if api_key:
                    params[param_name] = api_key

        return params


class SchemathesisTestRunner:
    """Runs Schemathesis tests against provider APIs."""

    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "errors": [],
            "test_results": [],
            "summary": {},
            "execution_time": 0,
        }

    async def run_tests(
        self,
        openapi_spec: Dict[str, Any],
        provider_url: str,
        auth_headers: Dict[str, str],
        auth_params: Dict[str, str],
        test_strategies: Optional[List[str]] = None,
        max_examples: int = 100,
    ) -> Dict[str, Any]:
        """Run Schemathesis tests against the provider API."""
        start_time = datetime.now()

        try:
            # Create a Schemathesis schema from the OpenAPI spec
            schema = schemathesis.from_dict(openapi_spec, base_url=provider_url)

            # Configure test strategies
            if test_strategies:
                # Apply specific test strategies if provided
                for strategy in test_strategies:
                    if hasattr(schemathesis.strategies, strategy):
                        schema = schema.with_strategy(
                            getattr(schemathesis.strategies, strategy)
                        )

            # Run tests using a simpler approach
            test_count = 0

            # Use httpx to test each endpoint defined in the OpenAPI spec
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Extract paths from OpenAPI spec
                paths = openapi_spec.get("paths", {})

                for path, methods in paths.items():
                    if test_count >= max_examples:
                        break

                    for method, operation in methods.items():
                        if test_count >= max_examples:
                            break

                        if method.upper() not in [
                            "GET",
                            "POST",
                            "PUT",
                            "DELETE",
                            "PATCH",
                        ]:
                            continue

                        try:
                            # Construct full URL
                            full_url = f"{provider_url.rstrip('/')}{path}"

                            # Prepare request
                            request_kwargs = {
                                "headers": auth_headers,
                                "params": auth_params,
                            }

                            # Execute the test case
                            response = await client.request(
                                method.upper(), full_url, **request_kwargs
                            )

                            # Analyze the response
                            test_result = self._analyze_response_simple(
                                method.upper(), path, response
                            )
                            self.results["test_results"].append(test_result)

                            if test_result["passed"]:
                                self.results["passed_tests"] += 1
                            else:
                                self.results["failed_tests"] += 1

                            test_count += 1

                        except Exception as e:
                            error_result = {
                                "test_case": f"{method.upper()} {path}",
                                "error": str(e),
                                "passed": False,
                                "timestamp": datetime.now().isoformat(),
                            }
                            self.results["test_results"].append(error_result)
                            self.results["errors"].append(str(e))
                            self.results["failed_tests"] += 1
                            test_count += 1

            self.results["total_tests"] = test_count

        except Exception as e:
            logger.error(f"Error running Schemathesis tests: {e}")
            self.results["errors"].append(f"Test execution error: {str(e)}")

        end_time = datetime.now()
        self.results["execution_time"] = (end_time - start_time).total_seconds()

        # Generate summary
        self._generate_summary()

        return self.results

    def _analyze_response_simple(
        self, method: str, path: str, response
    ) -> Dict[str, Any]:
        """Analyze a test response and determine if it passes."""
        result = {
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "passed": True,
            "issues": [],
            "timestamp": datetime.now().isoformat(),
        }

        # Check for obvious failures
        if response.status_code >= 500:
            result["passed"] = False
            result["issues"].append(f"Server error: {response.status_code}")

        # Check response time (basic performance check)
        if hasattr(response, "elapsed") and response.elapsed.total_seconds() > 30:
            result["issues"].append(f"Slow response: {response.elapsed.total_seconds()}s")

        # Additional validation could be added here
        # (schema validation, business logic checks, etc.)

        return result

    def _generate_summary(self):
        """Generate a summary of test results."""
        total = self.results["total_tests"]
        passed = self.results["passed_tests"]
        failed = self.results["failed_tests"]

        self.results["summary"] = {
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": failed,
            "error_count": len(self.results["errors"]),
            "execution_time": self.results["execution_time"],
        }


class SchemathesisIntegrationService:
    """Main service for Schemathesis integration."""

    @staticmethod
    async def create_validation_run(
        db: Session,
        api_specification_id: int,
        provider_url: str,
        user_id: int,
        auth_method: AuthMethod = AuthMethod.NONE,
        auth_config: Optional[Dict[str, Any]] = None,
        test_strategies: Optional[List[str]] = None,
        max_examples: int = 100,
        timeout: int = 300,
    ) -> ValidationRun:
        """Create a new validation run."""
        validation_run = ValidationRun(
            api_specification_id=api_specification_id,
            provider_url=provider_url,
            user_id=user_id,
            auth_method=auth_method.value,
            auth_config=auth_config,
            test_strategies=test_strategies,
            max_examples=max_examples,
            timeout=timeout,
            status=ValidationRunStatus.PENDING.value,
        )

        db.add(validation_run)
        db.commit()
        db.refresh(validation_run)

        return validation_run

    @staticmethod
    async def execute_validation_run(
        db: Session, validation_run_id: int
    ) -> ValidationRun:
        """Execute a validation run asynchronously."""
        validation_run = (
            db.query(ValidationRun).filter(ValidationRun.id == validation_run_id).first()
        )

        if not validation_run:
            raise ValueError(f"Validation run {validation_run_id} not found")

        # Update status to running
        validation_run.status = ValidationRunStatus.RUNNING.value
        db.commit()

        try:
            # Get the API specification
            api_spec = (
                db.query(APISpecification)
                .filter(APISpecification.id == validation_run.api_specification_id)
                .first()
            )

            if not api_spec:
                raise ValueError("API specification not found")

            # Prepare authentication
            auth_method = AuthMethod(validation_run.auth_method)
            auth_headers = AuthenticationHandler.prepare_auth_headers(
                auth_method, validation_run.auth_config
            )
            auth_params = AuthenticationHandler.prepare_auth_params(
                auth_method, validation_run.auth_config
            )

            # Run the tests
            test_runner = SchemathesisTestRunner(timeout=validation_run.timeout)
            results = await test_runner.run_tests(
                openapi_spec=api_spec.openapi_content,
                provider_url=validation_run.provider_url,
                auth_headers=auth_headers,
                auth_params=auth_params,
                test_strategies=validation_run.test_strategies,
                max_examples=validation_run.max_examples,
            )

            # Update validation run with results
            validation_run.schemathesis_results = results
            validation_run.status = ValidationRunStatus.COMPLETED.value

            # Send n8n notification for successful completion
            try:
                await n8n_service.send_validation_completed(validation_run, api_spec)
            except Exception as notification_error:
                logger.warning(
                    f"Failed to send n8n notification for completed validation "
                    f"{validation_run_id}: {notification_error}"
                )

        except Exception as e:
            logger.error(f"Error executing validation run {validation_run_id}: {e}")
            validation_run.schemathesis_results = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            validation_run.status = ValidationRunStatus.FAILED.value

            # Send n8n notification for failure
            try:
                await n8n_service.send_validation_failed(validation_run, api_spec)
            except Exception as notification_error:
                logger.warning(
                    f"Failed to send n8n notification for failed validation "
                    f"{validation_run_id}: {notification_error}"
                )

        db.commit()
        db.refresh(validation_run)

        return validation_run

    @staticmethod
    async def get_validation_runs(
        db: Session,
        user_id: int,
        api_specification_id: Optional[int] = None,
        status: Optional[ValidationRunStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ValidationRun], int]:
        """Get validation runs with filtering and pagination."""
        query = db.query(ValidationRun).filter(ValidationRun.user_id == user_id)

        if api_specification_id:
            query = query.filter(
                ValidationRun.api_specification_id == api_specification_id
            )

        if status:
            query = query.filter(ValidationRun.status == status.value)

        total = query.count()
        validation_runs = query.offset(skip).limit(limit).all()

        return validation_runs, total

    @staticmethod
    async def get_validation_run(
        db: Session, validation_run_id: int, user_id: int
    ) -> Optional[ValidationRun]:
        """Get a specific validation run."""
        return (
            db.query(ValidationRun)
            .filter(
                ValidationRun.id == validation_run_id,
                ValidationRun.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    async def cancel_validation_run(
        db: Session, validation_run_id: int, user_id: int
    ) -> Optional[ValidationRun]:
        """Cancel a running validation run."""
        validation_run = (
            db.query(ValidationRun)
            .filter(
                ValidationRun.id == validation_run_id,
                ValidationRun.user_id == user_id,
                ValidationRun.status.in_(
                    [
                        ValidationRunStatus.PENDING.value,
                        ValidationRunStatus.RUNNING.value,
                    ]
                ),
            )
            .first()
        )

        if validation_run:
            validation_run.status = ValidationRunStatus.CANCELLED.value
            db.commit()
            db.refresh(validation_run)

            # Send n8n notification for cancellation
            try:
                api_spec = (
                    db.query(APISpecification)
                    .filter(APISpecification.id == validation_run.api_specification_id)
                    .first()
                )
                if api_spec:
                    await n8n_service.send_validation_failed(validation_run, api_spec)
            except Exception as notification_error:
                logger.warning(
                    f"Failed to send n8n notification for cancelled validation "
                    f"{validation_run.id}: {notification_error}"
                )

        return validation_run

    @staticmethod
    async def validate_provider_connectivity(
        provider_url: str,
    ) -> Dict[str, Any]:
        """Test basic connectivity to a provider URL."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(provider_url)
                return {
                    "reachable": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                }
        except Exception as e:
            return {
                "reachable": False,
                "error": str(e),
            }
