"""Add unique constraint to emails table

Revision ID: 60c3fa099af5
Revises: 7705845822f4
Create Date: 2024-08-28 15:06:50.636069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60c3fa099af5'
down_revision: Union[str, None] = '7705845822f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_unique_constraint('uq_email_id_sent', 'emails', ['id', 'sent'])

def downgrade():
    op.drop_constraint('uq_email_id_sent', 'emails', type_='unique')