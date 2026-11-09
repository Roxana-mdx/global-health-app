"""add is_outlier to observations

Revision ID: bfc6908434a7
Revises: edf3ac493aaf
Create Date: 2026-11-09 22:37:23.246819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfc6908434a7'
down_revision: Union[str, Sequence[str], None] = 'edf3ac493aaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "observation",
        sa.Column("is_outlier", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("observation", "is_outlier")
