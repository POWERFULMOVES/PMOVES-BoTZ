"""
Geometry Slice - Data Models.

Defines data structures for Geometric Cognitive Architecture:
- Geometry Packets (CGPs) for shape-based reasoning
- Anchor Vectors for CHIT Bus communication
- Entropy metrics for MACA consensus
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid
import math


class TopologyType(Enum):
    """Types of topological features."""
    MANIFOLD = "manifold"
    SIMPLEX = "simplex"
    GRAPH = "graph"
    FIELD = "field"
    WAVEFORM = "waveform"


class SymmetryType(Enum):
    """Types of symmetry in shapes."""
    ROTATIONAL = "rotational"
    REFLECTIVE = "reflective"
    TRANSLATIONAL = "translational"
    SCALE = "scale"
    NONE = "none"


@dataclass
class TopologyFeature:
    """A topological feature of a geometry."""
    name: str
    feature_type: TopologyType
    dimensions: int = 3
    genus: int = 0  # Number of "holes"
    euler_characteristic: float = 0.0
    symmetries: List[SymmetryType] = field(default_factory=list)
    spectral_density: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "feature_type": self.feature_type.value,
            "dimensions": self.dimensions,
            "genus": self.genus,
            "euler_characteristic": self.euler_characteristic,
            "symmetries": [s.value for s in self.symmetries],
            "spectral_density": self.spectral_density,
            "metadata": self.metadata,
        }


@dataclass
class ShapeAttribute:
    """An attributed property of a shape."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    value: Any = None
    confidence: float = 1.0
    invariant: bool = False  # Is this a geometric invariant?
    grounded: bool = False   # Is this grounded in physics?
    source: str = ""         # Attribution source
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "confidence": self.confidence,
            "invariant": self.invariant,
            "grounded": self.grounded,
            "source": self.source,
            "timestamp": self.timestamp,
        }


@dataclass
class AnchorVector:
    """
    Anchor Vector for CHIT Bus communication.

    Represents a compressed holographic reference to a geometry.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    coordinates: List[float] = field(default_factory=list)
    coefficients: List[float] = field(default_factory=list)
    dimension: int = 0
    reference_frame: str = "standard"
    compression_ratio: float = 1.0
    checksum: str = ""

    def __post_init__(self):
        if self.coordinates and not self.dimension:
            self.dimension = len(self.coordinates)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "coordinates": self.coordinates,
            "coefficients": self.coefficients,
            "dimension": self.dimension,
            "reference_frame": self.reference_frame,
            "compression_ratio": self.compression_ratio,
            "checksum": self.checksum,
        }


@dataclass
class GeometryPacket:
    """
    Cymatic Geometry Packet (CGP) - Core unit of geometric reasoning.

    Encodes a concept as a mathematical shape with topological features
    and attributed properties.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    topology: TopologyFeature = None
    attributes: List[ShapeAttribute] = field(default_factory=list)
    anchor: Optional[AnchorVector] = None
    parent_ids: List[str] = field(default_factory=list)  # For composite shapes
    entropy: float = 0.0  # Information entropy
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_entropy(self) -> float:
        """Calculate Shannon entropy of the shape's attributes."""
        if not self.attributes:
            return 0.0

        confidences = [a.confidence for a in self.attributes if a.confidence > 0]
        if not confidences:
            return 0.0

        # Normalize to probabilities
        total = sum(confidences)
        probs = [c / total for c in confidences]

        # Shannon entropy: -sum(p * log2(p))
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        self.entropy = entropy
        return entropy

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "topology": self.topology.to_dict() if self.topology else None,
            "attributes": [a.to_dict() for a in self.attributes],
            "anchor": self.anchor.to_dict() if self.anchor else None,
            "parent_ids": self.parent_ids,
            "entropy": self.entropy,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class ConsensusVote:
    """A vote in MACA consensus."""
    agent_id: str
    packet_id: str
    vote: float  # -1.0 to 1.0 (reject to accept)
    transformation: Optional[Dict] = None  # Shape transformation as argument
    entropy_delta: float = 0.0  # Change in entropy from this vote
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "packet_id": self.packet_id,
            "vote": self.vote,
            "transformation": self.transformation,
            "entropy_delta": self.entropy_delta,
            "timestamp": self.timestamp,
        }


@dataclass
class EntropyMetric:
    """
    Entropy metric for MACA consensus.

    Value is defined by: ΔS = S_initial - S_final
    Positive ΔS indicates entropy reduction (increased certainty).
    """
    initial_entropy: float = 0.0
    final_entropy: float = 0.0
    delta: float = 0.0
    convergence_rate: float = 0.0  # How fast consensus was reached
    participants: int = 0

    def __post_init__(self):
        self.delta = self.initial_entropy - self.final_entropy

    @property
    def converged(self) -> bool:
        """Check if consensus converged (entropy reduced)."""
        return self.delta > 0

    def to_dict(self) -> Dict:
        return {
            "initial_entropy": self.initial_entropy,
            "final_entropy": self.final_entropy,
            "delta": self.delta,
            "convergence_rate": self.convergence_rate,
            "participants": self.participants,
            "converged": self.converged,
        }
