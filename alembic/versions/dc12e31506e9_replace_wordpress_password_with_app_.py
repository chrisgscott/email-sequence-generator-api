"""replace wordpress_password with app_password

Revision ID: dc12e31506e9
Revises: daf85cfcfe6e
Create Date: 2024-09-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'dc12e31506e9'
down_revision = 'daf85cfcfe6e'
branch_labels = None
depends_on = None

def upgrade():
    # Check if the column exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns('api_keys')
    column_names = [c['name'] for c in columns]

    if 'wordpress_password' not in column_names:
        # If the column doesn't exist, create it
        op.add_column('api_keys', sa.Column('wordpress_password', sa.String(), nullable=True))

    # Now rename the column
    op.alter_column('api_keys', 'wordpress_password', new_column_name='wordpress_app_password')

def downgrade():
    op.alter_column('api_keys', 'wordpress_app_password', new_column_name='wordpress_password')