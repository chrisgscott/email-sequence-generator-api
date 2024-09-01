"""Initial migration

Revision ID: 7736e8bf8f76
Revises: 
Create Date: 2024-09-01 13:13:40.051051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7736e8bf8f76'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add preferred_time column as nullable
    op.add_column('sequences', sa.Column('preferred_time', sa.Time(), nullable=True))
    # Add timezone column as nullable
    op.add_column('sequences', sa.Column('timezone', sa.String(), nullable=True))
    
    # Update existing rows with default values
    op.execute("UPDATE sequences SET preferred_time = '09:00:00' WHERE preferred_time IS NULL")
    op.execute("UPDATE sequences SET timezone = 'UTC' WHERE timezone IS NULL")
    
    # Make columns non-nullable
    op.alter_column('sequences', 'preferred_time', nullable=False)
    op.alter_column('sequences', 'timezone', nullable=False)


def downgrade() -> None:
    op.drop_column('sequences', 'timezone')
    op.drop_column('sequences', 'preferred_time')
