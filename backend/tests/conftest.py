import os
import sys

# Add the 'backend' directory (parent of 'tests') to the Python path
# This allows pytest to find the 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from alembic import command
from alembic.config import Config
from app.db.base_class import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import text

# Determine the database URL
# If TEST_DATABASE_URL is set, use it, otherwise construct from alembic.ini defaults (which should match docker-compose)
DEFAULT_DB_URL = "postgresql://user:password@localhost:5432/appdb_test"
DATABASE_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_DB_URL)

# Alembic config
ALEMBIC_INI_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "alembic.ini"
)


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def setup_test_database(db_engine):
    """Creates all tables using Alembic before tests and drops them afterwards."""
    alembic_cfg = Config(ALEMBIC_INI_PATH)
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

    # Ensure the alembic_version table is also cleared for a truly fresh start for migrations
    with db_engine.connect() as connection:
        try:
            connection.execute(text("TRUNCATE TABLE alembic_version;"))
            connection.commit()
        except Exception as e:
            print(
                f"Note: Could not truncate alembic_version (may not exist yet or other issue): {e}"
            )
            connection.rollback()  # Rollback if truncate failed for any reason

    Base.metadata.drop_all(bind=db_engine)

    command.upgrade(alembic_cfg, "head")

    yield

    Base.metadata.drop_all(bind=db_engine)


@pytest.fixture(scope="function")
def db_session(db_engine, setup_test_database):
    """Yields a SQLAlchemy session for a test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# Fixture to make models available to tests if needed
@pytest.fixture(scope="session")
def models_fixture():
    from app import models as app_models

    return app_models
