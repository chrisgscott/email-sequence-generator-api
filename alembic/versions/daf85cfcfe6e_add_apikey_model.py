"""Add APIKey model

Revision ID: daf85cfcfe6e
Revises: b2c997a0134a
Create Date: 2024-09-16 14:08:46.599178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'daf85cfcfe6e'
down_revision: Union[str, None] = 'b2c997a0134a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('api_keys', 'key',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=True))
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_column('users', 'is_superuser')
    op.alter_column('api_keys', 'key',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###