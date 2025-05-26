from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class APISpecificationBase(BaseModel):
    """Base schema for API Specification."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the API specification",
    )
    version_string: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Version string (e.g., 'v1.0', '2.1.0')",
    )
    openapi_content: Dict[str, Any] = Field(
        ..., description="OpenAPI specification content as JSON"
    )

    @validator("openapi_content")
    def validate_openapi_content(cls, v):
        """Basic validation for OpenAPI content."""
        if not isinstance(v, dict):
            raise ValueError("OpenAPI content must be a valid JSON object")

        # Basic OpenAPI structure validation
        if "openapi" not in v and "swagger" not in v:
            raise ValueError(
                'OpenAPI content must contain "openapi" or "swagger" field'
            )

        if "info" not in v:
            raise ValueError('OpenAPI content must contain "info" field')

        return v


class APISpecificationCreate(APISpecificationBase):
    """Schema for creating an API Specification."""

    pass


class APISpecificationUpdate(BaseModel):
    """Schema for updating an API Specification."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    version_string: Optional[str] = Field(None, min_length=1, max_length=50)
    openapi_content: Optional[Dict[str, Any]] = None

    @validator("openapi_content")
    def validate_openapi_content(cls, v):
        """Basic validation for OpenAPI content."""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("OpenAPI content must be a valid JSON object")

        # Basic OpenAPI structure validation
        if "openapi" not in v and "swagger" not in v:
            raise ValueError(
                'OpenAPI content must contain "openapi" or "swagger" field'
            )

        if "info" not in v:
            raise ValueError('OpenAPI content must contain "info" field')

        return v


class APISpecificationResponse(APISpecificationBase):
    """Schema for API Specification response."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APISpecificationListResponse(BaseModel):
    """Schema for paginated API Specification list response."""

    items: List[APISpecificationResponse]
    total: int
    page: int
    size: int
    pages: int


class APISpecificationFilters(BaseModel):
    """Schema for API Specification filtering and sorting."""

    name: Optional[str] = Field(
        None, description="Filter by name (partial match)"
    )
    version_string: Optional[str] = Field(
        None, description="Filter by version string (exact match)"
    )
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    sort_by: Optional[str] = Field(
        "created_at",
        description=(
            "Sort field (name, version_string, created_at, updated_at)"
        ),
    )
    sort_order: Optional[str] = Field(
        "desc", description="Sort order (asc, desc)"
    )
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(10, ge=1, le=100, description="Page size")

    @validator("sort_by")
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        allowed_fields = ["name", "version_string", "created_at", "updated_at"]
        if v not in allowed_fields:
            raise ValueError(
                f"sort_by must be one of: {', '.join(allowed_fields)}"
            )
        return v

    @validator("sort_order")
    def validate_sort_order(cls, v):
        """Validate sort_order field."""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v.lower()
