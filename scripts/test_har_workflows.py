#!/usr/bin/env python3
"""
Test script for HAR processing n8n workflows.

This script tests both HAR processing notification workflows:
1. Workflow 4.1: HAR Processed & Sketches Ready
2. Workflow 4.2: Review Request for AI-Generated Artifacts

Usage:
    python scripts/test_har_workflows.py
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict

import requests


def create_har_processed_payload(success: bool = True) -> Dict[str, Any]:
    """Create a test payload for HAR processing completion."""
    base_payload = {
        "upload_id": 123,
        "file_name": "test-api-traffic.har",
        "user_id": 456,
        "timestamp": datetime.now().isoformat(),
        "processing_status": "completed" if success else "failed",
        "processing_statistics": {
            "interactions_count": 25,
            "processed_interactions_count": 23 if success else 10,
            "openapi_paths_count": 8 if success else 0,
            "wiremock_stubs_count": 23 if success else 0,
            "processing_steps_completed": 5 if success else 3,
            "total_processing_steps": 5,
            "processing_progress": 100 if success else 60,
            "processing_options": {
                "enable_ai_processing": True,
                "enable_data_generalization": True,
            },
        },
    }

    if success:
        base_payload["artifacts_summary"] = {
            "openapi_available": True,
            "openapi_title": "Test API",
            "openapi_version": "1.0.0",
            "openapi_paths_count": 8,
            "wiremock_available": True,
            "wiremock_stubs_count": 23,
            "artifacts_generated_at": datetime.now().isoformat(),
        }
    else:
        base_payload["error_message"] = (
            "Failed to parse HAR file: Invalid JSON structure"
        )
        base_payload["artifacts_summary"] = {
            "openapi_available": False,
            "wiremock_available": False,
        }

    return base_payload


def create_har_review_request_payload() -> Dict[str, Any]:
    """Create a test payload for HAR review request."""
    return {
        "upload_id": 124,
        "file_name": "complex-api-traffic.har",
        "user_id": 789,
        "timestamp": datetime.now().isoformat(),
        "artifacts_summary": {
            "openapi_available": True,
            "openapi_title": "Complex API",
            "openapi_version": "2.1.0",
            "openapi_paths_count": 15,
            "wiremock_available": True,
            "wiremock_stubs_count": 42,
            "artifacts_generated_at": datetime.now().isoformat(),
        },
        "review_url": "http://localhost:5173/har-uploads/124/review",
        "processing_statistics": {
            "interactions_count": 50,
            "processed_interactions_count": 48,
            "processing_options": {
                "enable_ai_processing": True,
                "enable_data_generalization": True,
            },
        },
    }


def test_webhook(url: str, payload: Dict[str, Any], workflow_name: str) -> bool:
    """Test a webhook endpoint with the given payload."""
    print(f"\n🧪 Testing {workflow_name}")
    print(f"📡 Webhook URL: {url}")
    print(f"📦 Payload preview: {json.dumps(payload, indent=2)[:200]}...")

    try:
        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=30
        )

        print(f"📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"✅ Success Response: {json.dumps(response_data, indent=2)}")
                return True
            except json.JSONDecodeError:
                print(f"✅ Success Response (non-JSON): {response.text}")
                return True
        else:
            print(f"❌ Error Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Starting HAR Processing Workflows Test")
    print("=" * 60)

    # Configuration
    n8n_base_url = "http://localhost:5679/webhook-test"

    # Test data
    test_cases = [
        {
            "name": "Workflow 4.1 - HAR Processing Success",
            "url": f"{n8n_base_url}/har-processed",
            "payload": create_har_processed_payload(success=True),
        },
        {
            "name": "Workflow 4.1 - HAR Processing Failure",
            "url": f"{n8n_base_url}/har-processed",
            "payload": create_har_processed_payload(success=False),
        },
        {
            "name": "Workflow 4.2 - HAR Review Request",
            "url": f"{n8n_base_url}/har-review-request",
            "payload": create_har_review_request_payload(),
        },
    ]

    # Run tests
    results = []
    for test_case in test_cases:
        success = test_webhook(
            test_case["url"], test_case["payload"], test_case["name"]
        )
        results.append((test_case["name"], success))

    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Results Summary")
    print("=" * 60)

    passed = 0
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")
        if success:
            passed += 1

    print(f"\n📊 Overall Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! HAR processing workflows are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the n8n configuration and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
