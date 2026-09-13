from __future__ import annotations
import json
from datetime import datetime
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..engine.alerts import CrossingStateMachine
from ..db.models import Alert as AlertModel, AlertHistory
from ..db.database import get_db

class AlertCreate(BaseModel):
    name: str
    symbol: str
    condition_type: str = 'price'  # price, rsi, macd_signal, ema_cross
    condition_value: float
    direction: str = 'up'  # up, down, cross_up, cross_down
    timeframe: str = '1h'
    notification_channels: list[str] = Field(default_factory=list)

class AlertUpdate(BaseModel):
    name: Optional[str] = None
    condition_value: Optional[float] = None
    direction: Optional[str] = None
    enabled: Optional[bool] = None
    notification_channels: Optional[list[str]] = None

class Alert(BaseModel):
    id: str
    name: str
    symbol: str
    condition_type: str
    condition_value: float
    direction: str
    timeframe: str
    enabled: bool
    notification_channels: list[str]
    created_at: datetime
    updated_at: datetime
    fired_count: int
    last_fired_at: Optional[datetime]

class AlertFired(BaseModel):
    alert_id: str
    symbol: str
    condition_type: str
    trigger_value: float
    condition_value: float
    direction: str
    fired_at: datetime

class AlertService:
    def __init__(self):
        self.state = CrossingStateMachine()
        self._in_memory_alerts: dict[str, Alert] = {}  # Fallback if DB unavailable

    async def create(self, payload: AlertCreate, db: AsyncSession) -> Alert:
        """Create a new alert in the database."""
        if payload.direction not in ('up', 'down', 'cross_up', 'cross_down'):
            raise ValueError('direction must be up, down, cross_up, or cross_down')
        if payload.condition_type not in ('price', 'rsi', 'macd_signal', 'ema_cross'):
            raise ValueError('condition_type must be price, rsi, macd_signal, or ema_cross')

        alert_id = str(uuid4())
        db_alert = AlertModel(
            id=alert_id,
            name=payload.name,
            symbol=payload.symbol.upper(),
            condition_type=payload.condition_type,
            condition_value=payload.condition_value,
            direction=payload.direction,
            timeframe=payload.timeframe,
            enabled=True,
            notification_channels=json.dumps(payload.notification_channels),
            fired_count=0
        )
        db.add(db_alert)
        await db.commit()
        await db.refresh(db_alert)

        return self._model_to_pydantic(db_alert)

    async def get_all(self, db: AsyncSession, symbol: Optional[str] = None, enabled_only: bool = False) -> list[Alert]:
        """Retrieve all alerts, optionally filtered by symbol and enabled status."""
        query = select(AlertModel)
        if symbol:
            query = query.where(AlertModel.symbol == symbol.upper())
        if enabled_only:
            query = query.where(AlertModel.enabled == True)

        result = await db.execute(query.order_by(AlertModel.created_at.desc()))
        return [self._model_to_pydantic(alert) for alert in result.scalars().all()]

    async def get_by_id(self, alert_id: str, db: AsyncSession) -> Optional[Alert]:
        """Retrieve a specific alert by ID."""
        result = await db.execute(select(AlertModel).where(AlertModel.id == alert_id))
        db_alert = result.scalar_one_or_none()
        return self._model_to_pydantic(db_alert) if db_alert else None

    async def update(self, alert_id: str, payload: AlertUpdate, db: AsyncSession) -> Optional[Alert]:
        """Update an existing alert."""
        update_data = payload.model_dump(exclude_unset=True)
        if 'notification_channels' in update_data:
            update_data['notification_channels'] = json.dumps(update_data['notification_channels'])

        if not update_data:
            return await self.get_by_id(alert_id, db)

        await db.execute(
            update(AlertModel)
            .where(AlertModel.id == alert_id)
            .values(**update_data)
        )
        await db.commit()
        return await self.get_by_id(alert_id, db)

    async def delete(self, alert_id: str, db: AsyncSession) -> bool:
        """Delete an alert."""
        result = await db.execute(select(AlertModel).where(AlertModel.id == alert_id))
        db_alert = result.scalar_one_or_none()
        if db_alert:
            await db.delete(db_alert)
            await db.commit()
            return True
        return False

    async def evaluate(self, symbol: str, condition_type: str, value: float, db: AsyncSession) -> list[AlertFired]:
        """Evaluate all enabled alerts for a symbol and condition type."""
        alerts = await self.get_all(db, symbol=symbol, enabled_only=True)
        fired = []

        for alert in alerts:
            if alert.condition_type != condition_type:
                continue

            state_key = f"{alert.id}:{condition_type}"
            if self.state.evaluate(state_key, value, alert.condition_value, alert.direction):
                # Record the firing
                fired_event = AlertFired(
                    alert_id=alert.id,
                    symbol=symbol.upper(),
                    condition_type=condition_type,
                    trigger_value=value,
                    condition_value=alert.condition_value,
                    direction=alert.direction,
                    fired_at=datetime.utcnow()
                )
                fired.append(fired_event)

                # Update alert statistics
                await db.execute(
                    update(AlertModel)
                    .where(AlertModel.id == alert.id)
                    .values(
                        fired_count=AlertModel.fired_count + 1,
                        last_fired_at=datetime.utcnow()
                    )
                )

                # Save to history
                history = AlertHistory(
                    alert_id=alert.id,
                    symbol=symbol.upper(),
                    condition_type=condition_type,
                    trigger_value=value,
                    condition_value=alert.condition_value,
                    direction=alert.direction,
                    notification_sent=False,
                    notification_channels=json.dumps(alert.notification_channels)
                )
                db.add(history)

        if fired:
            await db.commit()

        return fired

    async def get_history(self, db: AsyncSession, alert_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        """Retrieve alert firing history."""
        query = select(AlertHistory).order_by(AlertHistory.fired_at.desc()).limit(limit)
        if alert_id:
            query = query.where(AlertHistory.alert_id == alert_id)

        result = await db.execute(query)
        return [
            {
                'id': h.id,
                'alert_id': h.alert_id,
                'symbol': h.symbol,
                'condition_type': h.condition_type,
                'trigger_value': h.trigger_value,
                'condition_value': h.condition_value,
                'direction': h.direction,
                'fired_at': h.fired_at.isoformat(),
                'notification_sent': h.notification_sent
            }
            for h in result.scalars().all()
        ]

    def _model_to_pydantic(self, db_alert: AlertModel) -> Alert:
        """Convert SQLAlchemy model to Pydantic model."""
        return Alert(
            id=db_alert.id,
            name=db_alert.name,
            symbol=db_alert.symbol,
            condition_type=db_alert.condition_type,
            condition_value=db_alert.condition_value,
            direction=db_alert.direction,
            timeframe=db_alert.timeframe,
            enabled=db_alert.enabled,
            notification_channels=json.loads(db_alert.notification_channels) if db_alert.notification_channels else [],
            created_at=db_alert.created_at,
            updated_at=db_alert.updated_at,
            fired_count=db_alert.fired_count,
            last_fired_at=db_alert.last_fired_at
        )

    # Backward compatibility: in-memory API for tests
    def create_sync(self, payload: dict) -> Alert:
        """Legacy synchronous create for tests."""
        alert_data = AlertCreate.model_validate(payload)
        alert = Alert(
            id=str(uuid4()),
            name=alert_data.name,
            symbol=alert_data.symbol.upper(),
            condition_type=alert_data.condition_type,
            condition_value=alert_data.condition_value,
            direction=alert_data.direction,
            timeframe=alert_data.timeframe,
            enabled=True,
            notification_channels=alert_data.notification_channels,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            fired_count=0,
            last_fired_at=None
        )
        self._in_memory_alerts[alert.id] = alert
        return alert

    def evaluate_sync(self, symbol: str, metric: str, value: float) -> list[Alert]:
        """Legacy synchronous evaluate for tests."""
        fired = []
        for alert in self._in_memory_alerts.values():
            if alert.enabled and alert.symbol.upper() == symbol.upper() and alert.condition_type == metric:
                state_key = f"{alert.id}:{metric}"
                if self.state.evaluate(state_key, value, alert.condition_value, alert.direction):
                    fired.append(alert)
        return fired

alerts = AlertService()
