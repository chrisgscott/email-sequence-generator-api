"""merge heads

Revision ID: merge_heads_manual
Revises: d08c62462b8d, dc12e31506e9
Create Date: 2023-09-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_manual'
down_revision = ('d08c62462b8d', 'dc12e31506e9')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass