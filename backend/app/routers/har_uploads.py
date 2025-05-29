import logging
import math
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import HARUploadFilters, HARUploadListResponse, HARUploadResponse
from app.services.har_uploads import HARUploadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/har-uploads", tags=["HAR Uploads"])

# File size limit: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

# Allowed file extensions
ALLOWED_EXTENSIONS = {".har", ".json"}


def get_filters(
    file_name: Optional[str] = Query(None, description="Filter by file name (partial match)"),
    sort_by: str = Query(
        "uploaded_at",
        description="Sort field (file_name, uploaded_at)",
    ),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
) -> HARUploadFilters:
    """Dependency to validate and create filters object."""
    try:
        return HARUploadFilters(
            file_name=file_name,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size,
        )
    except ValidationError as e:
        # Convert Pydantic validation error to FastAPI validation error
        raise RequestValidationError(errors=e.errors())


def validate_file(file: UploadFile) -> None:
    """
    Validate uploaded file.

    Args:
        file: Uploaded file

    Raises:
        HTTPException: If file validation fails
    """
    # Check file extension
    if file.filename:
        file_ext = "." + file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
            )

    # Check content type
    if file.content_type and not file.content_type.startswith(("application/json", "text/")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type. Expected JSON or text file.",
        )


@router.post(
    "",
    response_model=HARUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload HAR File",
    description="Upload and store a HTTP Archive (HAR) file.",
)
async def upload_har_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="HAR file to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HARUploadResponse:
    """
    Upload a HAR file.

    - **file**: HAR file to upload (max 50MB)
    - Validates HAR file format
    - Stores file content in database
    - Returns upload details
    """
    try:
        # Validate file
        validate_file(file)

        # Read file content
        content = await file.read()

        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        # Convert bytes to string
        try:
            content_str = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be UTF-8 encoded",
            )

        # Create HAR upload record
        har_upload = HARUploadService.create_har_upload(
            db, file.filename or "unknown.har", content_str, current_user
        )

        # TODO: Add background task for processing HAR file
        # background_tasks.add_task(process_har_file, har_upload.id)

        return HARUploadResponse.model_validate(har_upload)

    except HTTPException:
        raise
    except ValueError as e:
        # Handle HAR validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error uploading HAR file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload HAR file",
        )


@router.get(
    "",
    response_model=HARUploadListResponse,
    summary="List HAR Uploads",
    description="Get a paginated list of HAR uploads with optional filtering and sorting.",
)
def list_har_uploads(
    filters: HARUploadFilters = Depends(get_filters),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HARUploadListResponse:
    """
    Get a paginated list of HAR uploads.

    Supports filtering by:
    - **file_name**: Partial file name match (case-insensitive)

    Supports sorting by:
    - **file_name**, **uploaded_at**
    - Order: **asc** or **desc**
    """
    try:
        uploads, total = HARUploadService.get_har_uploads(db, current_user, filters)

        pages = math.ceil(total / filters.size) if total > 0 else 1

        return HARUploadListResponse(
            items=[HARUploadResponse.model_validate(upload) for upload in uploads],
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listing HAR uploads: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve HAR uploads",
        )


@router.get(
    "/{upload_id}",
    response_model=HARUploadResponse,
    summary="Get HAR Upload",
    description="Get a specific HAR upload by ID.",
)
def get_har_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HARUploadResponse:
    """
    Get a specific HAR upload by ID.

    Returns the upload details without the raw content.
    Use the download endpoint to get the raw HAR content.
    """
    try:
        upload = HARUploadService.get_har_upload(db, upload_id, current_user)

        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"HAR upload with ID {upload_id} not found",
            )

        return HARUploadResponse.model_validate(upload)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting HAR upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve HAR upload",
        )


@router.delete(
    "/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete HAR Upload",
    description="Delete a HAR upload.",
)
def delete_har_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a HAR upload.

    This will permanently remove the upload and its content.
    """
    try:
        deleted = HARUploadService.delete_har_upload(db, upload_id, current_user)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"HAR upload with ID {upload_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting HAR upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete HAR upload",
        )
