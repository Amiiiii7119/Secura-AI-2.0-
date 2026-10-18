"""001_initial_secura_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-18 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=256), nullable=False),
        sa.Column('salt', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=64), nullable=False, server_default='Forensic Analyst'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. session_tokens table
    op.create_table(
        'session_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=64), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_tokens_id'), 'session_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_session_tokens_token'), 'session_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_session_tokens_user_id'), 'session_tokens', ['user_id'], unique=False)

    # 3. analysis_audits table
    op.create_table(
        'analysis_audits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('media_type', sa.String(length=32), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('predicted_label', sa.String(length=64), nullable=False),
        sa.Column('confidence_pct', sa.Float(), nullable=False),
        sa.Column('evidence_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_audits_id'), 'analysis_audits', ['id'], unique=False)
    op.create_index(op.f('ix_analysis_audits_user_id'), 'analysis_audits', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_audits_user_id'), table_name='analysis_audits')
    op.drop_index(op.f('ix_analysis_audits_id'), table_name='analysis_audits')
    op.drop_table('analysis_audits')

    op.drop_index(op.f('ix_session_tokens_user_id'), table_name='session_tokens')
    op.drop_index(op.f('ix_session_tokens_token'), table_name='session_tokens')
    op.drop_index(op.f('ix_session_tokens_id'), table_name='session_tokens')
    op.drop_table('session_tokens')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
