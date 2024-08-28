"""Add sent and sent_at columns to emails table

Revision ID: b352902318c9
Revises: 995e700fef1b
Create Date: 2024-08-28 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b352902318c9'
down_revision = '995e700fef1b'
branch_labels = None
depends_on = None

def upgrade():
    # Check if 'sent' column exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns('emails')
    column_names = [c['name'] for c in columns]

    if 'sent' not in column_names:
        op.add_column('emails', sa.Column('sent', sa.Boolean(), nullable=True, server_default='false'))
    
    if 'sent_at' not in column_names:
        op.add_column('emails', sa.Column('sent_at', sa.DateTime(), nullable=True))

def downgrade():
    # We don't want to drop these columns in case they existed before this migration
    pass
