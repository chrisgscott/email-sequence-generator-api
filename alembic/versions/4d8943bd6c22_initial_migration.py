"""Initial migration

Revision ID: 4d8943bd6c22
Revises: 
Create Date: 2024-09-01 12:42:45.134793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4d8943bd6c22'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('emails', sa.Column('sent_to_brevo', sa.Boolean(), nullable=True))
    op.add_column('emails', sa.Column('sent_to_brevo_at', sa.DateTime(), nullable=True))
    op.add_column('emails', sa.Column('brevo_message_id', sa.String(), nullable=True))
    op.drop_column('emails', 'sent')
    op.drop_column('emails', 'sent_at')
    op.add_column('sequences', sa.Column('form_id', sa.String(), nullable=True))
    op.add_column('sequences', sa.Column('brevo_list_id', sa.Integer(), nullable=True))
    op.add_column('sequences', sa.Column('total_emails', sa.Integer(), nullable=True))
    op.add_column('sequences', sa.Column('days_between_emails', sa.Integer(), nullable=True))
    op.add_column('sequences', sa.Column('email_structure', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('sequences', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.add_column('sequences', sa.Column('next_email_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('sequences', sa.Column('progress', sa.Integer(), nullable=True))
    op.add_column('sequences', sa.Column('status', sa.String(), nullable=True))
    op.add_column('sequences', sa.Column('error_message', sa.String(), nullable=True))
    op.add_column('sequences', sa.Column('preferred_time', sa.Time(), nullable=False))
    op.add_column('sequences', sa.Column('timezone', sa.String(), nullable=False))
    op.alter_column('sequences', 'inputs',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               type_=postgresql.JSONB(astext_type=sa.Text()),
               existing_nullable=True)
    op.drop_index('ix_sequences_topic', table_name='sequences')
    op.create_index(op.f('ix_sequences_form_id'), 'sequences', ['form_id'], unique=False)
    op.drop_column('sequences', 'updated_at')
    op.drop_column('sequences', 'created_at')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sequences', sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=True))
    op.add_column('sequences', sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_sequences_form_id'), table_name='sequences')
    op.create_index('ix_sequences_topic', 'sequences', ['topic'], unique=False)
    op.alter_column('sequences', 'inputs',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               type_=postgresql.JSON(astext_type=sa.Text()),
               existing_nullable=True)
    op.drop_column('sequences', 'timezone')
    op.drop_column('sequences', 'preferred_time')
    op.drop_column('sequences', 'error_message')
    op.drop_column('sequences', 'status')
    op.drop_column('sequences', 'progress')
    op.drop_column('sequences', 'next_email_date')
    op.drop_column('sequences', 'is_active')
    op.drop_column('sequences', 'email_structure')
    op.drop_column('sequences', 'days_between_emails')
    op.drop_column('sequences', 'total_emails')
    op.drop_column('sequences', 'brevo_list_id')
    op.drop_column('sequences', 'form_id')
    op.add_column('emails', sa.Column('sent_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('emails', sa.Column('sent', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_column('emails', 'brevo_message_id')
    op.drop_column('emails', 'sent_to_brevo_at')
    op.drop_column('emails', 'sent_to_brevo')
    # ### end Alembic commands ###
