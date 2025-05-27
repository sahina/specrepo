"""
Validation runs router for API validation using Schemathesis.
"""

import logging
import math
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    ValidationRunCreate,
    ValidationRunFilters,
    ValidationRunListResponse,
    ValidationRunResponse,
    ValidationRunStatus,
)
from app.services.schemathesis_integration import (
    SchemathesisIntegrationService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validation-runs", tags=["Validation Runs"])


def get_filters(
    api_specification_id: Optional[int] = Query(
        None, description="Filter by API specification ID"
    ),
    status: Optional[ValidationRunStatus] = Query(
        None, description="Filter by status"
    ),
    provider_url: Optional[str] = Query(
        None, description="Filter by provider URL (partial match)"
    ),
    sort_by: str = Query(
        "triggered_at",
        description="Sort field (triggered_at, status, provider_url)",
    ),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
) -> ValidationRunFilters:
    """Dependency to validate and create filters object."""
    try:
        return ValidationRunFilters(
            api_specification_id=api_specification_id,
            status=status,
            provider_url=provider_url,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size,
        )
    except ValidationError as e:
        # Convert Pydantic validation error to FastAPI validation error
        raise RequestValidationError(errors=e.errors())


async def execute_validation_in_background(
    db: Session, validation_run_id: int
):
    """Background task to execute validation run."""
    try:
        await SchemathesisIntegrationService.execute_validation_run(
            db, validation_run_id
        )
    except Exception as e:
        logger.error(f"Background validation execution failed: {e}")


@router.post(
    "",
    response_model=ValidationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Validation Run",
    description=(
        "Create a new validation run to test a provider against an API "
        "specification."
    ),
)
async def create_validation_run(
    validation_data: ValidationRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationRunResponse:
    """
    Create a new validation run.

    - **api_specification_id**: ID of the API specification to validate against
    - **provider_url**: URL of the provider to validate
    - **auth_method**: Authentication method to use
    - **auth_config**: Authentication configuration
    - **test_strategies**: Specific test strategies to use
    - **max_examples**: Maximum number of test examples to generate
    - **timeout**: Timeout for the validation run in seconds
    """
    try:
        # Test provider connectivity first
        service = SchemathesisIntegrationService
        connectivity_result = await service.validate_provider_connectivity(
            validation_data.provider_url
        )

        if not connectivity_result.get("reachable"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Provider URL is not reachable: "
                    f"{connectivity_result.get('error', 'Unknown error')}"
                ),
            )

        # Create the validation run
        validation_run = (
            await SchemathesisIntegrationService.create_validation_run(
                db=db,
                api_specification_id=validation_data.api_specification_id,
                provider_url=validation_data.provider_url,
                user_id=current_user.id,
                auth_method=validation_data.auth_method,
                auth_config=validation_data.auth_config,
                test_strategies=validation_data.test_strategies,
                max_examples=validation_data.max_examples,
                timeout=validation_data.timeout,
            )
        )

        # Execute validation in background
        background_tasks.add_task(
            execute_validation_in_background, db, validation_run.id
        )

        return ValidationRunResponse.model_validate(validation_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating validation run: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create validation run",
        )


@router.get(
    "",
    response_model=ValidationRunListResponse,
    summary="List Validation Runs",
    description=(
        "Get a paginated list of validation runs with optional filtering "
        "and sorting."
    ),
)
async def list_validation_runs(
    filters: ValidationRunFilters = Depends(get_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationRunListResponse:
    """
    Get a paginated list of validation runs.

    Supports filtering by:
    - **api_specification_id**: Filter by API specification ID
    - **status**: Filter by validation run status
    - **provider_url**: Partial provider URL match

    Supports sorting by:
    - **triggered_at**, **status**, **provider_url**
    - Order: **asc** or **desc**
    """
    try:
        skip = (filters.page - 1) * filters.size
        (
            validation_runs,
            total,
        ) = await SchemathesisIntegrationService.get_validation_runs(
            db=db,
            user_id=current_user.id,
            api_specification_id=filters.api_specification_id,
            status=filters.status,
            skip=skip,
            limit=filters.size,
        )

        pages = math.ceil(total / filters.size) if total > 0 else 1

        return ValidationRunListResponse(
            items=[
                ValidationRunResponse.model_validate(run)
                for run in validation_runs
            ],
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listing validation runs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation runs",
        )


@router.get(
    "/{validation_run_id}",
    response_model=ValidationRunResponse,
    summary="Get Validation Run",
    description="Get a specific validation run by ID.",
)
async def get_validation_run(
    validation_run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationRunResponse:
    """
    Get a specific validation run by ID.

    Returns the full validation run including test results.
    """
    try:
        validation_run = (
            await SchemathesisIntegrationService.get_validation_run(
                db, validation_run_id, current_user.id
            )
        )

        if not validation_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation run with ID {validation_run_id} not found",
            )

        return ValidationRunResponse.model_validate(validation_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation run: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation run",
        )


@router.post(
    "/{validation_run_id}/cancel",
    response_model=ValidationRunResponse,
    summary="Cancel Validation Run",
    description="Cancel a running or pending validation run.",
)
async def cancel_validation_run(
    validation_run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationRunResponse:
    """
    Cancel a running or pending validation run.

    Only validation runs with status 'pending' or 'running' can be cancelled.
    """
    try:
        validation_run = (
            await SchemathesisIntegrationService.cancel_validation_run(
                db, validation_run_id, current_user.id
            )
        )

        if not validation_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Validation run with ID {validation_run_id} not found or "
                    "cannot be cancelled"
                ),
            )

        return ValidationRunResponse.model_validate(validation_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling validation run: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel validation run",
        )


@router.post(
    "/test-connectivity",
    summary="Test Provider Connectivity",
    description="Test basic connectivity to a provider URL.",
)
async def test_provider_connectivity(
    provider_url: str = Query(..., description="Provider URL to test"),
) -> dict:
    """
    Test basic connectivity to a provider URL.

    Returns connectivity status and basic response information.
    """
    try:
        service = SchemathesisIntegrationService
        result = await service.validate_provider_connectivity(provider_url)
        return result

    except Exception as e:
        logger.error(f"Error testing provider connectivity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test provider connectivity",
        )
