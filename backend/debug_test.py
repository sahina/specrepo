#!/usr/bin/env python3

import os
import sys

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.auth.api_key import create_user_with_api_key
from main import app
from tests.conftest import db_engine, setup_test_database


def test_auth_debug():
    """Debug authentication issues."""

    # Set up test database
    engine = db_engine()
    setup_test_database(engine)

    # Create a test session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Create a test user
        user, api_key = create_user_with_api_key(
            db, "debug_user", "debug@example.com"
        )
        print(f"Created user: {user.username} with API key: {api_key}")
        print(f"User ID: {user.id}")
        print(f"Stored API key hash: {user.api_key}")

        # Test with TestClient
        client = TestClient(app)

        # Test health endpoint
        response = client.get("/health")
        print(f"Health check: {response.status_code}")

        # Test profile endpoint with API key
        headers = {"X-API-Key": api_key}
        response = client.get("/api/profile", headers=headers)
        print(f"Profile response: {response.status_code}")

        if response.status_code != 200:
            print(f"Error response: {response.json()}")
        else:
            print(f"Profile data: {response.json()}")

        # Test API specifications endpoint
        spec_data = {
            "name": "Test API",
            "version_string": "v1.0",
            "openapi_content": {
                "openapi": "3.0.0",
                "info": {"title": "Test", "version": "1.0.0"},
                "paths": {},
            },
        }

        response = client.post(
            "/api/specifications", json=spec_data, headers=headers
        )
        print(f"Create spec response: {response.status_code}")

        if response.status_code != 201:
            print(f"Create spec error: {response.json()}")
        else:
            print(f"Created spec: {response.json()}")

    finally:
        db.close()


if __name__ == "__main__":
    test_auth_debug()
