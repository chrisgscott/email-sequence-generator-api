"""Add support for Pexels

Revision ID: ee1017abe142
Revises: 7df62c6a1bf1
Create Date: 2024-09-24 12:33:26.785662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee1017abe142'
down_revision: Union[str, None] = '7df62c6a1bf1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('emails', sa.Column('image_url', sa.String(), nullable=True))
    op.add_column('emails', sa.Column('photographer', sa.String(), nullable=True))
    op.add_column('emails', sa.Column('pexels_url', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('emails', 'pexels_url')
    op.drop_column('emails', 'photographer')
    op.drop_column('emails', 'image_url')
    # ### end Alembic commands ###
