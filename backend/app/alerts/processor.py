"""Real-time alert evaluation processor."""
import asyncio
import json
import logging
from typing import Optional
from ..db.database import async_session_maker
from ..market.realtime import hub
from .service import alerts

logger = logging.getLogger(__name__)

class AlertProcessor:
    """Processes market data in real-time and evaluates alerts."""

    def __init__(self):
        self.running = False
        self.tasks: list[asyncio.Task] = []

    async def start(self):
        """Start the alert processor."""
        if self.running:
            logger.warning("AlertProcessor is already running")
            return

        self.running = True
        logger.info("AlertProcessor started")

        # Start processors for common symbols
        symbols = ['BTCUSDT', 'XAUUSD']
        for symbol in symbols:
            task = asyncio.create_task(self._process_symbol(symbol))
            self.tasks.append(task)

    async def stop(self):
        """Stop the alert processor."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping AlertProcessor...")

        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        logger.info("AlertProcessor stopped")

    async def _process_symbol(self, symbol: str):
        """Process alerts for a specific symbol."""
        logger.info(f"Starting alert processing for {symbol}")

        while self.running:
            try:
                # Subscribe to market updates for this symbol
                pubsub = await hub.subscribe(symbol, '1m')

                try:
                    while self.running:
                        message = await pubsub.get_message(timeout=5)

                        if message and message.get('data'):
                            try:
                                data = json.loads(message['data'])
                                await self._evaluate_tick(symbol, data)
                            except json.JSONDecodeError:
                                logger.error(f"Failed to decode message for {symbol}")
                            except Exception as e:
                                logger.error(f"Error evaluating tick for {symbol}: {e}")

                        await asyncio.sleep(0.1)  # Small delay to prevent tight loop

                finally:
                    await pubsub.close()

            except Exception as e:
                logger.error(f"Error in alert processor for {symbol}: {e}")
                if self.running:
                    await asyncio.sleep(5)  # Wait before reconnecting

    async def _evaluate_tick(self, symbol: str, tick_data: dict):
        """Evaluate alerts against a new tick."""
        try:
            # Extract price from tick data
            price = tick_data.get('close') or tick_data.get('price')
            if price is None:
                return

            # Create a database session
            async with async_session_maker() as db:
                # Evaluate price alerts
                fired_alerts = await alerts.evaluate(symbol, 'price', float(price), db)

                # If any alerts fired, publish to Redis for WebSocket clients
                if fired_alerts:
                    for fired in fired_alerts:
                        alert_notification = {
                            'alert_id': fired.alert_id,
                            'symbol': fired.symbol,
                            'condition_type': fired.condition_type,
                            'trigger_value': fired.trigger_value,
                            'condition_value': fired.condition_value,
                            'direction': fired.direction,
                            'fired_at': fired.fired_at.isoformat(),
                            'message': f"{symbol} {fired.condition_type} crossed {fired.direction} {fired.condition_value}"
                        }

                        # Publish to Redis for WebSocket distribution
                        await hub.publish('ALERTS', 'notifications', alert_notification)

                        logger.info(f"Alert fired: {alert_notification['message']}")

        except Exception as e:
            logger.error(f"Error evaluating tick for {symbol}: {e}")


# Global instance
processor = AlertProcessor()
