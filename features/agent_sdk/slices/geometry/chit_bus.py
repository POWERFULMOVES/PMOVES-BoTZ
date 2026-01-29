"""
CHIT Geometry Bus - Cymatic-Holographic Information Transfer.

Enables shape-based communication between agents:
- Holographic compression of geometry packets
- Anchor vector transmission
- Bandwidth-efficient for edge networks (LoRa, MANETs)

Reference: docs/agents/PMOVES.AI Agentic Architecture Deep Dive.md (Section 5.2)
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import uuid

from .models import AnchorVector, GeometryPacket

logger = logging.getLogger(__name__)


@dataclass
class CHITMessage:
    """
    CHIT Bus Message - Compressed geometry packet transmission.

    Instead of verbose JSON, transmits mathematical definition of shapes
    via anchor vectors for bandwidth efficiency.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    packet_id: str = ""
    anchor: Optional[AnchorVector] = None
    payload_type: str = "geometry"  # geometry, consensus, query
    compressed_size: int = 0
    original_size: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    ttl: int = 60  # Time-to-live in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        if self.original_size == 0:
            return 0.0
        return 1 - (self.compressed_size / self.original_size)

    def to_bytes(self) -> bytes:
        """Serialize message to compact binary format."""
        # Compact format: id|sender|packet|anchor_coords|anchor_coeffs|type|ts
        parts = [
            self.id[:8],  # Truncated UUID
            self.sender_id[:16],
            self.packet_id[:8],
            self.payload_type[:4],
        ]

        if self.anchor:
            # Encode coordinates as fixed-point integers (3 decimal places)
            coords = [int(c * 1000) for c in self.anchor.coordinates[:8]]
            parts.append(",".join(str(c) for c in coords))
            coeffs = [int(c * 1000) for c in self.anchor.coefficients[:4]]
            parts.append(",".join(str(c) for c in coeffs))
        else:
            parts.extend(["", ""])

        message = "|".join(parts)
        encoded = message.encode("utf-8")
        self.compressed_size = len(encoded)
        return encoded

    @classmethod
    def from_bytes(cls, data: bytes) -> "CHITMessage":
        """Deserialize message from compact binary format."""
        message = data.decode("utf-8")
        parts = message.split("|")

        msg = cls(
            id=parts[0] if len(parts) > 0 else "",
            sender_id=parts[1] if len(parts) > 1 else "",
            packet_id=parts[2] if len(parts) > 2 else "",
            payload_type=parts[3] if len(parts) > 3 else "geometry",
        )

        # Decode anchor (guard against malformed/truncated payloads)
        if len(parts) > 4 and parts[4]:
            try:
                coords = [int(c) / 1000 for c in parts[4].split(",") if c]
                coeffs_part = parts[5] if len(parts) > 5 else ""
                coeffs = [int(c) / 1000 for c in coeffs_part.split(",") if c]
                msg.anchor = AnchorVector(
                    coordinates=coords,
                    coefficients=coeffs,
                    dimension=len(coords),
                )
            except (ValueError, IndexError) as e:
                logger.warning(f"Malformed CHIT payload, skipping anchor: {e}")

        msg.compressed_size = len(data)
        return msg

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "packet_id": self.packet_id,
            "anchor": self.anchor.to_dict() if self.anchor else None,
            "payload_type": self.payload_type,
            "compressed_size": self.compressed_size,
            "original_size": self.original_size,
            "compression_ratio": self.compression_ratio,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "metadata": self.metadata,
        }


class CHITBus:
    """
    CHIT Geometry Bus - Inter-agent geometry packet exchange.

    Provides:
    - Holographic compression for bandwidth-constrained networks
    - Pub/Sub for geometry packets
    - Deduplication and caching
    """

    def __init__(
        self,
        agent_id: str,
        nats_client: Optional[Any] = None,
        cache_ttl: int = 300,
    ):
        """
        Initialize CHIT Bus.

        Args:
            agent_id: Unique identifier for this agent
            nats_client: NATS client for message transport (optional)
            cache_ttl: Cache time-to-live in seconds
        """
        self.agent_id = agent_id
        self.nats_client = nats_client
        self.cache_ttl = cache_ttl

        # Local packet cache
        self._cache: Dict[str, GeometryPacket] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # Message handlers
        self._handlers: Dict[str, List[Callable]] = {}

        # Stats
        self._messages_sent = 0
        self._messages_received = 0
        self._bytes_saved = 0

    async def publish(
        self,
        packet: GeometryPacket,
        subject: str = "chit.geometry.v1",
    ) -> CHITMessage:
        """
        Publish a geometry packet to the CHIT Bus.

        Args:
            packet: GeometryPacket to publish
            subject: NATS subject for routing

        Returns:
            CHITMessage that was sent
        """
        # Create compressed message
        original_json = json.dumps(packet.to_dict())
        original_size = len(original_json.encode())

        message = CHITMessage(
            sender_id=self.agent_id,
            packet_id=packet.id,
            anchor=packet.anchor,
            payload_type="geometry",
            original_size=original_size,
        )

        # Compress to bytes
        compressed = message.to_bytes()
        message.compressed_size = len(compressed)

        # Cache locally
        self._cache_packet(packet)

        # Send via NATS if available
        if self.nats_client:
            try:
                await self.nats_client.publish(subject, compressed)
                logger.debug(f"Published packet {packet.id} to {subject}")
            except Exception as e:
                logger.error(f"Failed to publish to NATS: {e}")

        # Update stats
        self._messages_sent += 1
        self._bytes_saved += original_size - message.compressed_size

        logger.info(
            f"CHIT publish: {packet.name} "
            f"({message.compression_ratio:.1%} compression)"
        )
        return message

    async def subscribe(
        self,
        subject: str,
        handler: Callable[[CHITMessage], None],
    ) -> None:
        """
        Subscribe to geometry packets on a subject.

        Args:
            subject: NATS subject pattern
            handler: Callback for received messages
        """
        if subject not in self._handlers:
            self._handlers[subject] = []
        self._handlers[subject].append(handler)

        if self.nats_client:
            async def nats_handler(msg):
                try:
                    chit_msg = CHITMessage.from_bytes(msg.data)
                    self._messages_received += 1
                    handler(chit_msg)
                except Exception as e:
                    logger.error(f"Error handling CHIT message: {e}")

            await self.nats_client.subscribe(subject, cb=nats_handler)
            logger.info(f"Subscribed to CHIT subject: {subject}")
        else:
            # Local mode: handlers are stored and invoked directly via publish_local
            logger.info(f"Subscribed to CHIT subject (local mode): {subject}")

    def reconstruct_packet(
        self,
        message: CHITMessage,
        name: str = "",
    ) -> GeometryPacket:
        """
        Reconstruct a GeometryPacket from a CHIT message.

        Uses cached data if available, otherwise creates minimal packet.

        Args:
            message: CHITMessage received
            name: Optional name override

        Returns:
            Reconstructed GeometryPacket
        """
        # Check cache first (use truncated ID to match wire format)
        cache_key = message.packet_id[:8]
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        # Reconstruct minimal packet from anchor
        from .models import TopologyFeature, TopologyType

        packet = GeometryPacket(
            id=message.packet_id,
            name=name or f"reconstructed_{message.packet_id[:8]}",
            anchor=message.anchor,
            topology=TopologyFeature(
                name="reconstructed",
                feature_type=TopologyType.SIMPLEX,
                dimensions=message.anchor.dimension if message.anchor else 0,
            ),
        )

        # Cache the reconstruction
        self._cache_packet(packet)
        return packet

    def _cache_packet(self, packet: GeometryPacket) -> None:
        """Add packet to local cache.

        Uses truncated packet ID (first 8 chars) as cache key to match
        the wire format used in CHITMessage serialization.
        """
        cache_key = packet.id[:8]
        self._cache[cache_key] = packet
        self._cache_timestamps[cache_key] = time.time()
        self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """Remove expired cache entries."""
        now = time.time()
        expired = [
            pid for pid, ts in self._cache_timestamps.items()
            if now - ts > self.cache_ttl
        ]
        for pid in expired:
            self._cache.pop(pid, None)
            self._cache_timestamps.pop(pid, None)

    def get_stats(self) -> Dict:
        """Get bus statistics."""
        return {
            "agent_id": self.agent_id,
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
            "bytes_saved": self._bytes_saved,
            "cache_size": len(self._cache),
            "has_nats": self.nats_client is not None,
        }


def create_chit_bus(
    agent_id: str,
    nats_url: Optional[str] = None,
) -> CHITBus:
    """
    Create a CHIT Bus instance (sync factory, local-only).

    For distributed messaging with NATS, use create_chit_bus_async() instead.

    Args:
        agent_id: Agent identifier
        nats_url: Optional NATS URL (logged for info, but connection requires async)

    Returns:
        CHITBus instance in local mode
    """
    if nats_url:
        logger.info(
            f"CHIT Bus configured for NATS at {nats_url}. "
            "Use create_chit_bus_async() for actual NATS connection."
        )

    return CHITBus(agent_id=agent_id, nats_client=None)


async def create_chit_bus_async(
    agent_id: str,
    nats_url: Optional[str] = None,
) -> CHITBus:
    """
    Create a CHIT Bus instance with NATS connection (async factory).

    Args:
        agent_id: Agent identifier
        nats_url: Optional NATS URL for distributed messaging

    Returns:
        Configured CHITBus instance with active NATS connection
    """
    nats_client = None

    if nats_url:
        try:
            import nats
            nats_client = await nats.connect(nats_url)
            logger.info(f"CHIT Bus connected to NATS: {nats_url}")
        except ImportError:
            logger.warning("NATS package not installed - running in local mode")
        except Exception as e:
            logger.warning(f"NATS connection failed ({e}) - running in local mode")

    return CHITBus(agent_id=agent_id, nats_client=nats_client)
