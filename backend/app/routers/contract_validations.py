"""
Contract validation router for end-to-end contract validation endpoints.

This module provides FastAPI endpoints for managing contract validations,
including creating, executing, and retrieving validation results.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import (
    ContractHealthStatus,
    ContractHealthSummary,
    ContractValidationCreate,
    ContractValidationFilters,
    ContractValidationListResponse,
    ContractValidationResponse,
    ContractValidationStatus,
)
from app.services.contract_validation import ContractValidationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contract-validations", tags=["contract-validations"])

# Initialize service
contract_validation_service = ContractValidationService()


@router.post("/", response_model=ContractValidationResponse, status_code=status.HTTP_201_CREATED)
async def create_contract_validation(
    validation_data: ContractValidationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractValidationResponse:
    """
    Create and trigger a new contract validation.

    This endpoint creates a contract validation run and immediately starts
    the validation process in the background.
    """
    try:
        # Create contract validation
        contract_validation = await contract_validation_service.create_contract_validation(
            db=db,
            api_specification_id=validation_data.api_specification_id,
            user_id=current_user.id,
            environment_id=validation_data.environment_id,
            provider_url=validation_data.provider_url,
            auth_method=validation_data.auth_method,
            auth_config=validation_data.auth_config,
            test_strategies=validation_data.test_strategies,
            max_examples=validation_data.max_examples or 100,
            timeout=validation_data.timeout or 300,
        )

        # Execute validation in background
        background_tasks.add_task(
            contract_validation_service.execute_contract_validation, db, contract_validation.id
        )

        logger.info(
            f"Created contract validation {contract_validation.id} for user {current_user.id}"
        )

        return ContractValidationResponse.model_validate(contract_validation)

    except ValueError as e:
        logger.error(f"Validation error creating contract validation: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating contract validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create contract validation",
        )


@router.get("/", response_model=ContractValidationListResponse)
async def list_contract_validations(
    api_specification_id: Optional[int] = Query(None, description="Filter by API specification ID"),
    status: Optional[ContractValidationStatus] = Query(
        None, description="Filter by validation status"
    ),
    contract_health_status: Optional[ContractHealthStatus] = Query(
        None, description="Filter by health status"
    ),
    environment_id: Optional[int] = Query(None, description="Filter by environment ID"),
    provider_url: Optional[str] = Query(None, description="Filter by provider URL"),
    sort_by: str = Query("triggered_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractValidationListResponse:
    """
    List contract validations with filtering and pagination.
    """
    try:
        # Create filters object
        filters = ContractValidationFilters(
            api_specification_id=api_specification_id,
            status=status,
            contract_health_status=contract_health_status,
            environment_id=environment_id,
            provider_url=provider_url,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size,
        )

        # Calculate skip
        skip = (page - 1) * size

        # Get validations
        validations, total = await contract_validation_service.get_contract_validations(
            db=db,
            user_id=current_user.id,
            api_specification_id=api_specification_id,
            status=status,
            contract_health_status=contract_health_status,
            skip=skip,
            limit=size,
        )

        # Calculate pagination info
        pages = (total + size - 1) // size

        # Convert to response models
        validation_responses = [
            ContractValidationResponse.model_validate(validation) for validation in validations
        ]

        return ContractValidationListResponse(
            items=validation_responses,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listing contract validations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve contract validations",
        )


@router.get("/{validation_id}", response_model=ContractValidationResponse)
async def get_contract_validation(
    validation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractValidationResponse:
    """
    Get a specific contract validation by ID.
    """
    try:
        validation = await contract_validation_service.get_contract_validation(
            db=db,
            contract_validation_id=validation_id,
            user_id=current_user.id,
        )

        if not validation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Contract validation not found"
            )

        return ContractValidationResponse.model_validate(validation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving contract validation {validation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve contract validation",
        )


@router.post("/{validation_id}/execute", response_model=ContractValidationResponse)
async def execute_contract_validation(
    validation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractValidationResponse:
    """
    Re-execute an existing contract validation.

    This endpoint allows re-running a contract validation that may have
    failed or needs to be updated with new results.
    """
    try:
        # Check if validation exists and belongs to user
        validation = await contract_validation_service.get_contract_validation(
            db=db,
            contract_validation_id=validation_id,
            user_id=current_user.id,
        )

        if not validation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Contract validation not found"
            )

        # Reset status to pending
        validation.status = ContractValidationStatus.PENDING.value
        validation.completed_at = None
        db.commit()

        # Execute validation in background
        background_tasks.add_task(
            contract_validation_service.execute_contract_validation, db, validation_id
        )

        logger.info(f"Re-executing contract validation {validation_id} for user {current_user.id}")

        return ContractValidationResponse.model_validate(validation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing contract validation {validation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute contract validation",
        )


@router.get(
    "/specifications/{specification_id}/health-summary", response_model=ContractHealthSummary
)
async def get_contract_health_summary(
    specification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractHealthSummary:
    """
    Get contract health summary for a specific API specification.

    This endpoint provides an overview of contract health metrics
    including validation counts, health scores, and latest validation.
    """
    try:
        summary = await contract_validation_service.get_contract_health_summary(
            db=db,
            api_specification_id=specification_id,
            user_id=current_user.id,
        )

        return ContractHealthSummary(**summary)

    except Exception as e:
        logger.error(
            f"Error retrieving contract health summary for specification {specification_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve contract health summary",
        )


@router.get("/health-status/overview", response_model=Dict[str, Any])
async def get_health_status_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get an overview of contract health status across all specifications.

    This endpoint provides aggregate metrics for contract health
    across all API specifications owned by the user.
    """
    try:
        # Get all validations for the user
        validations, _ = await contract_validation_service.get_contract_validations(
            db=db,
            user_id=current_user.id,
            status=ContractValidationStatus.COMPLETED,
            skip=0,
            limit=1000,  # Get a large number for overview
        )

        if not validations:
            return {
                "total_specifications": 0,
                "total_validations": 0,
                "overall_health_distribution": {
                    "healthy": 0,
                    "degraded": 0,
                    "broken": 0,
                },
                "average_health_score": 0.0,
                "recent_validations": [],
            }

        # Calculate metrics
        total_validations = len(validations)

        health_distribution = {
            "healthy": sum(
                1
                for v in validations
                if v.contract_health_status == ContractHealthStatus.HEALTHY.value
            ),
            "degraded": sum(
                1
                for v in validations
                if v.contract_health_status == ContractHealthStatus.DEGRADED.value
            ),
            "broken": sum(
                1
                for v in validations
                if v.contract_health_status == ContractHealthStatus.BROKEN.value
            ),
        }

        average_health_score = sum(v.health_score for v in validations) / total_validations

        # Get unique specifications
        unique_specs = set(v.api_specification_id for v in validations)

        # Get recent validations (last 5)
        recent_validations = sorted(validations, key=lambda v: v.triggered_at, reverse=True)[:5]
        recent_validation_data = [
            {
                "id": v.id,
                "api_specification_id": v.api_specification_id,
                "health_status": v.contract_health_status,
                "health_score": v.health_score,
                "triggered_at": v.triggered_at,
            }
            for v in recent_validations
        ]

        return {
            "total_specifications": len(unique_specs),
            "total_validations": total_validations,
            "overall_health_distribution": health_distribution,
            "average_health_score": round(average_health_score, 3),
            "recent_validations": recent_validation_data,
        }

    except Exception as e:
        logger.error(f"Error retrieving health status overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve health status overview",
        )
