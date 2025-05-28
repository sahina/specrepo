import logging
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models import APISpecification, User
from app.schemas import APISpecificationCreate, APISpecificationFilters, APISpecificationUpdate

logger = logging.getLogger(__name__)


class APISpecificationService:
    """Service class for API Specification CRUD operations."""

    @staticmethod
    def create_specification(
        db: Session, spec_data: APISpecificationCreate, user: User
    ) -> APISpecification:
        """
        Create a new API specification.

        Args:
            db: Database session
            spec_data: API specification data
            user: Owner user

        Returns:
            Created API specification
        """
        db_spec = APISpecification(
            name=spec_data.name,
            version_string=spec_data.version_string,
            openapi_content=spec_data.openapi_content,
            user_id=user.id,
        )

        db.add(db_spec)
        db.commit()
        db.refresh(db_spec)

        logger.info(
            f"Created API specification '{spec_data.name}' "
            f"v{spec_data.version_string} for user {user.username}"
        )
        return db_spec

    @staticmethod
    def get_specification(db: Session, spec_id: int, user: User) -> Optional[APISpecification]:
        """
        Get an API specification by ID.

        Args:
            db: Database session
            spec_id: Specification ID
            user: Current user

        Returns:
            API specification if found and accessible, None otherwise
        """
        return (
            db.query(APISpecification)
            .filter(
                and_(
                    APISpecification.id == spec_id,
                    APISpecification.user_id == user.id,
                )
            )
            .first()
        )

    @staticmethod
    def get_specifications(
        db: Session, user: User, filters: APISpecificationFilters
    ) -> Tuple[List[APISpecification], int]:
        """
        Get paginated list of API specifications with filtering and sorting.

        Args:
            db: Database session
            user: Current user
            filters: Filtering and pagination parameters

        Returns:
            Tuple of (specifications list, total count)
        """
        query = db.query(APISpecification).filter(APISpecification.user_id == user.id)

        # Apply filters
        if filters.name:
            query = query.filter(APISpecification.name.ilike(f"%{filters.name}%"))

        if filters.version_string:
            query = query.filter(APISpecification.version_string == filters.version_string)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        try:
            sort_column = getattr(APISpecification, filters.sort_by)
            if filters.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
        except AttributeError:
            # This should not happen if Pydantic validation is working
            # correctly,
            # but adding as a safety net
            logger.error(f"Invalid sort field: {filters.sort_by}")
            raise ValueError(f"Invalid sort field: {filters.sort_by}")

        # Apply pagination
        offset = (filters.page - 1) * filters.size
        specifications = query.offset(offset).limit(filters.size).all()

        return specifications, total

    @staticmethod
    def update_specification(
        db: Session,
        spec_id: int,
        spec_data: APISpecificationUpdate,
        user: User,
    ) -> Optional[APISpecification]:
        """
        Update an API specification.

        Args:
            db: Database session
            spec_id: Specification ID
            spec_data: Updated specification data
            user: Current user

        Returns:
            Updated API specification if found and accessible, None otherwise
        """
        db_spec = APISpecificationService.get_specification(db, spec_id, user)

        if not db_spec:
            return None

        # Update only provided fields
        update_data = spec_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_spec, field, value)

        db.commit()
        db.refresh(db_spec)

        logger.info(f"Updated API specification {spec_id} for user {user.username}")
        return db_spec

    @staticmethod
    def delete_specification(db: Session, spec_id: int, user: User) -> bool:
        """
        Delete an API specification.

        Args:
            db: Database session
            spec_id: Specification ID
            user: Current user

        Returns:
            True if deleted successfully, False if not found or not accessible
        """
        db_spec = APISpecificationService.get_specification(db, spec_id, user)

        if not db_spec:
            return False

        db.delete(db_spec)
        db.commit()

        logger.info(f"Deleted API specification {spec_id} for user {user.username}")
        return True

    @staticmethod
    def check_name_version_exists(
        db: Session,
        name: str,
        version_string: str,
        user: User,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Check if an API specification with the same name and version already
        exists for the user.

        Args:
            db: Database session
            name: Specification name
            version_string: Version string
            user: Current user
            exclude_id: ID to exclude from check (for updates)

        Returns:
            True if exists, False otherwise
        """
        query = db.query(APISpecification).filter(
            and_(
                APISpecification.name == name,
                APISpecification.version_string == version_string,
                APISpecification.user_id == user.id,
            )
        )

        if exclude_id:
            query = query.filter(APISpecification.id != exclude_id)

        return query.first() is not None
