"""add_user_model_and_auth

Creates the ``users`` table backing the Phase 12 auth baseline. If the table
was already created at runtime by ``init_db``'s ``create_all`` (e.g. in an
existing dev DB), the upgrade is effectively a no-op for that table.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b93b7d94b3ff'
down_revision = '24980c84f250'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('username', name='uq_users_username'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )

def downgrade():
    op.drop_table('users')