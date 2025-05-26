import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import MockConfiguration, User

logger = logging.getLogger(__name__)


class MockConfigurationService:
    """Service for managing mock configurations."""

    @staticmethod
    def create_mock_configuration(
        db: Session,
        api_specification_id: int,
        wiremock_mapping_json: dict,
        status: str = "active",
        user: User = None,
    ) -> MockConfiguration:
        """
        Create a new mock configuration.

        Args:
            db: Database session
            api_specification_id: ID of the API specification
            wiremock_mapping_json: WireMock mapping configuration
            status: Status of the mock configuration
            user: User creating the configuration (for authorization)

        Returns:
            Created MockConfiguration instance
        """
        mock_config = MockConfiguration(
            api_specification_id=api_specification_id,
            wiremock_mapping_json=wiremock_mapping_json,
            status=status,
            deployed_at=datetime.utcnow(),
        )

        db.add(mock_config)
        db.commit()
        db.refresh(mock_config)

        logger.info(
            f"Created mock configuration {mock_config.id} for API specification {api_specification_id}"
        )

        return mock_config

    @staticmethod
    def get_mock_configuration(
        db: Session, config_id: int, user: User = None
    ) -> Optional[MockConfiguration]:
        """
        Get a mock configuration by ID.

        Args:
            db: Database session
            config_id: ID of the mock configuration
            user: User requesting the configuration (for authorization)

        Returns:
            MockConfiguration instance or None if not found
        """
        return (
            db.query(MockConfiguration)
            .filter(MockConfiguration.id == config_id)
            .first()
        )

    @staticmethod
    def get_mock_configurations_by_api_spec(
        db: Session, api_specification_id: int, user: User = None
    ) -> List[MockConfiguration]:
        """
        Get all mock configurations for an API specification.

        Args:
            db: Database session
            api_specification_id: ID of the API specification
            user: User requesting the configurations (for authorization)

        Returns:
            List of MockConfiguration instances
        """
        return (
            db.query(MockConfiguration)
            .filter(
                MockConfiguration.api_specification_id == api_specification_id
            )
            .all()
        )

    @staticmethod
    def get_active_mock_configurations(
        db: Session, user: User = None
    ) -> List[MockConfiguration]:
        """
        Get all active mock configurations.

        Args:
            db: Database session
            user: User requesting the configurations (for authorization)

        Returns:
            List of active MockConfiguration instances
        """
        return (
            db.query(MockConfiguration)
            .filter(MockConfiguration.status == "active")
            .all()
        )

    @staticmethod
    def update_mock_configuration_status(
        db: Session,
        config_id: int,
        status: str,
        user: User = None,
    ) -> Optional[MockConfiguration]:
        """
        Update the status of a mock configuration.

        Args:
            db: Database session
            config_id: ID of the mock configuration
            status: New status
            user: User updating the configuration (for authorization)

        Returns:
            Updated MockConfiguration instance or None if not found
        """
        mock_config = (
            db.query(MockConfiguration)
            .filter(MockConfiguration.id == config_id)
            .first()
        )

        if mock_config:
            mock_config.status = status
            db.commit()
            db.refresh(mock_config)

            logger.info(
                f"Updated mock configuration {config_id} status to {status}"
            )

        return mock_config

    @staticmethod
    def delete_mock_configuration(
        db: Session, config_id: int, user: User = None
    ) -> bool:
        """
        Delete a mock configuration.

        Args:
            db: Database session
            config_id: ID of the mock configuration
            user: User deleting the configuration (for authorization)

        Returns:
            True if deleted, False if not found
        """
        mock_config = (
            db.query(MockConfiguration)
            .filter(MockConfiguration.id == config_id)
            .first()
        )

        if mock_config:
            db.delete(mock_config)
            db.commit()

            logger.info(f"Deleted mock configuration {config_id}")
            return True

        return False

    @staticmethod
    def reset_all_mock_configurations(db: Session, user: User = None) -> int:
        """
        Reset all mock configurations by setting their status to 'inactive'.

        Args:
            db: Database session
            user: User resetting the configurations (for authorization)

        Returns:
            Number of configurations reset
        """
        updated_count = (
            db.query(MockConfiguration)
            .filter(MockConfiguration.status == "active")
            .update({"status": "inactive"})
        )

        db.commit()

        logger.info(f"Reset {updated_count} mock configurations")

        return updated_count
