import logging
from typing import List, Optional, Tuple

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

from app.models import Environment, User
from app.schemas import EnvironmentCreate, EnvironmentFilters, EnvironmentUpdate

logger = logging.getLogger(__name__)


class EnvironmentService:
    """Service class for Environment CRUD operations."""

    @staticmethod
    def create_environment(db: Session, env_data: EnvironmentCreate, user: User) -> Environment:
        """
        Create a new environment.

        Args:
            db: Database session
            env_data: Environment data
            user: Owner user

        Returns:
            Created environment
        """
        db_env = Environment(
            name=env_data.name,
            base_url=env_data.base_url,
            description=env_data.description,
            environment_type=env_data.environment_type,
            user_id=user.id,
        )

        db.add(db_env)
        db.commit()
        db.refresh(db_env)

        logger.info(
            f"Created environment '{env_data.name}' "
            f"({env_data.environment_type}) for user {user.username}"
        )
        return db_env

    @staticmethod
    def get_environment(db: Session, env_id: int, user: User) -> Optional[Environment]:
        """
        Get an environment by ID.

        Args:
            db: Database session
            env_id: Environment ID
            user: Current user

        Returns:
            Environment if found and accessible, None otherwise
        """
        return (
            db.query(Environment)
            .filter(
                and_(
                    Environment.id == env_id,
                    Environment.user_id == user.id,
                    Environment.is_active == "true",
                )
            )
            .first()
        )

    @staticmethod
    def get_environments(
        db: Session, user: User, filters: EnvironmentFilters
    ) -> Tuple[List[Environment], int]:
        """
        Get environments with filtering and pagination.

        Args:
            db: Database session
            user: Current user
            filters: Filter and pagination parameters

        Returns:
            Tuple of (environments list, total count)
        """
        query = db.query(Environment).filter(Environment.user_id == user.id)

        # Apply filters
        if filters.name:
            query = query.filter(Environment.name.ilike(f"%{filters.name}%"))

        if filters.environment_type:
            query = query.filter(Environment.environment_type == filters.environment_type)

        if filters.is_active:
            query = query.filter(Environment.is_active == filters.is_active)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = getattr(Environment, filters.sort_by)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        skip = (filters.page - 1) * filters.size
        environments = query.offset(skip).limit(filters.size).all()

        return environments, total

    @staticmethod
    def update_environment(
        db: Session,
        env_id: int,
        env_data: EnvironmentUpdate,
        user: User,
    ) -> Optional[Environment]:
        """
        Update an environment.

        Args:
            db: Database session
            env_id: Environment ID
            env_data: Updated environment data
            user: Current user

        Returns:
            Updated environment if found and accessible, None otherwise
        """
        db_env = EnvironmentService.get_environment(db, env_id, user)

        if not db_env:
            return None

        # Update only provided fields
        update_data = env_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_env, field, value)

        db.commit()
        db.refresh(db_env)

        logger.info(f"Updated environment {env_id} for user {user.username}")
        return db_env

    @staticmethod
    def delete_environment(db: Session, env_id: int, user: User) -> bool:
        """
        Soft delete an environment (set is_active to false).

        Args:
            db: Database session
            env_id: Environment ID
            user: Current user

        Returns:
            True if deleted successfully, False if not found or not accessible
        """
        db_env = EnvironmentService.get_environment(db, env_id, user)

        if not db_env:
            return False

        db_env.is_active = "false"
        db.commit()

        logger.info(f"Soft deleted environment {env_id} for user {user.username}")
        return True

    @staticmethod
    def check_name_exists(
        db: Session, name: str, user: User, exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if an environment name already exists for the user.

        Args:
            db: Database session
            name: Environment name to check
            user: Current user
            exclude_id: Environment ID to exclude from check (for updates)

        Returns:
            True if name exists, False otherwise
        """
        query = db.query(Environment).filter(
            and_(
                Environment.name == name,
                Environment.user_id == user.id,
                Environment.is_active == "true",
            )
        )

        if exclude_id:
            query = query.filter(Environment.id != exclude_id)

        return query.first() is not None

    @staticmethod
    def get_active_environments(db: Session, user: User) -> List[Environment]:
        """
        Get all active environments for a user.

        Args:
            db: Database session
            user: Current user

        Returns:
            List of active environments
        """
        return (
            db.query(Environment)
            .filter(
                and_(
                    Environment.user_id == user.id,
                    Environment.is_active == "true",
                )
            )
            .order_by(Environment.name)
            .all()
        )
