#!/usr/bin/env python3
"""
Manual test script for n8n webhook integration.

This script tests the n8n workflow webhook endpoint directly,
providing detailed output about the webhook's functionality.

Usage:
    python scripts/test_n8n_webhook.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

import httpx


class N8nWebhookTester:
    """Test class for n8n webhook functionality."""

    def __init__(self):
        self.webhook_url = os.getenv(
            "N8N_WEBHOOK_URL",
            "http://localhost:5678/webhook-test/api-spec-notification",
        )
        self.webhook_secret = os.getenv("N8N_WEBHOOK_SECRET")
        self.base_url = self.webhook_url.split("/webhook")[0]

    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{'=' * 60}")
        print(f"{title:^60}")
        print(f"{'=' * 60}")

    def print_section(self, title: str):
        """Print a formatted section header."""
        print(f"\n{'-' * 40}")
        print(f"{title}")
        print(f"{'-' * 40}")

    async def check_n8n_health(self) -> bool:
        """Check if n8n service is running."""
        self.print_section("Checking n8n Service Health")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/healthz")

                if response.status_code in [200, 404]:
                    print(f"✅ n8n service is running at {self.base_url}")
                    print(f"   Status: {response.status_code}")
                    return True
                else:
                    print(
                        f"⚠️ n8n service responded with status: {response.status_code}"
                    )
                    return False

        except httpx.RequestError as e:
            print(f"❌ Cannot reach n8n service: {e}")
            print(f"   Make sure n8n is running at {self.base_url}")
            return False

    def get_test_payload(self, event_type: str = "created") -> Dict[str, Any]:
        """Generate a comprehensive test payload."""
        timestamp = datetime.now().isoformat() + "Z"

        return {
            "event_type": event_type,
            "specification_id": 12345,
            "specification_name": f"Test API Specification ({event_type})",
            "version_string": "v1.2.3",
            "user_id": 67890,
            "timestamp": timestamp,
            "openapi_content": {
                "openapi": "3.0.0",
                "info": {
                    "title": f"Test API ({event_type})",
                    "description": f"A comprehensive test API for {event_type} event testing",
                    "version": "1.2.3",
                    "contact": {
                        "name": "Test Team",
                        "email": "test@example.com",
                        "url": "https://example.com/support",
                    },
                    "license": {
                        "name": "MIT",
                        "url": "https://opensource.org/licenses/MIT",
                    },
                },
                "servers": [
                    {
                        "url": "https://api.example.com/v1",
                        "description": "Production server",
                    },
                    {
                        "url": "https://staging-api.example.com/v1",
                        "description": "Staging server",
                    },
                ],
                "paths": {
                    "/users": {
                        "get": {
                            "summary": "List all users",
                            "description": "Retrieve a paginated list of users",
                            "tags": ["Users"],
                            "parameters": [
                                {
                                    "name": "page",
                                    "in": "query",
                                    "description": "Page number",
                                    "required": False,
                                    "schema": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "default": 1,
                                    },
                                },
                                {
                                    "name": "limit",
                                    "in": "query",
                                    "description": "Number of items per page",
                                    "required": False,
                                    "schema": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "maximum": 100,
                                        "default": 20,
                                    },
                                },
                            ],
                            "responses": {
                                "200": {
                                    "description": "Successful response",
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
                                },
                                "400": {
                                    "description": "Bad request",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/Error"
                                            }
                                        }
                                    },
                                },
                            },
                        },
                        "post": {
                            "summary": "Create a new user",
                            "description": "Create a new user account",
                            "tags": ["Users"],
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/CreateUserRequest"
                                        }
                                    }
                                },
                            },
                            "responses": {
                                "201": {
                                    "description": "User created successfully",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/User"
                                            }
                                        }
                                    },
                                },
                                "400": {
                                    "description": "Invalid input",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/Error"
                                            }
                                        }
                                    },
                                },
                                "409": {
                                    "description": "User already exists",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/Error"
                                            }
                                        }
                                    },
                                },
                            },
                        },
                    },
                    "/users/{id}": {
                        "get": {
                            "summary": "Get user by ID",
                            "description": "Retrieve a specific user by their ID",
                            "tags": ["Users"],
                            "parameters": [
                                {
                                    "name": "id",
                                    "in": "path",
                                    "description": "User ID",
                                    "required": True,
                                    "schema": {"type": "integer", "minimum": 1},
                                }
                            ],
                            "responses": {
                                "200": {
                                    "description": "User found",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/User"
                                            }
                                        }
                                    },
                                },
                                "404": {
                                    "description": "User not found",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/Error"
                                            }
                                        }
                                    },
                                },
                            },
                        }
                    },
                },
                "components": {
                    "schemas": {
                        "User": {
                            "type": "object",
                            "required": ["id", "email", "name"],
                            "properties": {
                                "id": {
                                    "type": "integer",
                                    "description": "Unique user identifier",
                                },
                                "email": {
                                    "type": "string",
                                    "format": "email",
                                    "description": "User's email address",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "User's full name",
                                },
                                "created_at": {
                                    "type": "string",
                                    "format": "date-time",
                                    "description": "Account creation timestamp",
                                },
                                "updated_at": {
                                    "type": "string",
                                    "format": "date-time",
                                    "description": "Last update timestamp",
                                },
                                "roles": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "User roles",
                                },
                            },
                        },
                        "CreateUserRequest": {
                            "type": "object",
                            "required": ["email", "name"],
                            "properties": {
                                "email": {
                                    "type": "string",
                                    "format": "email",
                                    "description": "User's email address",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "User's full name",
                                },
                                "roles": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Initial user roles",
                                },
                            },
                        },
                        "Pagination": {
                            "type": "object",
                            "properties": {
                                "page": {
                                    "type": "integer",
                                    "description": "Current page number",
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Items per page",
                                },
                                "total": {
                                    "type": "integer",
                                    "description": "Total number of items",
                                },
                                "pages": {
                                    "type": "integer",
                                    "description": "Total number of pages",
                                },
                            },
                        },
                        "Error": {
                            "type": "object",
                            "required": ["error", "message"],
                            "properties": {
                                "error": {
                                    "type": "string",
                                    "description": "Error code",
                                },
                                "message": {
                                    "type": "string",
                                    "description": "Human-readable error message",
                                },
                                "details": {
                                    "type": "object",
                                    "description": "Additional error details",
                                },
                            },
                        },
                    }
                },
                "tags": [
                    {"name": "Users", "description": "User management operations"}
                ],
            },
        }

    async def test_webhook(self, event_type: str = "created") -> Dict[str, Any]:
        """Test the webhook with a specific event type."""
        self.print_section(f"Testing {event_type.upper()} Event")

        payload = self.get_test_payload(event_type)
        headers = {"Content-Type": "application/json"}

        if self.webhook_secret:
            headers["X-N8N-Webhook-Secret"] = self.webhook_secret
            print(f"🔐 Using webhook secret: {'*' * len(self.webhook_secret)}")

        print(f"📤 Sending {event_type} event to: {self.webhook_url}")
        print(f"📋 Specification ID: {payload['specification_id']}")
        print(f"📋 Specification Name: {payload['specification_name']}")
        print(f"📋 Version: {payload['version_string']}")
        print(f"📋 User ID: {payload['user_id']}")
        print(f"📋 Timestamp: {payload['timestamp']}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.webhook_url, json=payload, headers=headers
                )

                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "success": response.status_code in [200, 201, 202],
                }

                try:
                    result["response_data"] = response.json()
                except:
                    result["response_text"] = response.text

                # Print results
                if result["success"]:
                    print(f"✅ Webhook successful! Status: {response.status_code}")
                    if "response_data" in result:
                        print(
                            f"📄 Response: {json.dumps(result['response_data'], indent=2)}"
                        )
                    else:
                        print(
                            f"📄 Response: {result.get('response_text', 'No response body')}"
                        )
                else:
                    print(f"❌ Webhook failed! Status: {response.status_code}")
                    if "response_data" in result:
                        print(
                            f"📄 Error response: {json.dumps(result['response_data'], indent=2)}"
                        )
                    else:
                        print(
                            f"📄 Error response: {result.get('response_text', 'No response body')}"
                        )

                return result

        except httpx.TimeoutException:
            print(f"⏰ Webhook request timed out after 30 seconds")
            return {"error": "timeout", "success": False}
        except httpx.RequestError as e:
            print(f"❌ Request error: {e}")
            return {"error": str(e), "success": False}
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {"error": str(e), "success": False}

    def print_environment_info(self):
        """Print current environment configuration."""
        self.print_section("Environment Configuration")

        print(f"N8N_WEBHOOK_URL: {self.webhook_url}")
        print(f"N8N_WEBHOOK_SECRET: {'***' if self.webhook_secret else 'Not set'}")
        print(f"N8N_MAX_RETRIES: {os.getenv('N8N_MAX_RETRIES', '3')}")
        print(f"N8N_RETRY_DELAY_SECONDS: {os.getenv('N8N_RETRY_DELAY_SECONDS', '5')}")
        print(f"N8N_TIMEOUT_SECONDS: {os.getenv('N8N_TIMEOUT_SECONDS', '30')}")

    def print_setup_instructions(self):
        """Print setup instructions if webhook fails."""
        self.print_section("Setup Instructions")

        print("If the webhook is not working, follow these steps:")
        print()
        print("1. Make sure n8n is running:")
        print("   docker-compose up n8n")
        print()
        print("2. Access n8n interface:")
        print("   http://localhost:5679")
        print()
        print("3. Import the workflow:")
        print("   - Go to 'Workflows' in n8n")
        print("   - Click 'Import from File'")
        print("   - Select 'n8n/workflows/api-spec-notification.json'")
        print("   - Save the workflow")
        print()
        print("4. Activate the workflow:")
        print("   - Open the imported workflow")
        print("   - Click the 'Active' toggle")
        print()
        print("5. Configure email settings (optional):")
        print("   - Go to 'Settings' > 'Credentials'")
        print("   - Add SMTP credentials")
        print("   - Update email nodes in the workflow")
        print()
        print("6. Test the workflow:")
        print("   - Click 'Test workflow' button in n8n")
        print("   - Then run this script again")

    async def run_all_tests(self):
        """Run all webhook tests."""
        self.print_header("N8N WEBHOOK INTEGRATION TEST")

        # Print environment info
        self.print_environment_info()

        # Check n8n health
        n8n_healthy = await self.check_n8n_health()

        if not n8n_healthy:
            print(
                "\n❌ n8n service is not available. Cannot proceed with webhook tests."
            )
            self.print_setup_instructions()
            return False

        # Test created event
        created_result = await self.test_webhook("created")

        # Test updated event
        updated_result = await self.test_webhook("updated")

        # Summary
        self.print_section("Test Summary")

        created_success = created_result.get("success", False)
        updated_success = updated_result.get("success", False)

        print(f"Created event test: {'✅ PASS' if created_success else '❌ FAIL'}")
        print(f"Updated event test: {'✅ PASS' if updated_success else '❌ FAIL'}")

        if not (created_success or updated_success):
            print("\n❌ All webhook tests failed!")
            self.print_setup_instructions()
            return False
        elif created_success and updated_success:
            print("\n✅ All webhook tests passed!")
            print("🎉 n8n workflow integration is working correctly!")
            return True
        else:
            print("\n⚠️ Some webhook tests failed!")
            print("Check the workflow configuration in n8n.")
            return False


async def main():
    """Main test function."""
    tester = N8nWebhookTester()
    success = await tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
