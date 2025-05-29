"""
Contract validation service for end-to-end contract validation workflow.

This module provides functionality to orchestrate the complete contract validation
process including producer validation, mock alignment verification, and contract
health determination.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import (
    APISpecification,
    ContractValidation,
    Environment,
    MockConfiguration,
    ValidationRun,
)
from app.schemas import AuthMethod, ContractHealthStatus, ContractValidationStatus
from app.services.mock_configuration import MockConfigurationService
from app.services.schemathesis_integration import SchemathesisIntegrationService
from app.services.wiremock_integration import WireMockIntegrationService

logger = logging.getLogger(__name__)


class ContractHealthAnalyzer:
    """Analyzes validation results to determine contract health."""

    @staticmethod
    def calculate_health_score(
        producer_results: Dict[str, Any],
        mock_alignment_results: Dict[str, Any],
    ) -> float:
        """
        Calculate overall health score based on validation results.

        Args:
            producer_results: Schemathesis validation results
            mock_alignment_results: Mock alignment check results

        Returns:
            Health score between 0.0 and 1.0
        """
        # Producer validation score (70% weight)
        producer_score = ContractHealthAnalyzer._calculate_producer_score(producer_results)

        # Mock alignment score (30% weight)
        mock_score = ContractHealthAnalyzer._calculate_mock_alignment_score(mock_alignment_results)

        # Weighted average
        overall_score = (producer_score * 0.7) + (mock_score * 0.3)

        return round(overall_score, 3)

    @staticmethod
    def _calculate_producer_score(producer_results: Dict[str, Any]) -> float:
        """Calculate score based on producer validation results."""
        if not producer_results:
            return 0.0

        total_tests = producer_results.get("total_tests", 0)
        passed_tests = producer_results.get("passed_tests", 0)

        if total_tests == 0:
            return 0.0

        # Base score from pass rate
        pass_rate = passed_tests / total_tests

        # Penalty for errors
        errors = producer_results.get("errors", [])
        error_penalty = min(len(errors) * 0.1, 0.5)  # Max 50% penalty

        # Penalty for slow responses
        execution_time = producer_results.get("execution_time", 0)
        if execution_time > 30:  # More than 30 seconds
            time_penalty = min((execution_time - 30) / 60 * 0.2, 0.3)  # Max 30% penalty
        else:
            time_penalty = 0

        score = max(0.0, pass_rate - error_penalty - time_penalty)
        return score

    @staticmethod
    def _calculate_mock_alignment_score(mock_alignment_results: Dict[str, Any]) -> float:
        """Calculate score based on mock alignment results."""
        if not mock_alignment_results:
            return 0.5  # Neutral score if no mock alignment check

        aligned_endpoints = mock_alignment_results.get("aligned_endpoints", 0)
        total_endpoints = mock_alignment_results.get("total_endpoints", 0)

        if total_endpoints == 0:
            return 0.5

        alignment_rate = aligned_endpoints / total_endpoints

        # Penalty for mismatched schemas
        schema_mismatches = mock_alignment_results.get("schema_mismatches", 0)
        mismatch_penalty = min(schema_mismatches * 0.1, 0.4)  # Max 40% penalty

        score = max(0.0, alignment_rate - mismatch_penalty)
        return score

    @staticmethod
    def determine_health_status(health_score: float) -> ContractHealthStatus:
        """
        Determine contract health status based on score.

        Args:
            health_score: Health score between 0.0 and 1.0

        Returns:
            Contract health status
        """
        if health_score >= 0.8:
            return ContractHealthStatus.HEALTHY
        elif health_score >= 0.5:
            return ContractHealthStatus.DEGRADED
        else:
            return ContractHealthStatus.BROKEN

    @staticmethod
    def generate_validation_summary(
        producer_results: Dict[str, Any],
        mock_alignment_results: Dict[str, Any],
        health_score: float,
        health_status: ContractHealthStatus,
    ) -> Dict[str, Any]:
        """Generate comprehensive validation summary."""
        summary = {
            "health_score": health_score,
            "health_status": health_status.value,
            "timestamp": datetime.now().isoformat(),
            "producer_validation": {
                "total_tests": producer_results.get("total_tests", 0),
                "passed_tests": producer_results.get("passed_tests", 0),
                "failed_tests": producer_results.get("failed_tests", 0),
                "error_count": len(producer_results.get("errors", [])),
                "execution_time": producer_results.get("execution_time", 0),
            },
            "mock_alignment": {
                "total_endpoints": mock_alignment_results.get("total_endpoints", 0),
                "aligned_endpoints": mock_alignment_results.get("aligned_endpoints", 0),
                "schema_mismatches": mock_alignment_results.get("schema_mismatches", 0),
                "alignment_rate": mock_alignment_results.get("alignment_rate", 0.0),
            },
            "recommendations": ContractHealthAnalyzer._generate_recommendations(
                producer_results, mock_alignment_results, health_status
            ),
        }

        return summary

    @staticmethod
    def _generate_recommendations(
        producer_results: Dict[str, Any],
        mock_alignment_results: Dict[str, Any],
        health_status: ContractHealthStatus,
    ) -> List[str]:
        """Generate actionable recommendations based on validation results."""
        recommendations = []

        if health_status == ContractHealthStatus.BROKEN:
            recommendations.append("Immediate attention required - contract is broken")

        # Producer-specific recommendations
        failed_tests = producer_results.get("failed_tests", 0)
        total_tests = producer_results.get("total_tests", 0)

        if total_tests > 0 and failed_tests / total_tests > 0.3:
            recommendations.append("High failure rate detected - review API implementation")

        errors = producer_results.get("errors", [])
        if len(errors) > 5:
            recommendations.append(
                "Multiple errors detected - check API connectivity and configuration"
            )

        execution_time = producer_results.get("execution_time", 0)
        if execution_time > 60:
            recommendations.append("Slow response times detected - optimize API performance")

        # Mock alignment recommendations
        schema_mismatches = mock_alignment_results.get("schema_mismatches", 0)
        if schema_mismatches > 0:
            recommendations.append("Schema mismatches found - update mocks or API specification")

        alignment_rate = mock_alignment_results.get("alignment_rate", 1.0)
        if alignment_rate < 0.8:
            recommendations.append("Poor mock alignment - review mock configurations")

        if not recommendations and health_status == ContractHealthStatus.HEALTHY:
            recommendations.append("Contract is healthy - continue monitoring")

        return recommendations


class MockAlignmentChecker:
    """Checks alignment between producer API and deployed mocks."""

    def __init__(self, wiremock_service: WireMockIntegrationService):
        self.wiremock_service = wiremock_service

    async def check_alignment(
        self,
        openapi_spec: Dict[str, Any],
        mock_configuration: Optional[MockConfiguration],
        producer_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check alignment between producer API and deployed mocks.

        Args:
            openapi_spec: OpenAPI specification
            mock_configuration: Deployed mock configuration
            producer_results: Producer validation results

        Returns:
            Mock alignment results
        """
        if not mock_configuration:
            return {
                "total_endpoints": 0,
                "aligned_endpoints": 0,
                "schema_mismatches": 0,
                "alignment_rate": 0.0,
                "details": "No mock configuration found",
            }

        try:
            # Get deployed stubs from WireMock
            deployed_stubs = await self.wiremock_service.get_all_stubs()

            # Extract endpoints from OpenAPI spec
            spec_endpoints = self._extract_spec_endpoints(openapi_spec)

            # Compare with deployed mocks
            alignment_results = self._compare_endpoints_with_mocks(
                spec_endpoints, deployed_stubs, producer_results
            )

            return alignment_results

        except Exception as e:
            logger.error(f"Error checking mock alignment: {e}")
            return {
                "total_endpoints": 0,
                "aligned_endpoints": 0,
                "schema_mismatches": 0,
                "alignment_rate": 0.0,
                "error": str(e),
            }

    def _extract_spec_endpoints(self, openapi_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract endpoint information from OpenAPI specification."""
        endpoints = []
        paths = openapi_spec.get("paths", {})

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    endpoints.append(
                        {
                            "path": path,
                            "method": method.upper(),
                            "operation": operation,
                        }
                    )

        return endpoints

    def _compare_endpoints_with_mocks(
        self,
        spec_endpoints: List[Dict[str, Any]],
        deployed_stubs: List[Dict[str, Any]],
        producer_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare specification endpoints with deployed mock stubs."""
        total_endpoints = len(spec_endpoints)
        aligned_endpoints = 0
        schema_mismatches = 0

        # Create a mapping of deployed stubs for easier lookup
        stub_mapping = {}
        for stub in deployed_stubs:
            request = stub.get("request", {})
            method = request.get("method", "").upper()
            url_pattern = request.get("urlPattern", "")

            key = f"{method}:{url_pattern}"
            stub_mapping[key] = stub

        # Check each specification endpoint
        for endpoint in spec_endpoints:
            path = endpoint["path"]
            method = endpoint["method"]

            # Convert OpenAPI path to WireMock pattern
            wiremock_pattern = self._convert_path_to_pattern(path)
            key = f"{method}:{wiremock_pattern}"

            if key in stub_mapping:
                aligned_endpoints += 1

                # Check for schema mismatches
                if self._has_schema_mismatch(endpoint, stub_mapping[key], producer_results):
                    schema_mismatches += 1

        alignment_rate = aligned_endpoints / total_endpoints if total_endpoints > 0 else 0.0

        return {
            "total_endpoints": total_endpoints,
            "aligned_endpoints": aligned_endpoints,
            "schema_mismatches": schema_mismatches,
            "alignment_rate": alignment_rate,
            "details": f"Checked {total_endpoints} endpoints, {aligned_endpoints} aligned",
        }

    def _convert_path_to_pattern(self, openapi_path: str) -> str:
        """Convert OpenAPI path to WireMock URL pattern."""
        # Convert {param} to ([^/]+) for WireMock regex
        import re

        pattern = re.sub(r"\{[^}]+\}", r"([^/]+)", openapi_path)
        return pattern

    def _has_schema_mismatch(
        self,
        endpoint: Dict[str, Any],
        stub: Dict[str, Any],
        producer_results: Dict[str, Any],
    ) -> bool:
        """Check if there's a schema mismatch between endpoint and stub."""
        # This is a simplified check - in a real implementation,
        # you would compare response schemas more thoroughly

        # Check if the producer test for this endpoint failed
        test_results = producer_results.get("test_results", [])
        endpoint_path = endpoint["path"]
        endpoint_method = endpoint["method"]

        for test_result in test_results:
            test_case = test_result.get("test_case", "")
            if f"{endpoint_method} {endpoint_path}" in test_case:
                return not test_result.get("passed", False)

        return False


class ContractValidationService:
    """Service for orchestrating end-to-end contract validation."""

    def __init__(self):
        self.schemathesis_service = SchemathesisIntegrationService()
        self.wiremock_service = WireMockIntegrationService()
        self.mock_service = MockConfigurationService()
        self.health_analyzer = ContractHealthAnalyzer()

    async def create_contract_validation(
        self,
        db: Session,
        api_specification_id: int,
        user_id: int,
        environment_id: Optional[int] = None,
        provider_url: Optional[str] = None,
        auth_method: AuthMethod = AuthMethod.NONE,
        auth_config: Optional[Dict[str, Any]] = None,
        test_strategies: Optional[List[str]] = None,
        max_examples: int = 100,
        timeout: int = 300,
    ) -> ContractValidation:
        """
        Create a new contract validation run.

        Args:
            db: Database session
            api_specification_id: ID of the API specification
            user_id: ID of the user triggering validation
            environment_id: Optional environment ID
            provider_url: Optional custom provider URL
            auth_method: Authentication method
            auth_config: Authentication configuration
            test_strategies: Test strategies to use
            max_examples: Maximum test examples
            timeout: Timeout in seconds

        Returns:
            Created ContractValidation instance
        """
        # Get API specification
        api_spec = (
            db.query(APISpecification)
            .filter(
                APISpecification.id == api_specification_id, APISpecification.user_id == user_id
            )
            .first()
        )

        if not api_spec:
            raise ValueError("API specification not found")

        # Determine provider URL
        final_provider_url = provider_url
        if environment_id:
            environment = (
                db.query(Environment)
                .filter(Environment.id == environment_id, Environment.user_id == user_id)
                .first()
            )
            if environment:
                final_provider_url = environment.base_url
            else:
                raise ValueError("Environment not found")

        if not final_provider_url:
            raise ValueError("Provider URL must be specified")

        # Create validation run first
        validation_run = await self.schemathesis_service.create_validation_run(
            db=db,
            api_specification_id=api_specification_id,
            user_id=user_id,
            environment_id=environment_id,
            provider_url=final_provider_url,
            auth_method=auth_method,
            auth_config=auth_config,
            test_strategies=test_strategies,
            max_examples=max_examples,
            timeout=timeout,
        )

        # Get latest mock configuration for this specification
        mock_config = (
            db.query(MockConfiguration)
            .filter(
                MockConfiguration.api_specification_id == api_specification_id,
                MockConfiguration.status == "active",
            )
            .order_by(MockConfiguration.deployed_at.desc())
            .first()
        )

        # Create contract validation record
        contract_validation = ContractValidation(
            api_specification_id=api_specification_id,
            environment_id=environment_id,
            provider_url=final_provider_url,
            validation_run_id=validation_run.id,
            mock_configuration_id=mock_config.id if mock_config else None,
            contract_health_status=ContractHealthStatus.HEALTHY.value,  # Will be updated
            health_score=0.0,  # Will be calculated
            status=ContractValidationStatus.PENDING.value,
            user_id=user_id,
        )

        db.add(contract_validation)
        db.commit()
        db.refresh(contract_validation)

        return contract_validation

    async def execute_contract_validation(
        self, db: Session, contract_validation_id: int
    ) -> ContractValidation:
        """
        Execute the complete contract validation workflow.

        Args:
            db: Database session
            contract_validation_id: ID of the contract validation

        Returns:
            Updated ContractValidation instance
        """
        # Get contract validation
        contract_validation = (
            db.query(ContractValidation)
            .filter(ContractValidation.id == contract_validation_id)
            .first()
        )

        if not contract_validation:
            raise ValueError("Contract validation not found")

        try:
            # Update status to running
            contract_validation.status = ContractValidationStatus.RUNNING.value
            db.commit()

            # Step 1: Execute producer validation using Schemathesis
            logger.info(
                f"Starting producer validation for contract validation {contract_validation_id}"
            )
            validation_run = await self.schemathesis_service.execute_validation_run(
                db, contract_validation.validation_run_id
            )

            producer_results = validation_run.schemathesis_results or {}
            contract_validation.producer_validation_results = producer_results

            # Step 2: Check mock alignment
            logger.info(f"Checking mock alignment for contract validation {contract_validation_id}")
            api_spec = (
                db.query(APISpecification)
                .filter(APISpecification.id == contract_validation.api_specification_id)
                .first()
            )

            mock_config = None
            if contract_validation.mock_configuration_id:
                mock_config = (
                    db.query(MockConfiguration)
                    .filter(MockConfiguration.id == contract_validation.mock_configuration_id)
                    .first()
                )

            mock_checker = MockAlignmentChecker(self.wiremock_service)
            mock_alignment_results = await mock_checker.check_alignment(
                api_spec.openapi_content, mock_config, producer_results
            )

            contract_validation.mock_alignment_results = mock_alignment_results

            # Step 3: Calculate contract health
            logger.info(
                f"Calculating contract health for contract validation {contract_validation_id}"
            )
            health_score = self.health_analyzer.calculate_health_score(
                producer_results, mock_alignment_results
            )

            health_status = self.health_analyzer.determine_health_status(health_score)

            # Step 4: Generate validation summary
            validation_summary = self.health_analyzer.generate_validation_summary(
                producer_results, mock_alignment_results, health_score, health_status
            )

            # Update contract validation with results
            contract_validation.health_score = health_score
            contract_validation.contract_health_status = health_status.value
            contract_validation.validation_summary = validation_summary
            contract_validation.status = ContractValidationStatus.COMPLETED.value
            contract_validation.completed_at = datetime.now()

            db.commit()
            db.refresh(contract_validation)

            logger.info(
                f"Contract validation {contract_validation_id} completed with health status: {health_status.value}"
            )

            return contract_validation

        except Exception as e:
            logger.error(f"Error executing contract validation {contract_validation_id}: {e}")

            # Update status to failed
            contract_validation.status = ContractValidationStatus.FAILED.value
            contract_validation.validation_summary = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            contract_validation.completed_at = datetime.now()

            db.commit()
            db.refresh(contract_validation)

            raise

    async def get_contract_validations(
        self,
        db: Session,
        user_id: int,
        api_specification_id: Optional[int] = None,
        status: Optional[ContractValidationStatus] = None,
        contract_health_status: Optional[ContractHealthStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ContractValidation], int]:
        """
        Get contract validations with filtering.

        Args:
            db: Database session
            user_id: User ID for filtering
            api_specification_id: Optional API specification filter
            status: Optional status filter
            contract_health_status: Optional health status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (validations list, total count)
        """
        query = db.query(ContractValidation).filter(ContractValidation.user_id == user_id)

        if api_specification_id:
            query = query.filter(ContractValidation.api_specification_id == api_specification_id)

        if status:
            query = query.filter(ContractValidation.status == status.value)

        if contract_health_status:
            query = query.filter(
                ContractValidation.contract_health_status == contract_health_status.value
            )

        total = query.count()

        validations = (
            query.order_by(ContractValidation.triggered_at.desc()).offset(skip).limit(limit).all()
        )

        return validations, total

    async def get_contract_validation(
        self, db: Session, contract_validation_id: int, user_id: int
    ) -> Optional[ContractValidation]:
        """Get a specific contract validation by ID."""
        return (
            db.query(ContractValidation)
            .filter(
                ContractValidation.id == contract_validation_id,
                ContractValidation.user_id == user_id,
            )
            .first()
        )

    async def get_contract_health_summary(
        self, db: Session, api_specification_id: int, user_id: int
    ) -> Dict[str, Any]:
        """
        Get contract health summary for an API specification.

        Args:
            db: Database session
            api_specification_id: API specification ID
            user_id: User ID

        Returns:
            Contract health summary
        """
        validations = (
            db.query(ContractValidation)
            .filter(
                ContractValidation.api_specification_id == api_specification_id,
                ContractValidation.user_id == user_id,
                ContractValidation.status == ContractValidationStatus.COMPLETED.value,
            )
            .all()
        )

        if not validations:
            return {
                "total_validations": 0,
                "healthy_count": 0,
                "degraded_count": 0,
                "broken_count": 0,
                "average_health_score": 0.0,
                "latest_validation": None,
            }

        total_validations = len(validations)
        healthy_count = sum(
            1 for v in validations if v.contract_health_status == ContractHealthStatus.HEALTHY.value
        )
        degraded_count = sum(
            1
            for v in validations
            if v.contract_health_status == ContractHealthStatus.DEGRADED.value
        )
        broken_count = sum(
            1 for v in validations if v.contract_health_status == ContractHealthStatus.BROKEN.value
        )

        average_health_score = sum(v.health_score for v in validations) / total_validations

        latest_validation = max(validations, key=lambda v: v.triggered_at)

        return {
            "total_validations": total_validations,
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "broken_count": broken_count,
            "average_health_score": round(average_health_score, 3),
            "latest_validation": latest_validation,
        }
