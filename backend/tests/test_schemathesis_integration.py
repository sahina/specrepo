"""
Tests for Schemathesis integration service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import APISpecification, User, ValidationRun
from app.schemas import AuthMethod, ValidationRunStatus
from app.services.schemathesis_integration import (
    AuthenticationHandler,
    SchemathesisIntegrationService,
    SchemathesisTestRunner,
)


@pytest.fixture
def sample_user(db_session):
    """Create a test user."""
    import uuid

    user = User(
        username=f"testuser-{uuid.uuid4().hex[:8]}",
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        api_key=f"test-api-key-{uuid.uuid4().hex}",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_api_spec(db_session, sample_user):
    """Create a test API specification."""
    openapi_content = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "Get users",
                    "responses": {"200": {"description": "Success"}},
                }
            },
            "/users/{id}": {
                "get": {
                    "summary": "Get user by ID",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "Success"}},
                }
            },
        },
    }

    api_spec = APISpecification(
        name="Test API",
        version_string="1.0.0",
        openapi_content=openapi_content,
        user_id=sample_user.id,
    )
    db_session.add(api_spec)
    db_session.commit()
    db_session.refresh(api_spec)
    return api_spec


@pytest.fixture
def sample_validation_run(db_session, sample_api_spec, sample_user):
    """Create a test validation run."""
    validation_run = ValidationRun(
        api_specification_id=sample_api_spec.id,
        provider_url="https://api.example.com",
        user_id=sample_user.id,
        auth_method=AuthMethod.NONE.value,
        status=ValidationRunStatus.PENDING.value,
    )
    db_session.add(validation_run)
    db_session.commit()
    db_session.refresh(validation_run)
    return validation_run


class TestAuthenticationHandler:
    """Test authentication handler functionality."""

    def test_prepare_auth_headers_none(self):
        """Test preparing headers with no authentication."""
        headers = AuthenticationHandler.prepare_auth_headers(
            AuthMethod.NONE, None
        )
        assert headers == {}

    def test_prepare_auth_headers_api_key(self):
        """Test preparing headers with API key authentication."""
        auth_config = {"api_key": "test-key", "header_name": "X-API-Key"}
        headers = AuthenticationHandler.prepare_auth_headers(
            AuthMethod.API_KEY, auth_config
        )
        assert headers == {"X-API-Key": "test-key"}

    def test_prepare_auth_headers_api_key_default_header(self):
        """Test preparing headers with API key using default header name."""
        auth_config = {"api_key": "test-key"}
        headers = AuthenticationHandler.prepare_auth_headers(
            AuthMethod.API_KEY, auth_config
        )
        assert headers == {"X-API-Key": "test-key"}

    def test_prepare_auth_headers_bearer_token(self):
        """Test preparing headers with Bearer token authentication."""
        auth_config = {"token": "test-token"}
        headers = AuthenticationHandler.prepare_auth_headers(
            AuthMethod.BEARER_TOKEN, auth_config
        )
        assert headers == {"Authorization": "Bearer test-token"}

    def test_prepare_auth_headers_basic_auth(self):
        """Test preparing headers with Basic authentication."""
        auth_config = {"username": "user", "password": "pass"}
        headers = AuthenticationHandler.prepare_auth_headers(
            AuthMethod.BASIC_AUTH, auth_config
        )
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_prepare_auth_params_none(self):
        """Test preparing query params with no authentication."""
        params = AuthenticationHandler.prepare_auth_params(
            AuthMethod.NONE, None
        )
        assert params == {}

    def test_prepare_auth_params_api_key_in_query(self):
        """Test preparing query params with API key in query."""
        auth_config = {
            "api_key": "test-key",
            "in_query": True,
            "param_name": "apikey",
        }
        params = AuthenticationHandler.prepare_auth_params(
            AuthMethod.API_KEY, auth_config
        )
        assert params == {"apikey": "test-key"}

    def test_prepare_auth_params_api_key_not_in_query(self):
        """Test preparing query params with API key not in query."""
        auth_config = {"api_key": "test-key", "in_query": False}
        params = AuthenticationHandler.prepare_auth_params(
            AuthMethod.API_KEY, auth_config
        )
        assert params == {}


class TestSchemathesisTestRunner:
    """Test Schemathesis test runner functionality."""

    @pytest.mark.asyncio
    async def test_run_tests_basic(self):
        """Test basic test execution."""
        runner = SchemathesisTestRunner(timeout=60)

        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {"responses": {"200": {"description": "Success"}}}
                }
            },
        }

        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = (
                AsyncMock(return_value=mock_response)
            )

            results = await runner.run_tests(
                openapi_spec=openapi_spec,
                provider_url="https://api.example.com",
                auth_headers={},
                auth_params={},
                max_examples=10,
            )

        assert results["total_tests"] == 1
        assert results["passed_tests"] == 1
        assert results["failed_tests"] == 0
        assert len(results["test_results"]) == 1
        assert results["test_results"][0]["method"] == "GET"
        assert results["test_results"][0]["path"] == "/test"
        assert results["test_results"][0]["status_code"] == 200
        assert results["test_results"][0]["passed"] is True

    @pytest.mark.asyncio
    async def test_run_tests_with_server_error(self):
        """Test handling server errors."""
        runner = SchemathesisTestRunner(timeout=60)

        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/error": {
                    "get": {
                        "responses": {"500": {"description": "Server Error"}}
                    }
                }
            },
        }

        # Mock httpx client with server error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.elapsed.total_seconds.return_value = 0.5

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = (
                AsyncMock(return_value=mock_response)
            )

            results = await runner.run_tests(
                openapi_spec=openapi_spec,
                provider_url="https://api.example.com",
                auth_headers={},
                auth_params={},
                max_examples=10,
            )

        assert results["total_tests"] == 1
        assert results["passed_tests"] == 0
        assert results["failed_tests"] == 1
        assert results["test_results"][0]["passed"] is False
        assert "Server error: 500" in results["test_results"][0]["issues"]

    @pytest.mark.asyncio
    async def test_run_tests_with_exception(self):
        """Test handling exceptions during test execution."""
        runner = SchemathesisTestRunner(timeout=60)

        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {"responses": {"200": {"description": "Success"}}}
                }
            },
        }

        # Mock httpx client to raise exception
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = (
                AsyncMock(side_effect=Exception("Connection error"))
            )

            results = await runner.run_tests(
                openapi_spec=openapi_spec,
                provider_url="https://api.example.com",
                auth_headers={},
                auth_params={},
                max_examples=10,
            )

        assert results["total_tests"] == 1
        assert results["passed_tests"] == 0
        assert results["failed_tests"] == 1
        assert "Connection error" in results["errors"]

    def test_analyze_response_simple_success(self):
        """Test response analysis for successful response."""
        runner = SchemathesisTestRunner()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5

        result = runner._analyze_response_simple("GET", "/test", mock_response)

        assert result["method"] == "GET"
        assert result["path"] == "/test"
        assert result["status_code"] == 200
        assert result["passed"] is True
        assert len(result["issues"]) == 0

    def test_analyze_response_simple_server_error(self):
        """Test response analysis for server error."""
        runner = SchemathesisTestRunner()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.elapsed.total_seconds.return_value = 0.5

        result = runner._analyze_response_simple("GET", "/test", mock_response)

        assert result["passed"] is False
        assert "Server error: 500" in result["issues"]

    def test_analyze_response_simple_slow_response(self):
        """Test response analysis for slow response."""
        runner = SchemathesisTestRunner()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 35.0

        result = runner._analyze_response_simple("GET", "/test", mock_response)

        assert result["passed"] is True  # Still passes but has issues
        assert "Slow response: 35.0s" in result["issues"]


class TestSchemathesisIntegrationService:
    """Test Schemathesis integration service functionality."""

    @pytest.mark.asyncio
    async def test_create_validation_run(
        self, db_session, sample_api_spec, sample_user
    ):
        """Test creating a validation run."""
        validation_run = (
            await SchemathesisIntegrationService.create_validation_run(
                db=db_session,
                api_specification_id=sample_api_spec.id,
                provider_url="https://api.example.com",
                user_id=sample_user.id,
                auth_method=AuthMethod.API_KEY,
                auth_config={"api_key": "test-key"},
                test_strategies=["path_parameters"],
                max_examples=50,
                timeout=600,
            )
        )

        assert validation_run.id is not None
        assert validation_run.api_specification_id == sample_api_spec.id
        assert validation_run.provider_url == "https://api.example.com"
        assert validation_run.user_id == sample_user.id
        assert validation_run.auth_method == AuthMethod.API_KEY.value
        assert validation_run.auth_config == {"api_key": "test-key"}
        assert validation_run.test_strategies == ["path_parameters"]
        assert validation_run.max_examples == 50
        assert validation_run.timeout == 600
        assert validation_run.status == ValidationRunStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_execute_validation_run_success(
        self, db_session, sample_validation_run
    ):
        """Test successful execution of a validation run."""
        # Mock the test runner
        mock_results = {
            "total_tests": 2,
            "passed_tests": 2,
            "failed_tests": 0,
            "errors": [],
            "test_results": [
                {
                    "method": "GET",
                    "path": "/users",
                    "status_code": 200,
                    "passed": True,
                    "issues": [],
                }
            ],
            "summary": {"success_rate": 100.0},
            "execution_time": 1.5,
        }

        with patch(
            "app.services.schemathesis_integration.SchemathesisTestRunner.run_tests"
        ) as mock_run_tests:
            mock_run_tests.return_value = mock_results

            result = (
                await SchemathesisIntegrationService.execute_validation_run(
                    db_session, sample_validation_run.id
                )
            )

        assert result.status == ValidationRunStatus.COMPLETED.value
        assert result.schemathesis_results == mock_results

    @pytest.mark.asyncio
    async def test_execute_validation_run_not_found(self, db_session):
        """Test execution of non-existent validation run."""
        with pytest.raises(ValueError, match="Validation run 999 not found"):
            await SchemathesisIntegrationService.execute_validation_run(
                db_session, 999
            )

    @pytest.mark.asyncio
    async def test_execute_validation_run_failure(
        self, db_session, sample_validation_run
    ):
        """Test handling of validation run execution failure."""
        with patch(
            "app.services.schemathesis_integration.SchemathesisTestRunner.run_tests"
        ) as mock_run_tests:
            mock_run_tests.side_effect = Exception("Test execution failed")

            result = (
                await SchemathesisIntegrationService.execute_validation_run(
                    db_session, sample_validation_run.id
                )
            )

        assert result.status == ValidationRunStatus.FAILED.value
        assert "Test execution failed" in result.schemathesis_results["error"]

    @pytest.mark.asyncio
    async def test_get_validation_runs(
        self, db_session, sample_api_spec, sample_user
    ):
        """Test getting validation runs with filtering."""
        # Create multiple validation runs
        validation_run1 = ValidationRun(
            api_specification_id=sample_api_spec.id,
            provider_url="https://api1.example.com",
            user_id=sample_user.id,
            status=ValidationRunStatus.COMPLETED.value,
        )
        validation_run2 = ValidationRun(
            api_specification_id=sample_api_spec.id,
            provider_url="https://api2.example.com",
            user_id=sample_user.id,
            status=ValidationRunStatus.PENDING.value,
        )

        db_session.add_all([validation_run1, validation_run2])
        db_session.commit()

        # Test getting all runs
        runs, total = await SchemathesisIntegrationService.get_validation_runs(
            db_session, sample_user.id
        )
        assert total == 2
        assert len(runs) == 2

        # Test filtering by status
        runs, total = await SchemathesisIntegrationService.get_validation_runs(
            db_session, sample_user.id, status=ValidationRunStatus.COMPLETED
        )
        assert total == 1
        assert runs[0].status == ValidationRunStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_get_validation_run(
        self, db_session, sample_validation_run, sample_user
    ):
        """Test getting a specific validation run."""
        result = await SchemathesisIntegrationService.get_validation_run(
            db_session, sample_validation_run.id, sample_user.id
        )

        assert result is not None
        assert result.id == sample_validation_run.id

    @pytest.mark.asyncio
    async def test_get_validation_run_not_found(self, db_session, sample_user):
        """Test getting non-existent validation run."""
        result = await SchemathesisIntegrationService.get_validation_run(
            db_session, 999, sample_user.id
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_validation_run(
        self, db_session, sample_validation_run, sample_user
    ):
        """Test cancelling a validation run."""
        # Set status to running
        sample_validation_run.status = ValidationRunStatus.RUNNING.value
        db_session.commit()

        result = await SchemathesisIntegrationService.cancel_validation_run(
            db_session, sample_validation_run.id, sample_user.id
        )

        assert result is not None
        assert result.status == ValidationRunStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_cancel_validation_run_not_cancellable(
        self, db_session, sample_validation_run, sample_user
    ):
        """Test cancelling a validation run that cannot be cancelled."""
        # Set status to completed
        sample_validation_run.status = ValidationRunStatus.COMPLETED.value
        db_session.commit()

        result = await SchemathesisIntegrationService.cancel_validation_run(
            db_session, sample_validation_run.id, sample_user.id
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_provider_connectivity_success(self):
        """Test successful provider connectivity validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await SchemathesisIntegrationService.validate_provider_connectivity(
                "https://api.example.com"
            )

        assert result["reachable"] is True
        assert result["status_code"] == 200
        assert result["response_time"] == 0.5

    @pytest.mark.asyncio
    async def test_validate_provider_connectivity_failure(self):
        """Test failed provider connectivity validation."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            result = await SchemathesisIntegrationService.validate_provider_connectivity(
                "https://api.example.com"
            )

        assert result["reachable"] is False
        assert "Connection failed" in result["error"]
