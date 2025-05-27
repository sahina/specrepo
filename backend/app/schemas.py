from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("openapi_content")
    @classmethod
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

    @field_validator("openapi_content")
    @classmethod
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

    model_config = ConfigDict(from_attributes=True)


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

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        allowed_fields = ["name", "version_string", "created_at", "updated_at"]
        if v not in allowed_fields:
            raise ValueError(
                f"sort_by must be one of: {', '.join(allowed_fields)}"
            )
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort_order field."""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v.lower()


class ValidationRunStatus(str, Enum):
    """Enum for validation run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuthMethod(str, Enum):
    """Enum for authentication methods."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"


class ValidationRunCreate(BaseModel):
    """Schema for creating a validation run."""

    api_specification_id: int = Field(
        ..., description="ID of the API specification to validate against"
    )
    provider_url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="URL of the provider to validate",
    )
    auth_method: AuthMethod = Field(
        default=AuthMethod.NONE, description="Authentication method to use"
    )
    auth_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Authentication configuration (API keys, tokens, etc.)",
    )
    test_strategies: Optional[List[str]] = Field(
        default=None,
        description=(
            "Specific test strategies to use "
            "(e.g., 'path_parameters', 'query_parameters')"
        ),
    )
    max_examples: Optional[int] = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of test examples to generate",
    )
    timeout: Optional[int] = Field(
        default=300,
        ge=30,
        le=3600,
        description="Timeout for the validation run in seconds",
    )

    @field_validator("provider_url")
    @classmethod
    def validate_provider_url(cls, v):
        """Validate provider URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                "Provider URL must start with http:// or https://"
            )
        return v


class ValidationRunResponse(BaseModel):
    """Schema for validation run response."""

    id: int
    api_specification_id: int
    provider_url: str
    status: ValidationRunStatus
    auth_method: AuthMethod
    test_strategies: Optional[List[str]] = None
    max_examples: Optional[int] = None
    timeout: Optional[int] = None
    schemathesis_results: Optional[Dict[str, Any]] = None
    triggered_at: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class ValidationRunListResponse(BaseModel):
    """Schema for paginated validation run list response."""

    items: List[ValidationRunResponse]
    total: int
    page: int
    size: int
    pages: int


class ValidationRunFilters(BaseModel):
    """Schema for validation run filtering and sorting."""

    api_specification_id: Optional[int] = Field(
        None, description="Filter by API specification ID"
    )
    status: Optional[ValidationRunStatus] = Field(
        None, description="Filter by status"
    )
    provider_url: Optional[str] = Field(
        None, description="Filter by provider URL (partial match)"
    )
    user_id: Optional[int] = Field(None, description="Filter by user ID")
    sort_by: Optional[str] = Field(
        "triggered_at",
        description="Sort field (triggered_at, status, provider_url)",
    )
    sort_order: Optional[str] = Field(
        "desc", description="Sort order (asc, desc)"
    )
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(10, ge=1, le=100, description="Page size")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        allowed_fields = ["triggered_at", "status", "provider_url"]
        if v not in allowed_fields:
            raise ValueError(
                f"sort_by must be one of: {', '.join(allowed_fields)}"
            )
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort_order field."""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v.lower()
