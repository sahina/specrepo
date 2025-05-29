import json
import logging
from io import StringIO
from typing import List, Optional, Tuple

import harfile
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models import HARUpload, User
from app.schemas import HARUploadFilters

logger = logging.getLogger(__name__)


class HARUploadService:
    """Service class for HAR upload operations."""

    @staticmethod
    def create_har_upload(db: Session, file_name: str, raw_content: str, user: User) -> HARUpload:
        """
        Create a new HAR upload record.

        Args:
            db: Database session
            file_name: Name of the uploaded file
            raw_content: Raw HAR file content as string
            user: User who uploaded the file

        Returns:
            Created HARUpload instance

        Raises:
            ValueError: If HAR content is invalid
        """
        # Validate HAR content
        if not HARUploadService.validate_har_content(raw_content):
            raise ValueError("Invalid HAR file format")

        har_upload = HARUpload(
            file_name=file_name,
            raw_content=raw_content,
            user_id=user.id,
        )

        db.add(har_upload)
        db.commit()
        db.refresh(har_upload)

        logger.info(f"Created HAR upload {har_upload.id} for user {user.username}")
        return har_upload

    @staticmethod
    def get_har_uploads(
        db: Session, user: User, filters: HARUploadFilters
    ) -> Tuple[List[HARUpload], int]:
        """
        Get paginated list of HAR uploads for a user.

        Args:
            db: Database session
            user: User to get uploads for
            filters: Filtering and pagination parameters

        Returns:
            Tuple of (uploads list, total count)
        """
        query = db.query(HARUpload).filter(HARUpload.user_id == user.id)

        # Apply filters
        if filters.file_name:
            query = query.filter(HARUpload.file_name.ilike(f"%{filters.file_name}%"))

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = getattr(HARUpload, filters.sort_by)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (filters.page - 1) * filters.size
        uploads = query.offset(offset).limit(filters.size).all()

        return uploads, total

    @staticmethod
    def get_har_upload(db: Session, upload_id: int, user: User) -> Optional[HARUpload]:
        """
        Get a specific HAR upload by ID for a user.

        Args:
            db: Database session
            upload_id: ID of the upload to retrieve
            user: User who owns the upload

        Returns:
            HARUpload instance if found, None otherwise
        """
        return (
            db.query(HARUpload)
            .filter(and_(HARUpload.id == upload_id, HARUpload.user_id == user.id))
            .first()
        )

    @staticmethod
    def delete_har_upload(db: Session, upload_id: int, user: User) -> bool:
        """
        Delete a HAR upload.

        Args:
            db: Database session
            upload_id: ID of the upload to delete
            user: User who owns the upload

        Returns:
            True if deleted, False if not found
        """
        upload = HARUploadService.get_har_upload(db, upload_id, user)
        if not upload:
            return False

        db.delete(upload)
        db.commit()

        logger.info(f"Deleted HAR upload {upload_id} for user {user.username}")
        return True

    @staticmethod
    def update_processed_artifacts(
        db: Session, upload_id: int, user: User, artifacts: dict
    ) -> Optional[HARUpload]:
        """
        Update the processed artifacts references for a HAR upload.

        Args:
            db: Database session
            upload_id: ID of the upload to update
            user: User who owns the upload
            artifacts: Dictionary of processed artifacts references

        Returns:
            Updated HARUpload instance if found, None otherwise
        """
        upload = HARUploadService.get_har_upload(db, upload_id, user)
        if not upload:
            return None

        upload.processed_artifacts_references = artifacts
        db.commit()
        db.refresh(upload)

        logger.info(f"Updated artifacts for HAR upload {upload_id}")
        return upload

    @staticmethod
    def validate_har_content(content: str) -> bool:
        """
        Validate HAR file content without creating a database record.

        Args:
            content: HAR file content as string

        Returns:
            True if valid, False otherwise
        """
        try:
            # Parse JSON
            har_data = json.loads(content)

            # Check basic HAR structure
            if not isinstance(har_data, dict):
                return False

            if "log" not in har_data:
                return False

            log = har_data["log"]
            if not isinstance(log, dict):
                return False

            # Check required log fields
            required_fields = ["version", "creator", "entries"]
            for field in required_fields:
                if field not in log:
                    return False

            # Check version
            if not isinstance(log["version"], str):
                return False

            # Check creator
            creator = log["creator"]
            if not isinstance(creator, dict) or "name" not in creator:
                return False

            # Check entries
            entries = log["entries"]
            if not isinstance(entries, list):
                return False

            # Validate each entry has required fields
            for entry in entries:
                if not isinstance(entry, dict):
                    return False

                required_entry_fields = [
                    "startedDateTime",
                    "time",
                    "request",
                    "response",
                    "cache",
                    "timings",
                ]
                for field in required_entry_fields:
                    if field not in entry:
                        return False

                # Basic request validation
                request = entry["request"]
                if not isinstance(request, dict):
                    return False

                required_request_fields = [
                    "method",
                    "url",
                    "httpVersion",
                    "headers",
                    "queryString",
                    "cookies",
                    "headersSize",
                    "bodySize",
                ]
                for field in required_request_fields:
                    if field not in request:
                        return False

                # Basic response validation
                response = entry["response"]
                if not isinstance(response, dict):
                    return False

                required_response_fields = [
                    "status",
                    "statusText",
                    "httpVersion",
                    "headers",
                    "cookies",
                    "content",
                    "redirectURL",
                    "headersSize",
                    "bodySize",
                ]
                for field in required_response_fields:
                    if field not in response:
                        return False

            # Try to parse with harfile library as additional validation
            har_io = StringIO(content)
            harfile.HarFile(har_io)

            return True

        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            return False
