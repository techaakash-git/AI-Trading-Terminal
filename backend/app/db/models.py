from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .database import Base

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime

class CandleRecord(Base):
    __tablename__ = 'market_candles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    __table_args__ = (
        UniqueConstraint('symbol','timeframe','time', name='uq_market_candle'),
        Index('ix_market_candles_lookup','symbol','timeframe','time'),
    )

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(32), nullable=False)  # price, rsi, macd, etc
    condition_value: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # up, down, cross_up, cross_down
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, default='1h')
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notification_channels: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of channels
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    fired_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_alerts_symbol_enabled', 'symbol', 'enabled'),
        Index('ix_alerts_created_at', 'created_at'),
    )

class AlertHistory(Base):
    __tablename__ = 'alert_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(36), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_value: Mapped[float] = mapped_column(Float, nullable=False)
    condition_value: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notification_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_channels: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index('ix_alert_history_alert_id', 'alert_id'),
        Index('ix_alert_history_fired_at', 'fired_at'),
        Index('ix_alert_history_symbol', 'symbol'),
    )
