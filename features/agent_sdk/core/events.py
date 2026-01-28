"""
Core Events - NATS event publishing utilities.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import NATS
try:
    import nats
    from nats.aio.client import Client as NATSClient
    HAS_NATS = True
except ImportError:
    HAS_NATS = False
    NATSClient = None


class EventPublisher:
    """
    NATS Event Publisher for PMOVES Agent SDK.

    Publishes events to NATS for observability and coordination.

    Usage:
        publisher = EventPublisher(nats_url="nats://localhost:4222")
        await publisher.connect()
        await publisher.publish("botz.agent.started.v1", {"agent_id": "..."})
        await publisher.disconnect()
    """

    def __init__(self, nats_url: str = "nats://localhost:4222"):
        """
        Initialize Event Publisher.

        Args:
            nats_url: NATS server URL
        """
        self.nats_url = nats_url
        self._client: Optional[NATSClient] = None

    @property
    def connected(self) -> bool:
        """Check if connected to NATS."""
        return self._client is not None and self._client.is_connected

    async def connect(self, require: bool = False) -> bool:
        """
        Connect to NATS server.

        Args:
            require: If True, raise error on connection failure

        Returns:
            True if connected, False otherwise
        """
        if not HAS_NATS:
            if require:
                raise RuntimeError("NATS not installed. Run: pip install nats-py")
            logger.warning("NATS not available - events will be logged only")
            return False

        try:
            self._client = await nats.connect(
                self.nats_url,
                connect_timeout=10,
                reconnect=False,
            )
            logger.info(f"Connected to NATS at {self.nats_url}")
            return True
        except Exception as e:
            if require:
                raise ConnectionError(f"Failed to connect to NATS: {e}")
            logger.warning(f"NATS connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self._client:
            await self._client.close()
            self._client = None

    async def publish(
        self,
        subject: str,
        payload: Dict[str, Any],
        add_timestamp: bool = True,
    ) -> bool:
        """
        Publish an event to NATS.

        Args:
            subject: NATS subject (e.g., "botz.agent.started.v1")
            payload: Event payload dict
            add_timestamp: Add timestamp to payload if not present

        Returns:
            True if published, False otherwise
        """
        if add_timestamp and "timestamp" not in payload:
            payload["timestamp"] = datetime.utcnow().isoformat() + "Z"

        if self._client and self._client.is_connected:
            try:
                await self._client.publish(
                    subject,
                    json.dumps(payload).encode(),
                )
                logger.debug(f"Published to {subject}")
                return True
            except Exception as e:
                logger.error(f"Failed to publish to {subject}: {e}")
                return False
        else:
            # Log event if NATS not connected
            logger.info(f"[EVENT] {subject}: {json.dumps(payload)}")
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False
