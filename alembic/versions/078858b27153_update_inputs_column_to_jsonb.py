"""Update inputs column to JSONB

Revision ID: 078858b27153
Revises: a16739d4e1af
Create Date: 2024-08-30 22:24:51.869973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '078858b27153'
down_revision: Union[str, None] = 'a16739d4e1af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('sequences', 'email_structure',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True)
    op.drop_index('ix_sequences_recipient_email', table_name='sequences')
    op.drop_index('ix_sequences_topic', table_name='sequences')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('ix_sequences_topic', 'sequences', ['topic'], unique=False)
    op.create_index('ix_sequences_recipient_email', 'sequences', ['recipient_email'], unique=False)
    op.alter_column('sequences', 'email_structure',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=True)
    # ### end Alembic commands ###
