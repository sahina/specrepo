import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    EnvironmentCreate,
    EnvironmentFilters,
    EnvironmentListResponse,
    EnvironmentResponse,
    EnvironmentType,
    EnvironmentUpdate,
)
from app.services.environments import EnvironmentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/environments", tags=["Environments"])


def get_filters(
    name: str = Query(None, description="Filter by name (partial match)"),
    environment_type: EnvironmentType = Query(None, description="Filter by environment type"),
    is_active: str = Query("true", description="Filter by active status"),
    sort_by: str = Query(
        "created_at",
        description="Sort field (name, environment_type, created_at, updated_at)",
    ),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
) -> EnvironmentFilters:
    """Dependency to validate and create filters object."""
    try:
        return EnvironmentFilters(
            name=name,
            environment_type=environment_type,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size,
        )
    except ValidationError as e:
        # Convert Pydantic validation error to FastAPI validation error
        raise RequestValidationError(errors=e.errors())


@router.post(
    "",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Environment",
    description="Create a new environment for the authenticated user.",
)
def create_environment(
    env_data: EnvironmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvironmentResponse:
    """
    Create a new environment.

    - **name**: Name of the environment
    - **base_url**: Base URL of the environment
    - **description**: Optional description
    - **environment_type**: Type of environment (production, staging, development, custom)
    """
    try:
        # Check if environment name already exists
        if EnvironmentService.check_name_exists(db, env_data.name, current_user):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Environment '{env_data.name}' already exists",
            )

        environment = EnvironmentService.create_environment(db, env_data, current_user)

        return EnvironmentResponse.model_validate(environment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating environment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create environment",
        )


@router.get(
    "",
    response_model=EnvironmentListResponse,
    summary="List Environments",
    description="Get a paginated list of environments with optional filtering and sorting.",
)
def list_environments(
    filters: EnvironmentFilters = Depends(get_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvironmentListResponse:
    """
    Get a paginated list of environments.

    Supports filtering by:
    - **name**: Partial name match (case-insensitive)
    - **environment_type**: Environment type
    - **is_active**: Active status

    Supports sorting by:
    - **name**, **environment_type**, **created_at**, **updated_at**
    - Order: **asc** or **desc**
    """
    try:
        environments, total = EnvironmentService.get_environments(db, current_user, filters)

        pages = math.ceil(total / filters.size) if total > 0 else 1

        return EnvironmentListResponse(
            items=[EnvironmentResponse.model_validate(env) for env in environments],
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listing environments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve environments",
        )


@router.get(
    "/{env_id}",
    response_model=EnvironmentResponse,
    summary="Get Environment",
    description="Get a specific environment by ID.",
)
def get_environment(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvironmentResponse:
    """
    Get a specific environment by ID.

    Returns the full environment details.
    """
    try:
        environment = EnvironmentService.get_environment(db, env_id, current_user)

        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment with ID {env_id} not found",
            )

        return EnvironmentResponse.model_validate(environment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving environment {env_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve environment",
        )


@router.put(
    "/{env_id}",
    response_model=EnvironmentResponse,
    summary="Update Environment",
    description="Update an existing environment.",
)
def update_environment(
    env_id: int,
    env_data: EnvironmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvironmentResponse:
    """
    Update an existing environment.

    Only provided fields will be updated. All fields are optional.
    """
    try:
        # Check if environment exists
        existing_env = EnvironmentService.get_environment(db, env_id, current_user)

        if not existing_env:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment with ID {env_id} not found",
            )

        # Check for name conflicts if updating name
        update_data = env_data.model_dump(exclude_unset=True)
        if "name" in update_data:
            new_name = update_data["name"]
            if EnvironmentService.check_name_exists(db, new_name, current_user, exclude_id=env_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Environment '{new_name}' already exists",
                )

        environment = EnvironmentService.update_environment(db, env_id, env_data, current_user)

        return EnvironmentResponse.model_validate(environment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating environment {env_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update environment",
        )


@router.delete(
    "/{env_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Environment",
    description="Delete an environment (soft delete).",
)
def delete_environment(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an environment (soft delete).

    This action sets the environment as inactive but preserves the data.
    """
    try:
        success = EnvironmentService.delete_environment(db, env_id, current_user)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Environment with ID {env_id} not found",
            )

        # Return 204 No Content on successful deletion
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting environment {env_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete environment",
        )
