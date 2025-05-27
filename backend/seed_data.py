#!/usr/bin/env python3
"""
Database seeding script for SpecRepo development and testing.

This script creates test users with known API keys and sample data
to make development and testing easier.
"""

import logging
from typing import List

from sqlalchemy.orm import Session

from app.auth.api_key import hash_api_key
from app.db.session import SessionLocal
from app.models import APISpecification, User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test users with predictable API keys for development
TEST_USERS = [
    {
        "username": "admin",
        "email": "admin@specrepo.dev",
        "api_key": "admin-dev-key-12345678901234567890",  # 32 chars
    },
    {
        "username": "developer",
        "email": "dev@specrepo.dev",
        "api_key": "dev-test-key-12345678901234567890",  # 32 chars
    },
    {
        "username": "tester",
        "email": "test@specrepo.dev",
        "api_key": "test-api-key-12345678901234567890",  # 32 chars
    },
]

# Sample OpenAPI specifications for testing
SAMPLE_SPECS = [
    {
        "name": "Pet Store API",
        "version_string": "v1.0.0",
        "openapi_content": {
            "openapi": "3.0.0",
            "info": {
                "title": "Pet Store API",
                "version": "1.0.0",
                "description": "A sample API for managing pets in a pet store",
            },
            "servers": [{"url": "https://api.petstore.example.com/v1"}],
            "paths": {
                "/pets": {
                    "get": {
                        "summary": "List all pets",
                        "operationId": "listPets",
                        "tags": ["pets"],
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "description": "How many items to return at one time (max 100)",
                                "required": False,
                                "schema": {
                                    "type": "integer",
                                    "maximum": 100,
                                    "format": "int32",
                                },
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "A paged array of pets",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"$ref": "#/components/schemas/Pet"},
                                        }
                                    }
                                },
                            }
                        },
                    },
                    "post": {
                        "summary": "Create a pet",
                        "operationId": "createPet",
                        "tags": ["pets"],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Pet"}
                                }
                            },
                        },
                        "responses": {
                            "201": {"description": "Pet created successfully"},
                            "400": {"description": "Invalid input"},
                        },
                    },
                },
                "/pets/{petId}": {
                    "get": {
                        "summary": "Info for a specific pet",
                        "operationId": "showPetById",
                        "tags": ["pets"],
                        "parameters": [
                            {
                                "name": "petId",
                                "in": "path",
                                "required": True,
                                "description": "The id of the pet to retrieve",
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Expected response to a valid request",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/Pet"}
                                    }
                                },
                            }
                        },
                    }
                },
            },
            "components": {
                "schemas": {
                    "Pet": {
                        "type": "object",
                        "required": ["id", "name"],
                        "properties": {
                            "id": {"type": "integer", "format": "int64"},
                            "name": {"type": "string"},
                            "tag": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["available", "pending", "sold"],
                            },
                        },
                    }
                }
            },
        },
    },
    {
        "name": "User Management API",
        "version_string": "v2.1.0",
        "openapi_content": {
            "openapi": "3.0.0",
            "info": {
                "title": "User Management API",
                "version": "2.1.0",
                "description": "API for managing user accounts and profiles",
            },
            "servers": [{"url": "https://api.users.example.com/v2"}],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "operationId": "listUsers",
                        "tags": ["users"],
                        "parameters": [
                            {
                                "name": "page",
                                "in": "query",
                                "schema": {"type": "integer", "default": 1},
                            },
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {
                                    "type": "integer",
                                    "default": 20,
                                    "maximum": 100,
                                },
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "List of users",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "users": {
                                                    "type": "array",
                                                    "items": {
                                                        "$ref": "#/components/schemas/User"
                                                    },
                                                },
                                                "pagination": {
                                                    "$ref": "#/components/schemas/Pagination"
                                                },
                                            },
                                        }
                                    }
                                },
                            }
                        },
                        "security": [{"ApiKeyAuth": []}],
                    }
                },
                "/users/{userId}": {
                    "get": {
                        "summary": "Get user by ID",
                        "operationId": "getUserById",
                        "tags": ["users"],
                        "parameters": [
                            {
                                "name": "userId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "User details",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/User"}
                                    }
                                },
                            },
                            "404": {"description": "User not found"},
                        },
                        "security": [{"ApiKeyAuth": []}],
                    }
                },
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "username": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "firstName": {"type": "string"},
                            "lastName": {"type": "string"},
                            "createdAt": {"type": "string", "format": "date-time"},
                            "status": {
                                "type": "string",
                                "enum": ["active", "inactive", "suspended"],
                            },
                        },
                    },
                    "Pagination": {
                        "type": "object",
                        "properties": {
                            "page": {"type": "integer"},
                            "limit": {"type": "integer"},
                            "total": {"type": "integer"},
                            "totalPages": {"type": "integer"},
                        },
                    },
                },
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    }
                },
            },
        },
    },
]


def create_test_user_with_known_key(
    db: Session, username: str, email: str, api_key: str
) -> User:
    """Create a user with a known API key for testing."""
    hashed_api_key = hash_api_key(api_key)

    user = User(username=username, email=email, api_key=hashed_api_key)
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def seed_users(db: Session) -> List[User]:
    """Seed test users with known API keys."""
    logger.info("Seeding test users...")

    users = []
    for user_data in TEST_USERS:
        # Check if user already exists
        existing_user = (
            db.query(User).filter(User.username == user_data["username"]).first()
        )
        if existing_user:
            logger.info(f"User '{user_data['username']}' already exists, skipping...")
            users.append(existing_user)
            continue

        user = create_test_user_with_known_key(
            db, user_data["username"], user_data["email"], user_data["api_key"]
        )
        users.append(user)
        logger.info(f"Created user: {user.username} (API Key: {user_data['api_key']})")

    return users


def seed_api_specifications(db: Session, users: List[User]) -> List[APISpecification]:
    """Seed sample API specifications."""
    logger.info("Seeding sample API specifications...")

    specs = []
    admin_user = next((u for u in users if u.username == "admin"), users[0])

    for spec_data in SAMPLE_SPECS:
        # Check if spec already exists
        existing_spec = (
            db.query(APISpecification)
            .filter(APISpecification.name == spec_data["name"])
            .first()
        )
        if existing_spec:
            logger.info(f"API spec '{spec_data['name']}' already exists, skipping...")
            specs.append(existing_spec)
            continue

        spec = APISpecification(
            name=spec_data["name"],
            version_string=spec_data["version_string"],
            openapi_content=spec_data["openapi_content"],
            user_id=admin_user.id,
        )
        db.add(spec)
        db.commit()
        db.refresh(spec)
        specs.append(spec)
        logger.info(f"Created API specification: {spec.name} v{spec.version_string}")

    return specs


def print_summary(users: List[User], specs: List[APISpecification]):
    """Print a summary of seeded data."""
    print("\n" + "=" * 60)
    print("🌱 DATABASE SEEDING COMPLETE")
    print("=" * 60)

    print("\n📋 TEST USERS CREATED:")
    print("-" * 40)
    for user in users:
        # Find the original API key for display
        user_data = next((u for u in TEST_USERS if u["username"] == user.username), None)
        api_key = user_data["api_key"] if user_data else "Generated dynamically"
        print(f"👤 {user.username}")
        print(f"   📧 Email: {user.email}")
        print(f"   🔑 API Key: {api_key}")
        print()

    print("📚 API SPECIFICATIONS CREATED:")
    print("-" * 40)
    for spec in specs:
        print(f"📄 {spec.name} v{spec.version_string}")
        print(f"   🆔 ID: {spec.id}")
        print(f"   👤 Owner: {spec.owner.username}")
        print()

    print("🧪 TESTING COMMANDS:")
    print("-" * 40)
    print("# Test health endpoint (no auth)")
    print("curl http://localhost:8000/health")
    print()
    print("# Test protected endpoint with admin user")
    print(
        f"curl -H 'X-API-Key: {TEST_USERS[0]['api_key']}' http://localhost:8000/api/protected"
    )
    print()
    print("# List API specifications")
    print(
        f"curl -H 'X-API-Key: {TEST_USERS[0]['api_key']}' http://localhost:8000/api/specifications"
    )
    print()
    print("# Get user profile")
    print(
        f"curl -H 'X-API-Key: {TEST_USERS[0]['api_key']}' http://localhost:8000/api/profile"
    )
    print()
    print("=" * 60)


def main():
    """Main seeding function."""
    logger.info("Starting database seeding...")

    db = SessionLocal()
    try:
        # Seed users
        users = seed_users(db)

        # Seed API specifications
        specs = seed_api_specifications(db, users)

        # Print summary
        print_summary(users, specs)

    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
