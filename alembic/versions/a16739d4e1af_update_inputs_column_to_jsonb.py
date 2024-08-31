"""Update inputs column to JSONB

Revision ID: a16739d4e1af
Revises: 59e6ebcfc0cd
Create Date: 2024-08-30 22:21:37.112805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a16739d4e1af'
down_revision: Union[str, None] = '59e6ebcfc0cd'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('sequences', 'inputs',
               existing_type=sa.VARCHAR(),
               type_=postgresql.JSONB(),
               postgresql_using='inputs::jsonb',
               existing_nullable=True)

def downgrade():
    op.alter_column('sequences', 'inputs',
               existing_type=postgresql.JSONB(),
               type_=sa.VARCHAR(),
               existing_nullable=True)