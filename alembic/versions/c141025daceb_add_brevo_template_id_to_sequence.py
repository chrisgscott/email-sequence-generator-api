"""Add brevo_template_id to Sequence

Revision ID: c141025daceb
Revises: e588a00a2767
Create Date: 2024-09-16 07:54:58.501205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c141025daceb'
down_revision: Union[str, None] = 'e588a00a2767'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sequences', sa.Column('brevo_template_id', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('sequences', 'brevo_template_id')
    # ### end Alembic commands ###
