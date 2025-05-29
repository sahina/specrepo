import logging
from typing import Dict

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth.api_key import create_user_with_api_key
from app.db.session import get_db
from app.dependencies import get_current_user
from app.middleware import RateLimitMiddleware
from app.models import User
from app.routers import (
    api_specifications,
    contract_validations,
    environments,
    har_uploads,
    mocks,
    validation_runs,
    validations,
    wiremock,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# API metadata for documentation
description = """
**SpecRepo API** provides comprehensive API lifecycle management capabilities.

## Features

* **API Specification Management**: Create, update, and manage OpenAPI specifications
* **Automated Mocking**: Deploy specifications as live mock services using WireMock
* **Contract Validation**: Validate real API implementations against specifications
* **HAR File Processing**: Upload and process HAR files with AI-powered analysis
* **Workflow Automation**: Automated notifications through n8n integration

## Authentication

This API uses **API Key authentication**. Include your API key in requests using either:

* `X-API-Key` header (recommended)
* `Authorization: Bearer <api-key>` header

To get an API key, create a user account using the `/api/users` endpoint.

## Rate Limiting

API requests are rate-limited to prevent abuse. Default limits:
* 100 requests per hour per API key
* Limits may vary by endpoint

## Support

For questions or issues, please refer to the project documentation or open an issue on GitHub.
"""

tags_metadata = [
    {
        "name": "Health",
        "description": "Health check and system status endpoints",
    },
    {
        "name": "Authentication",
        "description": "User management and authentication operations",
    },
    {
        "name": "API Specifications",
        "description": "Manage OpenAPI specifications - create, read, update, delete",
    },
    {
        "name": "WireMock Integration",
        "description": "Deploy specifications to WireMock for live mocking",
    },
    {
        "name": "Contract Validation",
        "description": "Validate API implementations against specifications using Schemathesis",
    },
    {
        "name": "HAR Processing",
        "description": "Upload and process HAR files with AI-powered analysis",
    },
    {
        "name": "Environments",
        "description": "Manage deployment environments and configurations",
    },
    {
        "name": "Mocks",
        "description": "Mock service management and configuration",
    },
    {
        "name": "Validation Runs",
        "description": "Execute and manage validation test runs",
    },
]

app = FastAPI(
    title="SpecRepo API",
    description=description,
    version="1.0.0",
    terms_of_service="https://github.com/sahina/specrepo/blob/main/LICENSE",
    contact={
        "name": "SpecRepo Team",
        "url": "https://github.com/sahina/specrepo",
        "email": "support@specrepo.dev",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/sahina/specrepo/blob/main/LICENSE",
    },
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],  # Frontend dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, max_attempts=5, window_seconds=300)

# Include routers with tags
app.include_router(api_specifications.router, tags=["API Specifications"])
app.include_router(contract_validations.router, tags=["Contract Validation"])
app.include_router(environments.router, tags=["Environments"])
app.include_router(har_uploads.router, tags=["HAR Processing"])
app.include_router(mocks.router, tags=["Mocks"])
app.include_router(validations.router, tags=["Contract Validation"])
app.include_router(validation_runs.router, tags=["Validation Runs"])
app.include_router(wiremock.router, tags=["WireMock Integration"])


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description=(
        "Check the health status of the API service. This endpoint requires no authentication."
    ),
    response_description="Service health status",
)
def read_root():
    """
    Health check endpoint - no authentication required.

    Returns the current status of the API service. Use this endpoint to verify
    that the service is running and accessible.

    **Example Response:**
    ```json
    {
        "status": "healthy"
    }
    ```
    """
    return {"status": "healthy"}


@app.post(
    "/api/users",
    response_model=Dict[str, str],
    tags=["Authentication"],
    summary="Create User Account",
    description="Create a new user account and receive an API key for authentication.",
    response_description="User creation confirmation with API key",
)
def create_user(username: str, email: str, db: Session = Depends(get_db)):
    """
    Create a new user with an API key.

    This endpoint is public for user registration. After creating an account,
    use the returned API key for authenticating subsequent requests.

    **Parameters:**
    - **username**: Unique username for the account (3-50 characters)
    - **email**: Valid email address for the account

    **Example Request:**
    ```
    POST /api/users?username=johndoe&email=john@example.com
    ```

    **Example Response:**
    ```json
    {
        "message": "User created successfully",
        "username": "johndoe",
        "api_key": "abcd1234567890abcd1234567890abcd"
    }
    ```

    **Note:** Store the API key securely - it cannot be retrieved later.
    """
    try:
        user, api_key = create_user_with_api_key(db, username, email)
        logger.info(f"Created new user: {username}")
        return {
            "message": "User created successfully",
            "username": user.username,
            "api_key": api_key,
        }
    except Exception as e:
        logger.error(f"Failed to create user {username}: {str(e)}")
        raise


@app.get(
    "/api/profile",
    tags=["Authentication"],
    summary="Get User Profile",
    description="Retrieve the current user's profile information.",
    response_description="User profile data",
)
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile - requires authentication.

    Returns profile information for the authenticated user.

    **Authentication Required:** Yes (API Key)

    **Example Request:**
    ```bash
    curl -H "X-API-Key: your-api-key" http://localhost:8000/api/profile
    ```

    **Example Response:**
    ```json
    {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "created_at": "2024-01-01T12:00:00Z"
    }
    ```
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at,
    }


@app.get(
    "/api/protected",
    tags=["Authentication"],
    summary="Protected Endpoint Example",
    description="Example of a protected endpoint that requires authentication.",
    response_description="Protected resource data",
)
def protected_endpoint(current_user: User = Depends(get_current_user)):
    """
    Example protected endpoint that requires authentication.

    This endpoint demonstrates how authentication works in the API.
    All protected endpoints require a valid API key.

    **Authentication Required:** Yes (API Key)

    **Example Request:**
    ```bash
    curl -H "X-API-Key: your-api-key" http://localhost:8000/api/protected
    ```

    **Example Response:**
    ```json
    {
        "message": "Hello johndoe! This is a protected endpoint.",
        "user_id": 1
    }
    ```
    """
    return {
        "message": f"Hello {current_user.username}! This is a protected endpoint.",
        "user_id": current_user.id,
    }
