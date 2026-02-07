"""
MACA - Multi-Agent Consensus Alignment.

Shape-based consensus mechanism using entropy reduction:
- Agents exchange shape transformations as arguments
- Consensus value = ΔS = S_initial - S_final
- Positive ΔS indicates convergence (entropy reduction)

Reference: docs/agents/PMOVES.AI Agentic Architecture Deep Dive.md (Section 5.2)
"""

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import uuid

from .models import (
    ConsensusVote,
    EntropyMetric,
    GeometryPacket,
)

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """Result of a MACA consensus round."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    packet_id: str = ""
    accepted: bool = False
    final_packet: Optional[GeometryPacket] = None
    votes: List[ConsensusVote] = field(default_factory=list)
    entropy_metric: Optional[EntropyMetric] = None
    rounds: int = 0
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "packet_id": self.packet_id,
            "accepted": self.accepted,
            "final_packet": self.final_packet.to_dict() if self.final_packet else None,
            "votes": [v.to_dict() for v in self.votes],
            "entropy_metric": self.entropy_metric.to_dict() if self.entropy_metric else None,
            "rounds": self.rounds,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


class MACAConsensus:
    """
    MACA (Multi-Agent Consensus Alignment) - Entropy-based consensus.

    Unlike traditional voting, MACA uses geometric arguments:
    - Each agent proposes shape transformations
    - Value is measured by entropy reduction: ΔS = S_initial - S_final
    - Consensus converges when global entropy decreases

    Usage:
        maca = MACAConsensus(agent_id="agent-1")

        # Propose a shape
        packet = attributor.attribute(data, name="proposal")
        result = maca.propose(packet, participants=["agent-2", "agent-3"])

        # Vote on a proposal
        maca.vote(packet, score=0.8, transformation={"scale": 1.5})

        # Finalize consensus
        result = maca.finalize(packet.id)
        if result.entropy_metric.converged:
            print("Consensus reached!")
    """

    def __init__(
        self,
        agent_id: str,
        threshold: float = 0.6,
        max_rounds: int = 10,
    ):
        """
        Initialize MACA Consensus.

        Args:
            agent_id: This agent's identifier
            threshold: Acceptance threshold (0-1)
            max_rounds: Maximum consensus rounds
        """
        self.agent_id = agent_id
        self.threshold = threshold
        self.max_rounds = max_rounds

        # Active proposals
        self._proposals: Dict[str, GeometryPacket] = {}
        self._votes: Dict[str, List[ConsensusVote]] = {}
        self._initial_entropy: Dict[str, float] = {}
        self._round_counts: Dict[str, int] = {}
        self._participants: Dict[str, List[str]] = {}  # Expected voters per proposal

    def propose(
        self,
        packet: GeometryPacket,
        participants: Optional[List[str]] = None,
    ) -> str:
        """
        Propose a shape for consensus.

        Args:
            packet: GeometryPacket to propose
            participants: List of agent IDs to participate

        Returns:
            Proposal ID (same as packet ID)
        """
        packet.calculate_entropy()

        self._proposals[packet.id] = packet
        self._votes[packet.id] = []
        self._initial_entropy[packet.id] = packet.entropy
        self._round_counts[packet.id] = 0
        self._participants[packet.id] = participants or []

        logger.info(
            f"MACA proposal: {packet.name} "
            f"(initial entropy: {packet.entropy:.4f}, "
            f"participants: {len(participants or [])})"
        )
        return packet.id

    def vote(
        self,
        packet_id: str,
        score: float,
        transformation: Optional[Dict] = None,
        voter_id: Optional[str] = None,
    ) -> ConsensusVote:
        """
        Cast a vote on a proposal.

        Args:
            packet_id: ID of the proposal
            score: Vote score (-1.0 to 1.0, negative = reject)
            transformation: Optional shape transformation as argument
            voter_id: Voter's agent ID (default: self)

        Returns:
            The recorded vote
        """
        if packet_id not in self._proposals:
            raise ValueError(f"Proposal not found: {packet_id}")

        voter = voter_id or self.agent_id
        packet = self._proposals[packet_id]

        # Calculate entropy delta from transformation
        entropy_delta = 0.0
        if transformation:
            transformed = self._apply_transformation(packet, transformation)
            transformed.calculate_entropy()
            entropy_delta = packet.entropy - transformed.entropy

        vote = ConsensusVote(
            agent_id=voter,
            packet_id=packet_id,
            vote=max(-1.0, min(1.0, score)),
            transformation=transformation,
            entropy_delta=entropy_delta,
        )

        self._votes[packet_id].append(vote)
        self._round_counts[packet_id] += 1

        logger.debug(
            f"MACA vote: {voter} -> {packet_id[:8]} "
            f"(score: {score:.2f}, ΔS: {entropy_delta:.4f})"
        )
        return vote

    def finalize(self, packet_id: str) -> ConsensusResult:
        """
        Finalize consensus on a proposal.

        Args:
            packet_id: ID of the proposal

        Returns:
            ConsensusResult with final determination
        """
        start_time = time.time()

        if packet_id not in self._proposals:
            return ConsensusResult(
                packet_id=packet_id,
                accepted=False,
            )

        packet = self._proposals[packet_id]
        votes = self._votes[packet_id]
        initial_entropy = self._initial_entropy[packet_id]

        # Calculate aggregate vote
        if votes:
            weighted_score = sum(v.vote * (1 + v.entropy_delta) for v in votes)
            avg_score = weighted_score / len(votes)
        else:
            avg_score = 0.0

        # Apply transformations to reduce entropy
        final_packet = self._aggregate_transformations(packet, votes)
        final_packet.calculate_entropy()

        # Calculate entropy metric
        # convergence_rate = entropy reduction per round (higher = faster convergence)
        rounds = self._round_counts.get(packet_id, 1)
        entropy_delta = initial_entropy - final_packet.entropy
        convergence_rate = entropy_delta / rounds if rounds > 0 else 0.0

        entropy_metric = EntropyMetric(
            initial_entropy=initial_entropy,
            final_entropy=final_packet.entropy,
            convergence_rate=convergence_rate,
            participants=len(set(v.agent_id for v in votes)),
        )

        # Acceptance criteria:
        # 1. Average score above threshold
        # 2. Entropy reduced (ΔS > 0)
        accepted = (
            avg_score >= self.threshold and
            entropy_metric.delta > 0
        )

        duration_ms = int((time.time() - start_time) * 1000)

        result = ConsensusResult(
            packet_id=packet_id,
            accepted=accepted,
            final_packet=final_packet,
            votes=votes,
            entropy_metric=entropy_metric,
            rounds=self._round_counts.get(packet_id, 0),
            duration_ms=duration_ms,
        )

        # Cleanup
        self._cleanup_proposal(packet_id)

        logger.info(
            f"MACA finalized: {packet.name} "
            f"(accepted: {accepted}, ΔS: {entropy_metric.delta:.4f})"
        )
        return result

    def _apply_transformation(
        self,
        packet: GeometryPacket,
        transformation: Dict,
    ) -> GeometryPacket:
        """Apply a transformation to a packet."""
        from copy import deepcopy

        transformed = deepcopy(packet)

        if not transformed.anchor:
            return transformed

        coords = list(transformed.anchor.coordinates)

        # Scale transformation
        if "scale" in transformation:
            scale = transformation["scale"]
            coords = [c * scale for c in coords]

        # Rotation transformation (simplified 2D)
        if "rotate" in transformation and len(coords) >= 2:
            angle = transformation["rotate"]
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            x, y = coords[0], coords[1]
            coords[0] = x * cos_a - y * sin_a
            coords[1] = x * sin_a + y * cos_a

        # Translation transformation
        if "translate" in transformation:
            offset = transformation["translate"]
            if isinstance(offset, (list, tuple)):
                coords = [c + (offset[i] if i < len(offset) else 0) for i, c in enumerate(coords)]
            else:
                coords = [c + offset for c in coords]

        transformed.anchor.coordinates = coords
        return transformed

    def _aggregate_transformations(
        self,
        packet: GeometryPacket,
        votes: List[ConsensusVote],
    ) -> GeometryPacket:
        """Aggregate all transformations weighted by votes."""
        from copy import deepcopy

        result = deepcopy(packet)

        if not votes or not result.anchor:
            return result

        # Collect all transformations weighted by vote score
        weighted_transforms = []
        for vote in votes:
            if vote.transformation and vote.vote > 0:
                weighted_transforms.append((vote.transformation, vote.vote))

        if not weighted_transforms:
            return result

        # Apply weighted average of transformations
        total_weight = sum(w for _, w in weighted_transforms)
        if total_weight == 0:
            return result

        for transform, weight in weighted_transforms:
            # Weight the transformation strength
            scaled_transform = {}
            weight_factor = weight / total_weight
            for key, value in transform.items():
                if isinstance(value, (int, float)):
                    # Interpolate toward transformation based on weight
                    if key == "scale":
                        scaled_transform[key] = 1 + (value - 1) * weight_factor
                    else:
                        scaled_transform[key] = value * weight_factor
                elif isinstance(value, (list, tuple)):
                    # Scale vector components (e.g., translation offsets)
                    scaled_transform[key] = type(value)(
                        v * weight_factor if isinstance(v, (int, float)) else v
                        for v in value
                    )
                else:
                    scaled_transform[key] = value

            result = self._apply_transformation(result, scaled_transform)

        return result

    def _cleanup_proposal(self, packet_id: str) -> None:
        """Clean up proposal data."""
        self._proposals.pop(packet_id, None)
        self._votes.pop(packet_id, None)
        self._initial_entropy.pop(packet_id, None)
        self._round_counts.pop(packet_id, None)
        self._participants.pop(packet_id, None)

    def get_pending_proposals(self) -> List[str]:
        """Get list of pending proposal IDs."""
        return list(self._proposals.keys())

    def get_proposal_status(self, packet_id: str) -> Dict:
        """Get current status of a proposal."""
        if packet_id not in self._proposals:
            return {"error": "Proposal not found"}

        packet = self._proposals[packet_id]
        votes = self._votes[packet_id]

        participants = self._participants.get(packet_id, [])
        voters = set(v.agent_id for v in votes)
        return {
            "packet_id": packet_id,
            "name": packet.name,
            "vote_count": len(votes),
            "current_score": sum(v.vote for v in votes) / len(votes) if votes else 0,
            "entropy_reduction": sum(v.entropy_delta for v in votes),
            "rounds": self._round_counts.get(packet_id, 0),
            "expected_participants": participants,
            "pending_participants": [p for p in participants if p not in voters],
        }
