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
            raise ValueError('OpenAPI content must contain "openapi" or "swagger" field')

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
            raise ValueError('OpenAPI content must contain "openapi" or "swagger" field')

        if "info" not in v:
            raise ValueError('OpenAPI content must contain "info" field')

        return v


class APISpecificationResponse(APISpecificationBase):
    """Schema for API Specification responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class APISpecificationFilters(BaseModel):
    """Schema for API Specification filtering and pagination."""

    name: Optional[str] = None
    version_string: Optional[str] = None
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        allowed_fields = ["name", "version_string", "created_at", "updated_at"]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of: {allowed_fields}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort_order field."""
        if v not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class APISpecificationListResponse(BaseModel):
    """Schema for paginated API Specification list response."""

    items: List[APISpecificationResponse]
    total: int
    page: int
    size: int
    pages: int


# Environment Management Schemas
class EnvironmentType(str, Enum):
    """Environment type enumeration."""

    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    CUSTOM = "custom"


class EnvironmentBase(BaseModel):
    """Base schema for Environment."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the environment (e.g., 'Production API', 'Staging')",
    )
    base_url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Base URL of the environment (e.g., 'https://api.example.com')",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description of the environment",
    )
    environment_type: EnvironmentType = Field(
        default=EnvironmentType.CUSTOM,
        description="Type of environment",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v):
        """Validate base URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip("/")  # Remove trailing slash for consistency


class EnvironmentCreate(EnvironmentBase):
    """Schema for creating an Environment."""

    pass


class EnvironmentUpdate(BaseModel):
    """Schema for updating an Environment."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    base_url: Optional[str] = Field(None, min_length=1, max_length=2048)
    description: Optional[str] = Field(None, max_length=500)
    environment_type: Optional[EnvironmentType] = None
    is_active: Optional[str] = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v):
        """Validate base URL format."""
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip("/")


class EnvironmentResponse(EnvironmentBase):
    """Schema for Environment responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class EnvironmentFilters(BaseModel):
    """Schema for Environment filtering and pagination."""

    name: Optional[str] = None
    environment_type: Optional[EnvironmentType] = None
    is_active: Optional[str] = Field(default="true")
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        allowed_fields = ["name", "environment_type", "created_at", "updated_at"]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of: {allowed_fields}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort_order field."""
        if v not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class EnvironmentListResponse(BaseModel):
    """Schema for paginated Environment list response."""

    items: List[EnvironmentResponse]
    total: int
    page: int
    size: int
    pages: int


# Validation Schemas
class AuthMethod(str, Enum):
    """Authentication method enumeration."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"


class ValidationRunStatus(str, Enum):
    """Validation run status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationRunCreate(BaseModel):
    """Schema for creating a validation run."""

    api_specification_id: int = Field(
        ..., description="ID of the API specification to validate against"
    )
    # Support both environment selection and custom URL
    environment_id: Optional[int] = Field(
        None, description="ID of the predefined environment to validate against"
    )
    provider_url: Optional[str] = Field(
        None,
        min_length=1,
        max_length=2048,
        description="Custom provider URL (used if environment_id is not provided)",
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
            "Specific test strategies to use (e.g., 'path_parameters', 'query_parameters')"
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
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("Provider URL must start with http:// or https://")
        return v

    def model_post_init(self, __context):
        """Validate that either environment_id or provider_url is provided."""
        if not self.environment_id and not self.provider_url:
            raise ValueError("Either environment_id or provider_url must be provided")
        if self.environment_id and self.provider_url:
            raise ValueError("Cannot specify both environment_id and provider_url")


class ValidationRunResponse(BaseModel):
    """Schema for validation run responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    api_specification_id: int
    provider_url: str
    environment_id: Optional[int] = None
    auth_method: AuthMethod
    auth_config: Optional[Dict[str, Any]] = None
    test_strategies: Optional[List[str]] = None
    max_examples: int
    timeout: int
    schemathesis_results: Optional[Dict[str, Any]] = None
    status: ValidationRunStatus
    triggered_at: datetime
    user_id: int


class ValidationRunFilters(BaseModel):
    """Schema for validation run filtering and pagination."""

    api_specification_id: Optional[int] = None
    status: Optional[ValidationRunStatus] = None
    environment_id: Optional[int] = None
    provider_url: Optional[str] = None
    sort_by: str = Field(default="triggered_at")
    sort_order: str = Field(default="desc")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        allowed_fields = ["triggered_at", "status", "provider_url"]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of: {allowed_fields}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort_order field."""
        if v not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class ValidationRunListResponse(BaseModel):
    """Schema for paginated validation run list response."""

    items: List[ValidationRunResponse]
    total: int
    page: int
    size: int
    pages: int


# HAR Upload Schemas
class HARUploadResponse(BaseModel):
    """Schema for HAR upload responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    processed_artifacts_references: Optional[Dict[str, Any]] = None
    uploaded_at: datetime
    user_id: int


class HARUploadFilters(BaseModel):
    """Schema for HAR upload filtering and pagination."""

    file_name: Optional[str] = None
    sort_by: str = Field(default="uploaded_at")
    sort_order: str = Field(default="desc")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        allowed_fields = ["file_name", "uploaded_at"]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of: {allowed_fields}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort_order field."""
        if v not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class HARUploadListResponse(BaseModel):
    """Schema for paginated HAR upload list response."""

    items: List[HARUploadResponse]
    total: int
    page: int
    size: int
    pages: int


# HAR Processing Schemas
class HARProcessingOptions(BaseModel):
    """Schema for HAR processing options."""

    api_title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Title for the generated OpenAPI specification",
    )
    api_description: Optional[str] = Field(
        None,
        max_length=500,
        description="Description for the generated OpenAPI specification",
    )
    api_version: Optional[str] = Field(
        None,
        min_length=1,
        max_length=20,
        description="Version for the generated OpenAPI specification",
    )
    enable_ai_processing: Optional[bool] = Field(
        default=True,
        description="Enable AI-based data processing and generalization",
    )
    enable_data_generalization: Optional[bool] = Field(
        default=True,
        description="Enable data generalization for creating reusable mock responses",
    )
    wiremock_stateful: Optional[bool] = Field(
        default=True,
        description="Enable stateful behavior in WireMock stubs",
    )
    wiremock_templating: Optional[bool] = Field(
        default=True,
        description="Enable response templating in WireMock stubs",
    )


class HARProcessingStatus(str, Enum):
    """HAR processing status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HARProcessingStepStatus(BaseModel):
    """Schema for individual processing step status."""

    status: str = Field(..., description="Status of the step")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    result: Optional[str] = Field(None, description="Result message")


class HARProcessingStatusResponse(BaseModel):
    """Schema for HAR processing status response."""

    status: HARProcessingStatus
    progress: int = Field(..., ge=0, le=100, description="Overall progress percentage")
    current_step: Optional[str] = Field(None, description="Current processing step")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    failed_at: Optional[datetime] = Field(None, description="Processing failure time")
    error: Optional[str] = Field(None, description="Error message if failed")
    artifacts_available: bool = Field(..., description="Whether artifacts are available")
    interactions_count: Optional[int] = Field(None, description="Number of API interactions found")
    openapi_paths_count: Optional[int] = Field(
        None, description="Number of OpenAPI paths generated"
    )
    wiremock_stubs_count: Optional[int] = Field(
        None, description="Number of WireMock stubs generated"
    )
    steps: Optional[Dict[str, HARProcessingStepStatus]] = Field(
        None, description="Detailed step status information"
    )


class HARProcessingResponse(BaseModel):
    """Schema for HAR processing initiation response."""

    success: bool = Field(..., description="Whether processing was initiated successfully")
    upload_id: int = Field(..., description="ID of the HAR upload being processed")
    message: str = Field(..., description="Status message")
    processing_status: Optional[HARProcessingStatusResponse] = Field(
        None, description="Current processing status"
    )


class HARProcessingMetadata(BaseModel):
    """Schema for HAR processing metadata."""

    interactions_count: int = Field(..., description="Number of API interactions processed")
    processed_interactions_count: int = Field(
        ..., description="Number of successfully processed interactions"
    )
    openapi_paths_count: int = Field(..., description="Number of OpenAPI paths generated")
    wiremock_stubs_count: int = Field(..., description="Number of WireMock stubs generated")
    processed_at: datetime = Field(..., description="Processing completion timestamp")
    processing_options: Dict[str, Any] = Field(..., description="Options used for processing")


class HARProcessingArtifacts(BaseModel):
    """Schema for HAR processing artifacts."""

    openapi_specification: Dict[str, Any] = Field(
        ..., description="Generated OpenAPI specification"
    )
    wiremock_mappings: List[Dict[str, Any]] = Field(
        ..., description="Generated WireMock stub mappings"
    )
    processing_metadata: HARProcessingMetadata = Field(..., description="Processing metadata")


class HARProcessingArtifactsResponse(BaseModel):
    """Schema for HAR processing artifacts response."""

    upload_id: int = Field(..., description="ID of the HAR upload")
    file_name: str = Field(..., description="Name of the original HAR file")
    artifacts: HARProcessingArtifacts = Field(..., description="Generated artifacts")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    processed_at: datetime = Field(..., description="Processing completion timestamp")
