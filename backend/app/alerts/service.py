from __future__ import annotations
from uuid import uuid4
from pydantic import BaseModel, Field
from ..engine.alerts import CrossingStateMachine

class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    metric: str = 'price'
    threshold: float
    direction: str = 'up'
    enabled: bool = True

class AlertService:
    def __init__(self): self.alerts: dict[str, Alert] = {}; self.state = CrossingStateMachine()
    def create(self, payload: dict) -> Alert:
        alert = Alert.model_validate(payload)
        if alert.direction not in ('up', 'down'): raise ValueError('direction must be up or down')
        self.alerts[alert.id] = alert; return alert
    def evaluate(self, symbol: str, metric: str, value: float) -> list[Alert]:
        fired=[]
        for alert in self.alerts.values():
            if alert.enabled and alert.symbol.upper() == symbol.upper() and alert.metric == metric and self.state.evaluate(alert.id, value, alert.threshold, alert.direction): fired.append(alert)
        return fired

alerts = AlertService()
