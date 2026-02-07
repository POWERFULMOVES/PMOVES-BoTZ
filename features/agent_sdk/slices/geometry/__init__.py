"""
Geometry Slice - Shape-Attribution, CHIT Bus, and MACA Consensus.

This vertical slice implements Geometric Cognitive Architecture:
- Shape-Attribution pipeline for topology-based reasoning
- CHIT (Cymatic-Holographic Information Transfer) Bus
- MACA (Multi-Agent Consensus Alignment) mechanism

Reference: docs/agents/PMOVES.AI Agentic Architecture Deep Dive.md (Section 5)

Use: from slices.geometry import ShapeAttributor, CHITBus, MACAConsensus
"""

from .chit_bus import CHITBus, CHITMessage, create_chit_bus, create_chit_bus_async
from .maca import ConsensusResult, MACAConsensus
from .models import (
    AnchorVector,
    ConsensusVote,
    EntropyMetric,
    GeometryPacket,
    ShapeAttribute,
    TopologyFeature,
)
from .shape_attribution import CompositeBuilder, GeometryNormalizer, ShapeAttributor
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
    "create_chit_bus",
    "create_chit_bus_async",
    "EntropyMetric",
    "GeometryNormalizer",
    "GeometryPacket",
    "MACAConsensus",
    "ShapeAttribute",
    "ShapeAttributor",
    "TopologyFeature",
]
