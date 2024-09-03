"""Add APIKey table

Revision ID: 292e7a2d7082
Revises: acd4e2187d64
Create Date: 2024-09-03 08:33:00.961460

"""
from alembic import op
import sqlalchemy as sa
from typing import Union, Sequence  # Add this line

# revision identifiers, used by Alembic.
revision: str = '292e7a2d7082'
down_revision: Union[str, None] = 'acd4e2187d64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key'), 'api_keys', ['key'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_api_keys_key'), table_name='api_keys')
    op.drop_table('api_keys')