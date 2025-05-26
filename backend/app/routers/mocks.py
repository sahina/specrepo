import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.api_specifications import APISpecificationService
from app.services.mock_configuration import MockConfigurationService
from app.services.wiremock_integration import WireMockIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mocks", tags=["Mock Management"])


class MockDeployRequest(BaseModel):
    """Request model for deploying API specification to WireMock."""

    specification_id: int
    clear_existing: bool = False


class MockDeployResponse(BaseModel):
    """Response model for mock deployment."""

    message: str
    configuration_id: int
    stubs_created: int
    status: str


class MockStatusResponse(BaseModel):
    """Response model for mock deployment status."""

    total_configurations: int
    active_configurations: int
    configurations: List[dict]


class MockResetResponse(BaseModel):
    """Response model for mock reset operation."""

    message: str
    configurations_reset: int
    wiremock_reset: bool


@router.post(
    "/deploy",
    response_model=MockDeployResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Deploy API Specification to WireMock",
    description="Deploy an API specification to WireMock and store deployment status in database.",
)
async def deploy_mock(
    request: MockDeployRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MockDeployResponse:
    """
    Deploy API specification to WireMock.

    - **specification_id**: ID of the API specification to deploy
    - **clear_existing**: Whether to clear existing WireMock stubs before deployment
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

        # Generate and deploy stubs to WireMock
        try:
            created_stubs = await wiremock_service.generate_stubs_from_openapi(
                specification.openapi_content,
                clear_existing=request.clear_existing,
            )
        except Exception as e:
            logger.error(f"Failed to deploy to WireMock: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"WireMock deployment failed: {str(e)}",
            )

        # Store deployment status in database
        try:
            mock_config = MockConfigurationService.create_mock_configuration(
                db=db,
                api_specification_id=request.specification_id,
                wiremock_mapping_json={
                    "stubs": created_stubs,
                    "specification_name": specification.name,
                    "specification_version": specification.version_string,
                    "deployment_metadata": {
                        "clear_existing": request.clear_existing,
                        "stubs_count": len(created_stubs),
                    },
                },
                status="active",
                user=current_user,
            )
        except Exception as e:
            logger.error(f"Failed to store deployment status: {str(e)}")
            # Try to clean up WireMock deployment if database storage fails
            try:
                await wiremock_service.clear_all_stubs()
            except Exception:
                pass  # Best effort cleanup
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store deployment status: {str(e)}",
            )

        logger.info(
            f"Successfully deployed API specification {specification.name} "
            f"v{specification.version_string} to WireMock with {len(created_stubs)} stubs"
        )

        return MockDeployResponse(
            message=f"Successfully deployed {specification.name} v{specification.version_string} to WireMock",
            configuration_id=mock_config.id,
            stubs_created=len(created_stubs),
            status="active",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during mock deployment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}",
        )


@router.delete(
    "/reset",
    response_model=MockResetResponse,
    summary="Reset All WireMock Configurations",
    description="Reset all WireMock configurations and update database status.",
)
async def reset_mocks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MockResetResponse:
    """
    Reset all WireMock configurations.

    This will:
    1. Clear all stubs from WireMock server
    2. Reset WireMock to initial state
    3. Mark all mock configurations as inactive in database
    """
    try:
        # Initialize WireMock service
        wiremock_service = WireMockIntegrationService()

        # Reset WireMock server
        wiremock_reset_success = False
        try:
            await wiremock_service.reset_wiremock()
            wiremock_reset_success = True
        except Exception as e:
            logger.error(f"Failed to reset WireMock: {str(e)}")
            # Continue with database reset even if WireMock reset fails
            pass

        # Reset all mock configurations in database
        try:
            configurations_reset = (
                MockConfigurationService.reset_all_mock_configurations(
                    db=db, user=current_user
                )
            )
        except Exception as e:
            logger.error(
                f"Failed to reset mock configurations in database: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reset database configurations: {str(e)}",
            )

        # If WireMock reset failed but database reset succeeded, raise an error
        if not wiremock_reset_success:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Database configurations reset successfully, but WireMock reset failed",
            )

        logger.info(
            f"Successfully reset {configurations_reset} mock configurations and WireMock"
        )

        return MockResetResponse(
            message=f"Successfully reset all mock configurations",
            configurations_reset=configurations_reset,
            wiremock_reset=wiremock_reset_success,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during mock reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset failed: {str(e)}",
        )


@router.get(
    "/status",
    response_model=MockStatusResponse,
    summary="Get WireMock Deployment Status",
    description="Get current WireMock deployment status from database.",
)
async def get_mock_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MockStatusResponse:
    """
    Get current WireMock deployment status.

    Returns information about all mock configurations stored in the database,
    including their deployment status and metadata.
    """
    try:
        # Get all mock configurations
        all_configurations = (
            MockConfigurationService.get_active_mock_configurations(
                db=db, user=current_user
            )
        )

        # Get active configurations
        active_configurations = [
            config
            for config in all_configurations
            if config.status == "active"
        ]

        # Build response data
        configurations_data = []
        for config in all_configurations:
            config_data = {
                "id": config.id,
                "api_specification_id": config.api_specification_id,
                "status": config.status,
                "deployed_at": config.deployed_at.isoformat()
                if config.deployed_at
                else None,
                "stubs_count": len(
                    config.wiremock_mapping_json.get("stubs", [])
                ),
                "specification_name": config.wiremock_mapping_json.get(
                    "specification_name"
                ),
                "specification_version": config.wiremock_mapping_json.get(
                    "specification_version"
                ),
            }
            configurations_data.append(config_data)

        logger.info(
            f"Retrieved status for {len(all_configurations)} mock configurations "
            f"({len(active_configurations)} active)"
        )

        return MockStatusResponse(
            total_configurations=len(all_configurations),
            active_configurations=len(active_configurations),
            configurations=configurations_data,
        )

    except Exception as e:
        logger.error(f"Error getting mock status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get mock status: {str(e)}",
        )
