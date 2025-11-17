"""Create robot state table

Revision ID: e92812b07fe8
Revises:
Create Date: 2025-11-17 12:38:45.581082

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "e92812b07fe8"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "persistent_robot_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("robot_id", sa.String(length=64), nullable=False),
        sa.Column("is_maintenance_mode", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("persistent_robot_state")
