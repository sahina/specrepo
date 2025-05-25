import pytest
from alembic import command
from alembic.config import Config
from conftest import ALEMBIC_INI_PATH, DATABASE_URL
from sqlalchemy import text


@pytest.fixture(scope="module")
def alembic_config_for_migration_test():
    cfg = Config(ALEMBIC_INI_PATH)
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg


def test_single_migration_apply_downgrade_apply(
    alembic_config_for_migration_test, db_engine, setup_test_database
):
    """
    Tests that the initial migration can be applied, fully downgraded, and then reapplied.
    Relies on setup_test_database having already applied it once.
    """
    cfg = alembic_config_for_migration_test

    # 1. Verify tables exist (confirming setup_test_database worked)
    with db_engine.connect() as connection:
        result = connection.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"
            )
        )
        assert result.scalar_one() is True, (
            "'users' table should exist after session setup."
        )

    # 2. Downgrade to base
    command.downgrade(cfg, "base")
    with db_engine.connect() as connection:
        result = connection.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"
            )
        )
        assert result.scalar_one() is False, (
            "'users' table should NOT exist after downgrading to base."
        )

    # 3. Upgrade back to head
    command.upgrade(cfg, "head")
    with db_engine.connect() as connection:
        result = connection.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"
            )
        )
        assert result.scalar_one() is True, (
            "'users' table should exist after re-upgrading to head."
        )
