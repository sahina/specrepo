import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.api_specifications import APISpecificationService
from app.services.wiremock_integration import WireMockIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wiremock", tags=["WireMock Integration"])


class WireMockStubResponse(BaseModel):
    """Response model for WireMock stub operations."""

    id: str
    request: dict
    response: dict
    metadata: Optional[dict] = None


class WireMockGenerateRequest(BaseModel):
    """Request model for generating stubs from API specification."""

    specification_id: int
    clear_existing: bool = False


class WireMockGenerateResponse(BaseModel):
    """Response model for stub generation."""

    message: str
    stubs_created: int
    stubs: List[WireMockStubResponse]


class WireMockStatusResponse(BaseModel):
    """Response model for WireMock status."""

    total_stubs: int
    stubs: List[WireMockStubResponse]


@router.post(
    "/generate",
    response_model=WireMockGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate WireMock Stubs",
    description="Generate WireMock stubs from an API specification.",
)
async def generate_stubs(
    request: WireMockGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WireMockGenerateResponse:
    """
    Generate WireMock stubs from an API specification.

    - **specification_id**: ID of the API specification to use
    - **clear_existing**: Whether to clear existing stubs before generating
      new ones
    """
    try:
        # Get the API specification
        specification = APISpecificationService.get_specification(
            db, request.specification_id, current_user
        )

        if not specification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API specification with ID {request.specification_id} not found",
            )

        # Initialize WireMock service
        wiremock_service = WireMockIntegrationService()

        # Generate stubs from OpenAPI content
        created_stubs = await wiremock_service.generate_stubs_from_openapi(
            specification.openapi_content,
            clear_existing=request.clear_existing,
            specification_id=specification.id,
            specification_name=specification.name,
        )

        # Convert to response format
        stub_responses = [
            WireMockStubResponse(
                id=stub.get("id", ""),
                request=stub.get("request", {}),
                response=stub.get("response", {}),
                metadata=stub.get("metadata"),
            )
            for stub in created_stubs
        ]

        logger.info(
            f"Generated {len(created_stubs)} WireMock stubs for specification "
            f"{specification.name} v{specification.version_string}"
        )

        return WireMockGenerateResponse(
            message=f"Successfully generated {len(created_stubs)} WireMock stubs",
            stubs_created=len(created_stubs),
            stubs=stub_responses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating WireMock stubs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate WireMock stubs: {str(e)}",
        )


@router.get(
    "/stubs",
    response_model=WireMockStatusResponse,
    summary="Get WireMock Stubs",
    description="Get all current WireMock stubs, optionally filtered by specification ID.",
)
async def get_stubs(
    specification_id: Optional[int] = Query(
        None, description="Filter stubs by API specification ID"
    ),
    current_user: User = Depends(get_current_user),
) -> WireMockStatusResponse:
    """
    Get all current WireMock stubs.

    Returns a list of all stubs currently configured in WireMock.
    If specification_id is provided, only returns stubs for that specification.
    """
    try:
        # Initialize WireMock service
        wiremock_service = WireMockIntegrationService()

        # Get all stubs
        stubs = await wiremock_service.get_all_stubs()

        # Filter by specification_id if provided
        if specification_id is not None:
            filtered_stubs = []
            for stub in stubs:
                metadata = stub.get("metadata", {})
                if metadata.get("specificationId") == specification_id:
                    filtered_stubs.append(stub)
            stubs = filtered_stubs

        # Convert to response format
        stub_responses = [
            WireMockStubResponse(
                id=stub.get("id", ""),
                request=stub.get("request", {}),
                response=stub.get("response", {}),
                metadata=stub.get("metadata"),
            )
            for stub in stubs
        ]

        return WireMockStatusResponse(total_stubs=len(stubs), stubs=stub_responses)

    except Exception as e:
        logger.error(f"Error getting WireMock stubs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get WireMock stubs: {str(e)}",
        )


@router.delete(
    "/stubs",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear WireMock Stubs",
    description="Clear all WireMock stubs.",
)
async def clear_stubs(
    current_user: User = Depends(get_current_user),
):
    """
    Clear all WireMock stubs.

    Removes all stub configurations from WireMock.
    """
    try:
        # Initialize WireMock service
        wiremock_service = WireMockIntegrationService()

        # Clear all stubs
        await wiremock_service.clear_all_stubs()

        logger.info("Cleared all WireMock stubs")

    except Exception as e:
        logger.error(f"Error clearing WireMock stubs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear WireMock stubs: {str(e)}",
        )


@router.post(
    "/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset WireMock",
    description="Reset WireMock to initial state.",
)
async def reset_wiremock(
    current_user: User = Depends(get_current_user),
):
    """
    Reset WireMock to initial state.

    Resets WireMock server to its initial configuration.
    """
    try:
        # Initialize WireMock service
        wiremock_service = WireMockIntegrationService()

        # Reset WireMock
        await wiremock_service.reset_wiremock()

        logger.info("Reset WireMock to initial state")

    except Exception as e:
        logger.error(f"Error resetting WireMock: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset WireMock: {str(e)}",
        )
