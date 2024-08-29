"""Add is_active column to sequences table

Revision ID: 99c5455a9789
Revises: 178ecd991557
Create Date: 2024-08-29 13:28:10.067504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '99c5455a9789'
down_revision: Union[str, None] = '178ecd991557'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sequences', sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')))

def downgrade() -> None:
    op.drop_column('sequences', 'is_active')