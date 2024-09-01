"""Add timezone column to sequences

Revision ID: acd4e2187d64
Revises: 7736e8bf8f76
Create Date: 2024-09-01 13:24:59.802831

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'acd4e2187d64'
down_revision = '7736e8bf8f76'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if the column exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns('sequences')
    if 'timezone' not in [c['name'] for c in columns]:
        op.add_column('sequences', sa.Column('timezone', sa.String(), nullable=True))
    
    # Update existing rows with default value
    op.execute("UPDATE sequences SET timezone = 'UTC' WHERE timezone IS NULL")
    
    # Make the column non-nullable if it's not already
    if 'timezone' in [c['name'] for c in columns] and any(c['name'] == 'timezone' and c['nullable'] for c in columns):
        op.alter_column('sequences', 'timezone', nullable=False)

def downgrade() -> None:
    op.drop_column('sequences', 'timezone')