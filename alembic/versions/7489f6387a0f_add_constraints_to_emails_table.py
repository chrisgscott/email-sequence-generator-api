"""Add constraints to emails table

Revision ID: 7489f6387a0f
Revises: 60c3fa099af5
Create Date: 2024-08-28 17:25:14.333987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7489f6387a0f'
down_revision: Union[str, None] = '60c3fa099af5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add new columns
    op.add_column('emails', sa.Column('sent_to_brevo', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('emails', sa.Column('sent_to_brevo_at', sa.DateTime(), nullable=True))
    op.add_column('emails', sa.Column('brevo_message_id', sa.String(), nullable=True))

    # Add constraints
    op.create_unique_constraint('uq_email_sent_to_brevo', 'emails', ['id', 'sent_to_brevo'])
    op.create_unique_constraint('uq_email_brevo_message_id', 'emails', ['brevo_message_id'])

def downgrade():
    # Remove constraints
    op.drop_constraint('uq_email_sent_to_brevo', 'emails', type_='unique')
    op.drop_constraint('uq_email_brevo_message_id', 'emails', type_='unique')

    # Remove columns
    op.drop_column('emails', 'brevo_message_id')
    op.drop_column('emails', 'sent_to_brevo_at')
    op.drop_column('emails', 'sent_to_brevo')