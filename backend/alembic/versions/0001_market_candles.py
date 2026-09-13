"""create market candles"""
from alembic import op
import sqlalchemy as sa
revision='0001_market_candles'; down_revision=None; branch_labels=None; depends_on=None
def upgrade():
    op.create_table('market_candles',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('timeframe', sa.String(8), nullable=False), sa.Column('time', sa.BigInteger(), nullable=False),
        sa.Column('open', sa.Float(), nullable=False), sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False), sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False), sa.UniqueConstraint('symbol','timeframe','time',name='uq_market_candle'))
    op.create_index('ix_market_candles_lookup','market_candles',['symbol','timeframe','time'])
def downgrade():
    op.drop_index('ix_market_candles_lookup', table_name='market_candles'); op.drop_table('market_candles')
