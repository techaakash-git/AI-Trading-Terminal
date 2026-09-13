"""Add alert tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '24980c84f250'
down_revision = '0001_market_candles'
branch_labels = None
depends_on = None

def upgrade():
    # Create alerts table
    op.create_table('alerts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('condition_type', sa.String(length=32), nullable=False),
        sa.Column('condition_value', sa.Float(), nullable=False),
        sa.Column('direction', sa.String(length=8), nullable=False),
        sa.Column('timeframe', sa.String(length=8), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('notification_channels', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fired_count', sa.Integer(), nullable=False),
        sa.Column('last_fired_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alerts_symbol_enabled', 'alerts', ['symbol', 'enabled'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])

    # Create alert_history table
    op.create_table('alert_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.String(length=36), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('condition_type', sa.String(length=32), nullable=False),
        sa.Column('trigger_value', sa.Float(), nullable=False),
        sa.Column('condition_value', sa.Float(), nullable=False),
        sa.Column('direction', sa.String(length=8), nullable=False),
        sa.Column('fired_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('notification_sent', sa.Boolean(), nullable=False),
        sa.Column('notification_channels', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_history_alert_id', 'alert_history', ['alert_id'])
    op.create_index('ix_alert_history_fired_at', 'alert_history', ['fired_at'])
    op.create_index('ix_alert_history_symbol', 'alert_history', ['symbol'])

def downgrade():
    # Drop alert_history table
    op.drop_index('ix_alert_history_symbol', table_name='alert_history')
    op.drop_index('ix_alert_history_fired_at', table_name='alert_history')
    op.drop_index('ix_alert_history_alert_id', table_name='alert_history')
    op.drop_table('alert_history')

    # Drop alerts table
    op.drop_index('ix_alerts_created_at', table_name='alerts')
    op.drop_index('ix_alerts_symbol_enabled', table_name='alerts')
    op.drop_table('alerts')
