import logging
import math

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
    APISpecificationCreate,
    APISpecificationFilters,
    APISpecificationListResponse,
    APISpecificationResponse,
    APISpecificationUpdate,
)
from app.services.api_specifications import APISpecificationService
from app.services.n8n_notifications import n8n_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/specifications", tags=["API Specifications"])


def get_filters(
    name: str = Query(None, description="Filter by name (partial match)"),
    version_string: str = Query(
        None, description="Filter by version string (exact match)"
    ),
    sort_by: str = Query(
        "created_at",
        description=(
            "Sort field (name, version_string, created_at, updated_at)"
        ),
    ),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
) -> APISpecificationFilters:
    """Dependency to validate and create filters object."""
    try:
        return APISpecificationFilters(
            name=name,
            version_string=version_string,
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
    response_model=APISpecificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API Specification",
    description="Create a new API specification for the authenticated user.",
)
def create_specification(
    spec_data: APISpecificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APISpecificationResponse:
    """
    Create a new API specification.

    - **name**: Name of the API specification
    - **version_string**: Version string (e.g., 'v1.0', '2.1.0')
    - **openapi_content**: OpenAPI specification content as JSON
    """
    try:
        # Check if specification with same name and version already exists
        if APISpecificationService.check_name_version_exists(
            db, spec_data.name, spec_data.version_string, current_user
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"API specification '{spec_data.name}' version "
                    f"'{spec_data.version_string}' already exists"
                ),
            )

        specification = APISpecificationService.create_specification(
            db, spec_data, current_user
        )

        # Send n8n notification in background
        background_tasks.add_task(
            n8n_service.send_specification_created, specification
        )

        return APISpecificationResponse.model_validate(specification)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating API specification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API specification",
        )


@router.get(
    "",
    response_model=APISpecificationListResponse,
    summary="List API Specifications",
    description=(
        "Get a paginated list of API specifications with optional "
        "filtering and sorting."
    ),
)
def list_specifications(
    filters: APISpecificationFilters = Depends(get_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APISpecificationListResponse:
    """
    Get a paginated list of API specifications.

    Supports filtering by:
    - **name**: Partial name match (case-insensitive)
    - **version_string**: Exact version match

    Supports sorting by:
    - **name**, **version_string**, **created_at**, **updated_at**
    - Order: **asc** or **desc**
    """
    try:
        specifications, total = APISpecificationService.get_specifications(
            db, current_user, filters
        )

        pages = math.ceil(total / filters.size) if total > 0 else 1

        return APISpecificationListResponse(
            items=[
                APISpecificationResponse.model_validate(spec)
                for spec in specifications
            ],
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listing API specifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API specifications",
        )


@router.get(
    "/{spec_id}",
    response_model=APISpecificationResponse,
    summary="Get API Specification",
    description="Get a specific API specification by ID.",
)
def get_specification(
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APISpecificationResponse:
    """
    Get a specific API specification by ID.

    Returns the full specification including OpenAPI content.
    """
    try:
        specification = APISpecificationService.get_specification(
            db, spec_id, current_user
        )

        if not specification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API specification with ID {spec_id} not found",
            )

        return APISpecificationResponse.model_validate(specification)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving API specification {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API specification",
        )


@router.put(
    "/{spec_id}",
    response_model=APISpecificationResponse,
    summary="Update API Specification",
    description="Update an existing API specification.",
)
def update_specification(
    spec_id: int,
    spec_data: APISpecificationUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APISpecificationResponse:
    """
    Update an existing API specification.

    Only provided fields will be updated. All fields are optional.
    """
    try:
        # Check if specification exists
        existing_spec = APISpecificationService.get_specification(
            db, spec_id, current_user
        )

        if not existing_spec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API specification with ID {spec_id} not found",
            )

        # Check for name/version conflicts if updating name or version
        update_data = spec_data.model_dump(exclude_unset=True)
        if "name" in update_data or "version_string" in update_data:
            new_name = update_data.get("name", existing_spec.name)
            new_version = update_data.get(
                "version_string", existing_spec.version_string
            )

            if APISpecificationService.check_name_version_exists(
                db, new_name, new_version, current_user, exclude_id=spec_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"API specification '{new_name}' version "
                        f"'{new_version}' already exists"
                    ),
                )

        specification = APISpecificationService.update_specification(
            db, spec_id, spec_data, current_user
        )

        # Send n8n notification in background
        background_tasks.add_task(
            n8n_service.send_specification_updated, specification
        )

        return APISpecificationResponse.model_validate(specification)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API specification {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API specification",
        )


@router.delete(
    "/{spec_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete API Specification",
    description="Delete an API specification.",
)
def delete_specification(
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an API specification.

    This action cannot be undone.
    """
    try:
        success = APISpecificationService.delete_specification(
            db, spec_id, current_user
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API specification with ID {spec_id} not found",
            )

        # Return 204 No Content on successful deletion
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API specification {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API specification",
        )
