"""
Validation endpoints for API validation using Schemathesis.
This module implements the endpoints specified in Task 12.
"""

import logging
import math
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
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
from app.services.environments import EnvironmentService
from app.services.schemathesis_integration import SchemathesisIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/validations", tags=["Validations"])


def get_filters(
    api_specification_id: Optional[int] = Query(None, description="Filter by API specification ID"),
    status: Optional[ValidationRunStatus] = Query(None, description="Filter by status"),
    environment_id: Optional[int] = Query(None, description="Filter by environment ID"),
    provider_url: Optional[str] = Query(None, description="Filter by provider URL (partial match)"),
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
            environment_id=environment_id,
            provider_url=provider_url,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size,
        )
    except ValidationError as e:
        # Convert Pydantic validation error to FastAPI validation error
        raise RequestValidationError(errors=e.errors())


async def execute_validation_in_background(db: Session, validation_run_id: int):
    """Background task to execute validation run."""
    try:
        await SchemathesisIntegrationService.execute_validation_run(db, validation_run_id)
    except Exception as e:
        logger.error(f"Background validation execution failed: {e}")


@router.post(
    "",
    response_model=ValidationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Validation",
    description=(
        "Trigger validation of provider against specification. "
        "Creates a new validation run and executes it in the background. "
        "You can either select a predefined environment or provide a custom provider URL."
    ),
)
async def trigger_validation(
    validation_data: ValidationRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationRunResponse:
    """
    Trigger validation of provider against specification.

    - **api_specification_id**: ID of the API specification to validate against
    - **environment_id**: ID of predefined environment (optional, mutually exclusive with
      provider_url)
    - **provider_url**: Custom provider URL (optional, mutually exclusive with environment_id)
    - **auth_method**: Authentication method to use
    - **auth_config**: Authentication configuration
    - **test_strategies**: Specific test strategies to use
    - **max_examples**: Maximum number of test examples to generate
    - **timeout**: Timeout for the validation run in seconds
    """
    try:
        # Determine the provider URL to test connectivity
        test_url = validation_data.provider_url
        if validation_data.environment_id:
            # Get environment to resolve URL
            environment = EnvironmentService.get_environment(
                db, validation_data.environment_id, current_user
            )
            if not environment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Environment with ID {validation_data.environment_id} not found",
                )
            test_url = environment.base_url

        # Test provider connectivity first
        service = SchemathesisIntegrationService
        connectivity_result = await service.validate_provider_connectivity(test_url)

        if not connectivity_result.get("reachable"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Provider URL is not reachable: "
                    f"{connectivity_result.get('error', 'Unknown error')}"
                ),
            )

        # Create the validation run
        validation_run = await SchemathesisIntegrationService.create_validation_run(
            db=db,
            api_specification_id=validation_data.api_specification_id,
            user_id=current_user.id,
            environment_id=validation_data.environment_id,
            provider_url=validation_data.provider_url,
            auth_method=validation_data.auth_method,
            auth_config=validation_data.auth_config,
            test_strategies=validation_data.test_strategies,
            max_examples=validation_data.max_examples,
            timeout=validation_data.timeout,
        )

        # Execute validation in background
        background_tasks.add_task(execute_validation_in_background, db, validation_run.id)

        logger.info(f"Triggered validation run {validation_run.id} for user {current_user.id}")

        return ValidationRunResponse.model_validate(validation_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger validation",
        )


@router.get(
    "/{id}",
    response_model=ValidationRunResponse,
    summary="Get Validation Results",
    description="Get validation results by ID.",
)
async def get_validation_results(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationRunResponse:
    """
    Get validation results by ID.

    Returns the full validation run including test results and status.
    """
    try:
        validation_run = await SchemathesisIntegrationService.get_validation_run(
            db, id, current_user.id
        )

        if not validation_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation with ID {id} not found",
            )

        return ValidationRunResponse.model_validate(validation_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation results",
        )


@router.get(
    "",
    response_model=ValidationRunListResponse,
    summary="List Validation Runs",
    description=("List validation runs with optional filtering and sorting."),
)
async def list_validations(
    filters: ValidationRunFilters = Depends(get_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationRunListResponse:
    """
    Get a paginated list of validation runs.

    Supports filtering by:
    - **api_specification_id**: Filter by API specification ID
    - **status**: Filter by validation run status
    - **environment_id**: Filter by environment ID
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
            items=[ValidationRunResponse.model_validate(run) for run in validation_runs],
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listing validations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation runs",
        )
