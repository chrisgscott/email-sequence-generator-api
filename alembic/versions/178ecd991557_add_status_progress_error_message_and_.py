"""Add status, progress, error_message, and next_email_date to Sequence model

Revision ID: 178ecd991557
Revises: 7d90d79554bb
Create Date: 2024-08-29 06:58:57.328536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '178ecd991557'
down_revision: Union[str, None] = '7d90d79554bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###