"""
Geometry Slice - Shape-Attribution, CHIT Bus, and MACA Consensus.

This vertical slice implements Geometric Cognitive Architecture:
- Shape-Attribution pipeline for topology-based reasoning
- CHIT (Cymatic-Holographic Information Transfer) Bus
- MACA (Multi-Agent Consensus Alignment) mechanism

Reference: docs/agents/PMOVES.AI Agentic Architecture Deep Dive.md (Section 5)

Use: from slices.geometry import ShapeAttributor, CHITBus, MACAConsensus
"""

from .models import (
    GeometryPacket,
    ShapeAttribute,
    TopologyFeature,
    AnchorVector,
    ConsensusVote,
    EntropyMetric,
)
from .shape_attribution import ShapeAttributor, GeometryNormalizer, CompositeBuilder
from .chit_bus import CHITBus, CHITMessage
from .maca import MACAConsensus, ConsensusResult
from .. import register_slice

# Register this slice
register_slice("geometry")(ShapeAttributor)

__all__ = [
    "AnchorVector",
    "CHITBus",
    "CHITMessage",
    "CompositeBuilder",
    "ConsensusResult",
    "ConsensusVote",
    "EntropyMetric",
    "GeometryNormalizer",
    "GeometryPacket",
    "MACAConsensus",
    "ShapeAttribute",
    "ShapeAttributor",
    "TopologyFeature",
]
