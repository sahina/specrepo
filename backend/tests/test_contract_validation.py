"""
Tests for contract validation functionality.

This module tests the end-to-end contract validation workflow including
service logic, health analysis, and API endpoints.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import APISpecification, ContractValidation, Environment, User, ValidationRun
from app.schemas import AuthMethod, ContractHealthStatus, ContractValidationStatus
from app.services.contract_validation import (
    ContractHealthAnalyzer,
    ContractValidationService,
    MockAlignmentChecker,
)


class TestContractHealthAnalyzer:
    """Test contract health analysis logic."""

    def test_calculate_health_score_healthy(self):
        """Test health score calculation for healthy contract."""
        producer_results = {
            "total_tests": 10,
            "passed_tests": 10,
            "failed_tests": 0,
            "errors": [],
            "execution_time": 15,
        }

        mock_alignment_results = {
            "total_endpoints": 5,
            "aligned_endpoints": 5,
            "schema_mismatches": 0,
            "alignment_rate": 1.0,
        }

        score = ContractHealthAnalyzer.calculate_health_score(
            producer_results, mock_alignment_results
        )

        assert score >= 0.8
        assert score <= 1.0

    def test_calculate_health_score_degraded(self):
        """Test health score calculation for degraded contract."""
        producer_results = {
            "total_tests": 10,
            "passed_tests": 7,
            "failed_tests": 3,
            "errors": ["Connection timeout"],
            "execution_time": 45,
        }

        mock_alignment_results = {
            "total_endpoints": 5,
            "aligned_endpoints": 4,
            "schema_mismatches": 1,
            "alignment_rate": 0.8,
        }

        score = ContractHealthAnalyzer.calculate_health_score(
            producer_results, mock_alignment_results
        )

        assert score >= 0.5
        assert score < 0.8

    def test_calculate_health_score_broken(self):
        """Test health score calculation for broken contract."""
        producer_results = {
            "total_tests": 10,
            "passed_tests": 2,
            "failed_tests": 8,
            "errors": ["Connection refused", "Timeout", "Invalid response"],
            "execution_time": 120,
        }

        mock_alignment_results = {
            "total_endpoints": 5,
            "aligned_endpoints": 1,
            "schema_mismatches": 4,
            "alignment_rate": 0.2,
        }

        score = ContractHealthAnalyzer.calculate_health_score(
            producer_results, mock_alignment_results
        )

        assert score < 0.5

    def test_determine_health_status(self):
        """Test health status determination from score."""
        assert ContractHealthAnalyzer.determine_health_status(0.9) == ContractHealthStatus.HEALTHY
        assert ContractHealthAnalyzer.determine_health_status(0.8) == ContractHealthStatus.HEALTHY
        assert ContractHealthAnalyzer.determine_health_status(0.7) == ContractHealthStatus.DEGRADED
        assert ContractHealthAnalyzer.determine_health_status(0.5) == ContractHealthStatus.DEGRADED
        assert ContractHealthAnalyzer.determine_health_status(0.4) == ContractHealthStatus.BROKEN
        assert ContractHealthAnalyzer.determine_health_status(0.0) == ContractHealthStatus.BROKEN

    def test_generate_validation_summary(self):
        """Test validation summary generation."""
        producer_results = {
            "total_tests": 10,
            "passed_tests": 8,
            "failed_tests": 2,
            "errors": ["Timeout"],
            "execution_time": 30,
        }

        mock_alignment_results = {
            "total_endpoints": 5,
            "aligned_endpoints": 4,
            "schema_mismatches": 1,
            "alignment_rate": 0.8,
        }

        health_score = 0.75
        health_status = ContractHealthStatus.DEGRADED

        summary = ContractHealthAnalyzer.generate_validation_summary(
            producer_results, mock_alignment_results, health_score, health_status
        )

        assert summary["health_score"] == 0.75
        assert summary["health_status"] == "degraded"
        assert "timestamp" in summary
        assert "producer_validation" in summary
        assert "mock_alignment" in summary
        assert "recommendations" in summary
        assert isinstance(summary["recommendations"], list)


class TestMockAlignmentChecker:
    """Test mock alignment checking logic."""

    @pytest.fixture
    def mock_wiremock_service(self):
        """Create a mock WireMock service."""
        service = MagicMock()
        service.get_all_stubs = AsyncMock()
        return service

    @pytest.fixture
    def alignment_checker(self, mock_wiremock_service):
        """Create a mock alignment checker."""
        return MockAlignmentChecker(mock_wiremock_service)

    @pytest.mark.asyncio
    async def test_check_alignment_no_mock_config(self, alignment_checker):
        """Test alignment check when no mock configuration exists."""
        openapi_spec = {"paths": {"/users": {"get": {}}}}

        result = await alignment_checker.check_alignment(openapi_spec, None, {})

        assert result["total_endpoints"] == 0
        assert result["aligned_endpoints"] == 0
        assert result["alignment_rate"] == 0.0
        assert "No mock configuration found" in result["details"]

    @pytest.mark.asyncio
    async def test_check_alignment_with_mocks(self, alignment_checker, mock_wiremock_service):
        """Test alignment check with deployed mocks."""
        openapi_spec = {
            "paths": {
                "/users": {"get": {"summary": "Get users"}},
                "/users/{id}": {"get": {"summary": "Get user by ID"}},
            }
        }

        deployed_stubs = [
            {
                "request": {
                    "method": "GET",
                    "urlPattern": "/users",
                },
                "response": {"status": 200},
            },
            {
                "request": {
                    "method": "GET",
                    "urlPattern": "/users/([^/]+)",
                },
                "response": {"status": 200},
            },
        ]

        mock_wiremock_service.get_all_stubs.return_value = deployed_stubs
        mock_config = MagicMock()

        result = await alignment_checker.check_alignment(openapi_spec, mock_config, {})

        assert result["total_endpoints"] == 2
        assert result["aligned_endpoints"] == 2
        assert result["alignment_rate"] == 1.0


class TestContractValidationService:
    """Test contract validation service."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock(spec=Session)
        return db

    @pytest.fixture
    def contract_service(self):
        """Create a contract validation service with mocked dependencies."""
        with (
            patch("app.services.contract_validation.SchemathesisIntegrationService"),
            patch("app.services.contract_validation.WireMockIntegrationService"),
            patch("app.services.contract_validation.MockConfigurationService"),
        ):
            return ContractValidationService()

    @pytest.fixture
    def sample_api_spec(self):
        """Create a sample API specification."""
        spec = MagicMock(spec=APISpecification)
        spec.id = 1
        spec.user_id = 1
        spec.openapi_content = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {"/users": {"get": {}}},
        }
        return spec

    @pytest.fixture
    def sample_environment(self):
        """Create a sample environment."""
        env = MagicMock(spec=Environment)
        env.id = 1
        env.base_url = "https://api.example.com"
        return env

    @pytest.mark.asyncio
    async def test_create_contract_validation_success(
        self, contract_service, mock_db, sample_api_spec, sample_environment
    ):
        """Test successful contract validation creation."""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_api_spec,  # API specification query
            sample_environment,  # Environment query
            None,  # Mock configuration query
        ]

        # Mock validation run creation
        mock_validation_run = MagicMock(spec=ValidationRun)
        mock_validation_run.id = 1
        contract_service.schemathesis_service.create_validation_run = AsyncMock(
            return_value=mock_validation_run
        )

        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = await contract_service.create_contract_validation(
            db=mock_db,
            api_specification_id=1,
            user_id=1,
            environment_id=1,
            auth_method=AuthMethod.NONE,
        )

        assert isinstance(result, ContractValidation)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_contract_validation_api_spec_not_found(self, contract_service, mock_db):
        """Test contract validation creation when API spec not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="API specification not found"):
            await contract_service.create_contract_validation(
                db=mock_db,
                api_specification_id=999,
                user_id=1,
                provider_url="https://api.example.com",
            )

    @pytest.mark.asyncio
    async def test_execute_contract_validation_with_notifications_success(
        self, contract_service, mock_db, sample_api_spec
    ):
        """Test contract validation execution with successful n8n notifications."""
        # Create contract validation
        contract_validation = ContractValidation(
            id=1,
            api_specification_id=sample_api_spec.id,
            user_id=123,
            status=ContractValidationStatus.PENDING.value,
            triggered_at=datetime.now(),
            validation_run_id=1,
        )

        # Mock validation run
        validation_run = ValidationRun(
            id=1,
            api_specification_id=sample_api_spec.id,
            user_id=123,
            status="completed",
            triggered_at=datetime.now(),
            schemathesis_results={
                "total_tests": 10,
                "passed_tests": 9,
                "failed_tests": 1,
                "execution_time": 30,
                "errors": [],
            },
        )

        # Setup database mocks
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            contract_validation,  # First call for contract validation
            sample_api_spec,  # Second call for API specification
            None,  # Third call for mock configuration (None)
        ]

        # Mock schemathesis service
        contract_service.schemathesis_service.execute_validation_run = AsyncMock(
            return_value=validation_run
        )

        # Mock wiremock service for alignment check
        contract_service.wiremock_service.get_all_stubs = AsyncMock(return_value=[])

        # Mock n8n service
        contract_service.n8n_service.send_contract_validation_completed = AsyncMock(
            return_value=True
        )

        # Execute contract validation
        result = await contract_service.execute_contract_validation(mock_db, 1)

        # Verify contract validation completed successfully
        assert result.status == ContractValidationStatus.COMPLETED.value
        assert result.health_score is not None
        assert result.contract_health_status is not None

        # Verify n8n notification was sent
        contract_service.n8n_service.send_contract_validation_completed.assert_called_once_with(
            contract_validation, sample_api_spec
        )

    @pytest.mark.asyncio
    async def test_execute_contract_validation_with_notifications_failure(
        self, contract_service, mock_db, sample_api_spec
    ):
        """Test contract validation execution with n8n notifications on failure."""
        # Create contract validation
        contract_validation = ContractValidation(
            id=1,
            api_specification_id=sample_api_spec.id,
            user_id=123,
            status=ContractValidationStatus.PENDING.value,
            triggered_at=datetime.now(),
            validation_run_id=1,
        )

        # Setup database mocks
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            contract_validation,  # First call for contract validation
            sample_api_spec,  # Second call for API specification (for notification)
        ]

        # Mock schemathesis service to raise an exception
        contract_service.schemathesis_service.execute_validation_run = AsyncMock(
            side_effect=Exception("Validation failed")
        )

        # Mock n8n service
        contract_service.n8n_service.send_contract_validation_failed = AsyncMock(return_value=True)

        # Execute contract validation and expect it to raise an exception
        with pytest.raises(Exception, match="Validation failed"):
            await contract_service.execute_contract_validation(mock_db, 1)

        # Verify contract validation status was updated to failed
        assert contract_validation.status == ContractValidationStatus.FAILED.value

        # Verify n8n failure notification was sent
        contract_service.n8n_service.send_contract_validation_failed.assert_called_once_with(
            contract_validation, sample_api_spec
        )

    @pytest.mark.asyncio
    async def test_execute_contract_validation_notification_failure_continues(
        self, contract_service, mock_db, sample_api_spec
    ):
        """Test that contract validation continues even if notification fails."""
        # Create contract validation
        contract_validation = ContractValidation(
            id=1,
            api_specification_id=sample_api_spec.id,
            user_id=123,
            status=ContractValidationStatus.PENDING.value,
            triggered_at=datetime.now(),
            validation_run_id=1,
        )

        # Mock validation run
        validation_run = ValidationRun(
            id=1,
            api_specification_id=sample_api_spec.id,
            user_id=123,
            status="completed",
            triggered_at=datetime.now(),
            schemathesis_results={
                "total_tests": 10,
                "passed_tests": 10,
                "failed_tests": 0,
                "execution_time": 20,
                "errors": [],
            },
        )

        # Setup database mocks
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            contract_validation,  # First call for contract validation
            sample_api_spec,  # Second call for API specification
            None,  # Third call for mock configuration (None)
        ]

        # Mock schemathesis service
        contract_service.schemathesis_service.execute_validation_run = AsyncMock(
            return_value=validation_run
        )

        # Mock wiremock service for alignment check
        contract_service.wiremock_service.get_all_stubs = AsyncMock(return_value=[])

        # Mock n8n service that fails
        contract_service.n8n_service.send_contract_validation_completed = AsyncMock(
            side_effect=Exception("Notification failed")
        )

        # Execute contract validation - should succeed despite notification failure
        result = await contract_service.execute_contract_validation(mock_db, 1)

        # Verify contract validation completed successfully
        assert result.status == ContractValidationStatus.COMPLETED.value
        assert result.health_score is not None
        assert result.contract_health_status is not None

        # Verify notification was attempted
        contract_service.n8n_service.send_contract_validation_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contract_validations(self, contract_service, mock_db):
        """Test getting contract validations with filtering."""
        mock_validations = [MagicMock(spec=ContractValidation) for _ in range(3)]

        # Mock the query chain properly - need to handle multiple filter calls
        mock_query = MagicMock()
        mock_query.count.return_value = 3
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            mock_validations
        )

        # Set up the filter chain to return our mock query
        # The service calls filter twice, so we need to chain them
        mock_db.query.return_value.filter.return_value.filter.return_value = mock_query

        validations, total = await contract_service.get_contract_validations(
            db=mock_db,
            user_id=1,
            api_specification_id=1,
            skip=0,
            limit=10,
        )

        assert len(validations) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_contract_health_summary(self, contract_service, mock_db):
        """Test getting contract health summary."""
        mock_validations = []
        for i, status in enumerate(
            [
                ContractHealthStatus.HEALTHY.value,
                ContractHealthStatus.DEGRADED.value,
                ContractHealthStatus.BROKEN.value,
            ]
        ):
            validation = MagicMock(spec=ContractValidation)
            validation.contract_health_status = status
            validation.health_score = 0.8 - (i * 0.3)
            validation.triggered_at = datetime.now()
            mock_validations.append(validation)

        mock_db.query.return_value.filter.return_value.all.return_value = mock_validations

        summary = await contract_service.get_contract_health_summary(
            db=mock_db,
            api_specification_id=1,
            user_id=1,
        )

        assert summary["total_validations"] == 3
        assert summary["healthy_count"] == 1
        assert summary["degraded_count"] == 1
        assert summary["broken_count"] == 1
        assert "average_health_score" in summary
        assert "latest_validation" in summary


class TestContractValidationEndpoints:
    """Test contract validation API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from main import app

        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"X-API-Key": "test-api-key"}

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"
        return mock_user

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock(spec=Session)

    def test_create_contract_validation_endpoint(
        self, client, auth_headers, mock_user, mock_db_session
    ):
        """Test contract validation creation endpoint."""
        from app.dependencies import get_current_user, get_db
        from main import app

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db_session

        try:
            with patch(
                "app.routers.contract_validations.contract_validation_service"
            ) as mock_service:
                # Mock service
                mock_validation = MagicMock(spec=ContractValidation)
                mock_validation.id = 1
                mock_validation.api_specification_id = 1
                mock_validation.status = ContractValidationStatus.PENDING.value
                mock_validation.health_score = 0.0
                mock_validation.contract_health_status = ContractHealthStatus.HEALTHY.value
                mock_validation.triggered_at = datetime.now()
                mock_validation.user_id = 1
                mock_validation.provider_url = "https://api.example.com"
                mock_validation.validation_run_id = 1
                mock_validation.environment_id = None
                mock_validation.mock_configuration_id = None
                mock_validation.completed_at = None
                mock_validation.producer_validation_results = None
                mock_validation.mock_alignment_results = None
                mock_validation.validation_summary = None

                mock_service.create_contract_validation = AsyncMock(return_value=mock_validation)

                response = client.post(
                    "/api/contract-validations/",
                    json={
                        "api_specification_id": 1,
                        "provider_url": "https://api.example.com",
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 201
                data = response.json()
                assert data["id"] == 1
                assert data["api_specification_id"] == 1
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    def test_list_contract_validations_endpoint(
        self, client, auth_headers, mock_user, mock_db_session
    ):
        """Test contract validations listing endpoint."""
        from app.dependencies import get_current_user, get_db
        from main import app

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db_session

        try:
            with patch(
                "app.routers.contract_validations.contract_validation_service"
            ) as mock_service:
                # Mock service
                mock_validations = []
                mock_service.get_contract_validations = AsyncMock(
                    return_value=(mock_validations, 0)
                )

                response = client.get(
                    "/api/contract-validations/",
                    headers=auth_headers,
                )

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
                assert "total" in data
                assert "page" in data
                assert "size" in data
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    def test_get_contract_validation_endpoint(
        self, client, auth_headers, mock_user, mock_db_session
    ):
        """Test getting specific contract validation endpoint."""
        from app.dependencies import get_current_user, get_db
        from main import app

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db_session

        try:
            with patch(
                "app.routers.contract_validations.contract_validation_service"
            ) as mock_service:
                # Mock service
                mock_validation = MagicMock(spec=ContractValidation)
                mock_validation.id = 1
                mock_validation.api_specification_id = 1
                mock_validation.status = ContractValidationStatus.COMPLETED.value
                mock_validation.health_score = 0.85
                mock_validation.contract_health_status = ContractHealthStatus.HEALTHY.value
                mock_validation.triggered_at = datetime.now()
                mock_validation.completed_at = datetime.now()
                mock_validation.user_id = 1
                mock_validation.provider_url = "https://api.example.com"
                mock_validation.validation_run_id = 1
                mock_validation.environment_id = None
                mock_validation.mock_configuration_id = None
                mock_validation.producer_validation_results = {}
                mock_validation.mock_alignment_results = {}
                mock_validation.validation_summary = {}

                mock_service.get_contract_validation = AsyncMock(return_value=mock_validation)

                response = client.get(
                    "/api/contract-validations/1",
                    headers=auth_headers,
                )

                assert response.status_code == 200
                data = response.json()
                assert data["id"] == 1
                assert data["api_specification_id"] == 1
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    def test_get_contract_validation_not_found(
        self, client, auth_headers, mock_user, mock_db_session
    ):
        """Test getting non-existent contract validation."""
        from app.dependencies import get_current_user, get_db
        from main import app

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db_session

        try:
            with patch(
                "app.routers.contract_validations.contract_validation_service"
            ) as mock_service:
                # Mock service
                mock_service.get_contract_validation = AsyncMock(return_value=None)

                response = client.get(
                    "/api/contract-validations/999",
                    headers=auth_headers,
                )

                assert response.status_code == 404
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()

    def test_get_health_summary_endpoint(self, client, auth_headers, mock_user, mock_db_session):
        """Test contract health summary endpoint."""
        from app.dependencies import get_current_user, get_db
        from main import app

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db_session

        try:
            with patch(
                "app.routers.contract_validations.contract_validation_service"
            ) as mock_service:
                # Mock service
                mock_summary = {
                    "total_validations": 5,
                    "healthy_count": 3,
                    "degraded_count": 1,
                    "broken_count": 1,
                    "average_health_score": 0.75,
                    "latest_validation": None,
                }
                mock_service.get_contract_health_summary = AsyncMock(return_value=mock_summary)

                response = client.get(
                    "/api/contract-validations/specifications/1/health-summary",
                    headers=auth_headers,
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total_validations"] == 5
                assert data["healthy_count"] == 3
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()
