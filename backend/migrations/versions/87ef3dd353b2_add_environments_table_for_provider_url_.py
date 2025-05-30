"""Add environments table for provider URL management

Revision ID: 87ef3dd353b2
Revises: 118b96c3e5fe
Create Date: 2025-05-28 16:43:29.167207

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "87ef3dd353b2"
down_revision: Union[str, None] = "118b96c3e5fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "environments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("environment_type", sa.String(), nullable=True),
        sa.Column("is_active", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_environments_id"), "environments", ["id"], unique=False)
    op.alter_column(
        "har_uploads",
        "raw_content",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=sa.String(),
        existing_nullable=False,
    )
    op.add_column("validation_runs", sa.Column("environment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_validation_runs_environment_id",
        "validation_runs",
        "environments",
        ["environment_id"],
        ["id"],
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###

    # Drop the foreign key constraint first
    op.drop_constraint("fk_validation_runs_environment_id", "validation_runs", type_="foreignkey")

    # Drop the environment_id column
    op.drop_column("validation_runs", "environment_id")

    # Drop the environments table
    op.drop_table("environments")

    # Alter the har_uploads column type with explicit USING clause
    op.execute("ALTER TABLE har_uploads ALTER COLUMN raw_content TYPE JSON USING raw_content::json")

    # ### end Alembic commands ###
