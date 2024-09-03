"""Add user table and update api_key table

Revision ID: e588a00a2767
Revises: 292e7a2d7082
Create Date: 2024-09-03 09:13:42.206772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'e588a00a2767'
down_revision: Union[str, None] = '292e7a2d7082'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table if it doesn't exist
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if 'users' not in tables:
        op.create_table('users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('hashed_password', sa.String(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Add user_id column to api_keys table if it doesn't exist
    if 'user_id' not in [c['name'] for c in inspector.get_columns('api_keys')]:
        op.add_column('api_keys', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint if it doesn't exist
    fks = inspector.get_foreign_keys('api_keys')
    if not any(fk['referred_table'] == 'users' for fk in fks):
        op.create_foreign_key(None, 'api_keys', 'users', ['user_id'], ['id'])

    # Create index on api_keys.id if it doesn't exist
    if 'ix_api_keys_id' not in [i['name'] for i in inspector.get_indexes('api_keys')]:
        op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)


def downgrade() -> None:
    # We'll keep the downgrade function as is, but be cautious when using it
    # as it might try to drop tables or columns that weren't created by this migration
    op.drop_constraint(None, 'api_keys', type_='foreignkey')
    op.drop_column('api_keys', 'user_id')
    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')