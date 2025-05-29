#!/usr/bin/env python3
"""Test script to debug HAR processing."""

import asyncio
import sys

sys.path.append(".")

from app.db.session import get_db
from app.models import User
from app.services.har_processing import HARProcessingService
from app.services.har_uploads import HARUploadService


async def test_processing():
    """Test HAR processing directly."""
    db = next(get_db())
    user = db.query(User).filter(User.id == 3).first()
    if not user:
        print("User not found")
        return

    service = HARProcessingService()
    try:
        print("Starting HAR processing test...")
        result = await service.process_har_upload(db, 2, user)
        print("Processing result:", result["success"])
        if result["success"]:
            print("Artifacts generated successfully")
            print(
                "OpenAPI paths:",
                result.get("artifacts", {})
                .get("processing_metadata", {})
                .get("openapi_paths_count"),
            )
            print(
                "WireMock stubs:",
                result.get("artifacts", {})
                .get("processing_metadata", {})
                .get("wiremock_stubs_count"),
            )
        else:
            print("Processing failed:", result.get("error"))
            print("Full result:", result)
    except Exception as e:
        print("Error:", str(e))
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_processing())
