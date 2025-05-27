#!/usr/bin/env python3
"""
Script to automatically import and activate the n8n workflow for API specification notifications.
This script uses the n8n API to import the workflow and activate it.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx


class N8nWorkflowSetup:
    """Setup class for n8n workflow management."""

    def __init__(self, n8n_base_url: str = "http://localhost:5678"):
        self.n8n_base_url = n8n_base_url
        self.workflow_file = Path("n8n/workflows/unified-notification.json")
        self.api_key = os.getenv("N8N_API_KEY", "specrepo-n8n-api-key-2024")
        self.headers = {
            "Content-Type": "application/json",
            "X-N8N-API-KEY": self.api_key,
        }

    async def check_n8n_health(self) -> bool:
        """Check if n8n service is running."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.n8n_base_url}/healthz")
                return response.status_code in [200, 404]
        except httpx.RequestError:
            return False

    async def get_existing_workflows(self) -> list:
        """Get list of existing workflows."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.n8n_base_url}/api/v1/workflows", headers=self.headers
                )
                if response.status_code == 200:
                    return response.json().get("data", [])
                return []
        except httpx.RequestError:
            return []

    async def import_workflow(self) -> dict:
        """Import the workflow from the JSON file."""
        if not self.workflow_file.exists():
            raise FileNotFoundError(f"Workflow file not found: {self.workflow_file}")

        with open(self.workflow_file, "r") as f:
            workflow_data = json.load(f)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.n8n_base_url}/api/v1/workflows",
                    json=workflow_data,
                    headers=self.headers,
                )

                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    print(f"Failed to import workflow: {response.status_code}")
                    print(f"Response: {response.text}")
                    return {}
        except httpx.RequestError as e:
            print(f"Error importing workflow: {e}")
            return {}

    async def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow by ID."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.patch(
                    f"{self.n8n_base_url}/api/v1/workflows/{workflow_id}",
                    json={"active": True},
                    headers=self.headers,
                )
                return response.status_code == 200
        except httpx.RequestError:
            return False

    async def setup_workflow(self) -> bool:
        """Main setup method to import and activate the workflow."""
        print("🔧 Setting up n8n workflow for API specification notifications...")
        print("=" * 60)

        # Check n8n health
        print("📡 Checking n8n service health...")
        if not await self.check_n8n_health():
            print("❌ n8n service is not running or not accessible")
            print("💡 Make sure n8n is running: docker-compose up n8n")
            return False
        print("✅ n8n service is running")

        # Check existing workflows
        print("\n📋 Checking existing workflows...")
        existing_workflows = await self.get_existing_workflows()

        # Check if our workflow already exists
        existing_workflow = None
        for workflow in existing_workflows:
            if workflow.get("name") == "New API Spec Notification":
                existing_workflow = workflow
                break

        if existing_workflow:
            print(f"📄 Workflow already exists with ID: {existing_workflow['id']}")

            if existing_workflow.get("active"):
                print("✅ Workflow is already active")
                return True
            else:
                print("🔄 Activating existing workflow...")
                if await self.activate_workflow(existing_workflow["id"]):
                    print("✅ Workflow activated successfully")
                    return True
                else:
                    print("❌ Failed to activate workflow")
                    return False

        # Import new workflow
        print("\n📥 Importing workflow...")
        imported_workflow = await self.import_workflow()

        if not imported_workflow:
            print("❌ Failed to import workflow")
            return False

        workflow_id = imported_workflow.get("id")
        print(f"✅ Workflow imported successfully with ID: {workflow_id}")

        # Activate workflow
        print("\n🔄 Activating workflow...")
        if await self.activate_workflow(workflow_id):
            print("✅ Workflow activated successfully")
            return True
        else:
            print("❌ Failed to activate workflow")
            return False

    async def test_webhook(self) -> bool:
        """Test the webhook endpoint after setup."""
        print("\n🧪 Testing webhook endpoint...")

        webhook_url = f"{self.n8n_base_url}/webhook-test/notification"
        test_payload = {
            "event_type": "created",
            "specification_id": 999,
            "specification_name": "Test Setup Workflow",
            "version_string": "v1.0.0",
            "user_id": 1,
            "timestamp": "2024-01-01T00:00:00Z",
            "openapi_content": {
                "openapi": "3.0.0",
                "info": {
                    "title": "Test API",
                    "version": "1.0.0",
                    "description": "Test API for workflow setup",
                },
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook_url,
                    json=test_payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    print("✅ Webhook test successful!")
                    print(f"📄 Response: {response.json()}")
                    return True
                else:
                    print(f"⚠️ Webhook test returned status: {response.status_code}")
                    print(f"📄 Response: {response.text}")
                    return False
        except httpx.RequestError as e:
            print(f"❌ Webhook test failed: {e}")
            return False


async def main():
    """Main function to run the setup."""
    setup = N8nWorkflowSetup()

    try:
        success = await setup.setup_workflow()

        if success:
            print("\n" + "=" * 60)
            print("🎉 n8n workflow setup completed successfully!")

            # Test the webhook
            test_success = await setup.test_webhook()

            if test_success:
                print("\n✅ All tests passed! The n8n integration is ready to use.")
                print("\n📋 Next steps:")
                print("1. Configure SMTP settings in n8n for email notifications")
                print("2. Update email addresses in the workflow nodes")
                print("3. Test with real API specification events")
            else:
                print("\n⚠️ Setup completed but webhook test failed.")
                print("💡 You may need to manually test the workflow in n8n interface.")
        else:
            print("\n❌ Setup failed. Please check the error messages above.")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
