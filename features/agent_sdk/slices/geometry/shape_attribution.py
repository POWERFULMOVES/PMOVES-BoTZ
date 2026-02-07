"""
Shape-Attribution Pipeline - Topology-based concept encoding.

Pipeline stages:
1. Geometry Normalizer: Standardize inputs to common coordinate system
2. Shape Attributor: Analyze geometry for topological features
3. Composite Builder: Merge shapes into Constellations
4. Visualizer: Render to human-perceivable form (Cymatic patterns)

Reference: docs/agents/PMOVES.AI Agentic Architecture Deep Dive.md (Section 5.1)
"""

import hashlib
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    AnchorVector,
    GeometryPacket,
    ShapeAttribute,
    SymmetryType,
    TopologyFeature,
    TopologyType,
)

logger = logging.getLogger(__name__)


class GeometryNormalizer:
    """
    Geometry Normalizer - First stage of Shape-Attribution pipeline.

    Standardizes diverse inputs (audio waveforms, 3D meshes, time-series)
    into a common coordinate system for geometric analysis.
    """

    def __init__(self, target_dimensions: int = 3):
        """
        Initialize Geometry Normalizer.

        Args:
            target_dimensions: Target coordinate dimensions (default: 3)
        """
        self.target_dimensions = target_dimensions

    def normalize(self, data: Any, data_type: str = "auto") -> List[float]:
        """
        Normalize input data to standard coordinates.

        Args:
            data: Input data (array, dict, or raw values)
            data_type: Type hint ("waveform", "mesh", "timeseries", "auto")

        Returns:
            Normalized coordinate vector
        """
        if data_type == "auto":
            data_type = self._detect_type(data)

        if data_type == "waveform":
            return self._normalize_waveform(data)
        elif data_type == "mesh":
            return self._normalize_mesh(data)
        elif data_type == "timeseries":
            return self._normalize_timeseries(data)
        else:
            return self._normalize_generic(data)

    def _detect_type(self, data: Any) -> str:
        """Auto-detect input data type."""
        if isinstance(data, (list, tuple)):
            if len(data) > 100:
                return "waveform"
            elif all(isinstance(x, (list, tuple)) for x in data):
                return "mesh"
        return "generic"

    def _normalize_waveform(self, data: List[float]) -> List[float]:
        """Normalize audio waveform to spectral coordinates."""
        if not data:
            return [0.0] * self.target_dimensions

        # Simple FFT-like decomposition (placeholder)
        n = len(data)
        magnitude = sum(abs(x) for x in data) / n
        mean = sum(data) / n
        variance = sum((x - mean) ** 2 for x in data) / n

        return [magnitude, mean, math.sqrt(variance)][:self.target_dimensions]

    def _normalize_mesh(self, vertices: List[List[float]]) -> List[float]:
        """Normalize 3D mesh to centroid coordinates."""
        if not vertices:
            return [0.0] * self.target_dimensions

        # Calculate centroid
        n = len(vertices)
        centroid = [
            sum(v[i] if i < len(v) else 0 for v in vertices) / n
            for i in range(self.target_dimensions)
        ]
        return centroid

    def _normalize_timeseries(self, data: List[float]) -> List[float]:
        """Normalize time-series to trend coordinates."""
        if not data:
            return [0.0] * self.target_dimensions

        n = len(data)
        mean = sum(data) / n
        trend = (data[-1] - data[0]) / n if n > 1 else 0
        volatility = math.sqrt(sum((x - mean) ** 2 for x in data) / n)

        return [mean, trend, volatility][:self.target_dimensions]

    def _normalize_generic(self, data: Any) -> List[float]:
        """Fallback normalization for unknown types."""
        if isinstance(data, (int, float)):
            return [float(data)] + [0.0] * (self.target_dimensions - 1)
        elif isinstance(data, (list, tuple)):
            result = [float(x) if isinstance(x, (int, float)) else 0.0 for x in data]
            while len(result) < self.target_dimensions:
                result.append(0.0)
            return result[:self.target_dimensions]
        else:
            # Hash-based encoding for complex objects
            h = hashlib.sha256(str(data).encode()).hexdigest()
            coords = [int(h[i:i+8], 16) / (16**8) for i in range(0, 24, 8)]
            return coords[:self.target_dimensions]


class ShapeAttributor:
    """
    Shape Attributor - Second stage of Shape-Attribution pipeline.

    Analyzes geometry for topological features and assigns attributes
    grounded in geometric invariants.
    """

    def __init__(self, normalizer: Optional[GeometryNormalizer] = None):
        """
        Initialize Shape Attributor.

        Args:
            normalizer: Geometry normalizer (created if not provided)
        """
        self.normalizer = normalizer or GeometryNormalizer()

    def attribute(
        self,
        data: Any,
        name: str = "",
        data_type: str = "auto",
    ) -> GeometryPacket:
        """
        Attribute a data input as a Geometry Packet.

        Args:
            data: Input data to analyze
            name: Name for the resulting shape
            data_type: Type hint for normalization

        Returns:
            GeometryPacket with topological features and attributes
        """
        # Normalize to coordinates
        coordinates = self.normalizer.normalize(data, data_type)

        # Analyze topology
        topology = self._analyze_topology(coordinates, data_type)

        # Extract attributes
        attributes = self._extract_attributes(coordinates, topology)

        # Create anchor vector
        anchor = self._create_anchor(coordinates)

        # Build packet
        packet = GeometryPacket(
            name=name or f"shape_{topology.feature_type.value}",
            topology=topology,
            attributes=attributes,
            anchor=anchor,
        )
        packet.calculate_entropy()

        logger.debug(f"Attributed shape: {packet.name} with {len(attributes)} attributes")
        return packet

    def _analyze_topology(self, coords: List[float], data_type: str) -> TopologyFeature:
        """Analyze topological features of coordinates."""
        # Determine topology type based on data
        type_map = {
            "waveform": TopologyType.WAVEFORM,
            "mesh": TopologyType.MANIFOLD,
            "timeseries": TopologyType.FIELD,
            "generic": TopologyType.SIMPLEX,
        }
        topo_type = type_map.get(data_type, TopologyType.SIMPLEX)

        # Detect symmetries
        symmetries = self._detect_symmetries(coords)

        # Calculate Euler characteristic (simplified)
        euler = self._calculate_euler(coords)

        return TopologyFeature(
            name=f"{topo_type.value}_topology",
            feature_type=topo_type,
            dimensions=len(coords),
            genus=0,  # Would require more complex analysis
            euler_characteristic=euler,
            symmetries=symmetries,
            spectral_density=coords,  # Simplified: use coords as spectral
        )

    def _detect_symmetries(self, coords: List[float]) -> List[SymmetryType]:
        """Detect symmetries in coordinates."""
        symmetries = []

        if not coords:
            return [SymmetryType.NONE]

        # Check for rotational symmetry (all coords equal)
        if len(set(round(c, 4) for c in coords)) == 1:
            symmetries.append(SymmetryType.ROTATIONAL)

        # Check for reflective symmetry (palindromic)
        if coords == coords[::-1]:
            symmetries.append(SymmetryType.REFLECTIVE)

        # Check for scale symmetry (proportional)
        if len(coords) > 1 and coords[0] != 0:
            ratios = [c / coords[0] for c in coords[1:] if coords[0] != 0]
            if len(set(round(r, 4) for r in ratios)) == 1:
                symmetries.append(SymmetryType.SCALE)

        return symmetries if symmetries else [SymmetryType.NONE]

    def _calculate_euler(self, coords: List[float]) -> float:
        """Calculate simplified Euler characteristic."""
        # V - E + F for simplicial complex (simplified)
        # For a point cloud, estimate based on dimension
        n = len(coords)
        return 2 - n if n > 0 else 0

    def _extract_attributes(
        self,
        coords: List[float],
        topology: TopologyFeature,
    ) -> List[ShapeAttribute]:
        """Extract attributes from coordinates and topology."""
        attributes = []

        # Magnitude attribute
        magnitude = math.sqrt(sum(c ** 2 for c in coords)) if coords else 0
        attributes.append(ShapeAttribute(
            name="magnitude",
            value=magnitude,
            confidence=1.0,
            invariant=True,
            grounded=True,
            source="geometric_analysis",
        ))

        # Dimension attribute
        attributes.append(ShapeAttribute(
            name="dimension",
            value=topology.dimensions,
            confidence=1.0,
            invariant=True,
            grounded=True,
            source="topology",
        ))

        # Symmetry count
        attributes.append(ShapeAttribute(
            name="symmetry_count",
            value=len([s for s in topology.symmetries if s != SymmetryType.NONE]),
            confidence=0.9,
            invariant=False,
            grounded=True,
            source="symmetry_analysis",
        ))

        return attributes

    def _create_anchor(self, coords: List[float]) -> AnchorVector:
        """Create anchor vector for CHIT Bus transmission."""
        # Simple anchor: normalized coordinates with checksum
        if not coords:
            return AnchorVector()

        magnitude = math.sqrt(sum(c ** 2 for c in coords)) or 1.0
        normalized = [c / magnitude for c in coords]

        # Generate checksum
        coord_str = ",".join(f"{c:.6f}" for c in normalized)
        checksum = hashlib.sha256(coord_str.encode()).hexdigest()[:16]

        return AnchorVector(
            coordinates=normalized,
            coefficients=[magnitude],
            dimension=len(coords),
            compression_ratio=len(coord_str) / 128,  # Relative to full precision
            checksum=checksum,
        )


class CompositeBuilder:
    """
    Composite Builder - Third stage of Shape-Attribution pipeline.

    Merges multiple shapes into Constellations for complex reasoning.
    """

    def __init__(self, attributor: Optional[ShapeAttributor] = None):
        """
        Initialize Composite Builder.

        Args:
            attributor: Shape attributor for sub-shapes
        """
        self.attributor = attributor or ShapeAttributor()

    def build_constellation(
        self,
        shapes: List[GeometryPacket],
        operation: str = "union",
        name: str = "",
    ) -> GeometryPacket:
        """
        Build a composite shape (Constellation) from multiple shapes.

        Args:
            shapes: List of GeometryPackets to combine
            operation: Combination operation ("union", "intersection", "transform")
            name: Name for the resulting constellation

        Returns:
            Composite GeometryPacket
        """
        if not shapes:
            return GeometryPacket(name=name or "empty_constellation")

        # Collect parent IDs
        parent_ids = [s.id for s in shapes]

        # Combine coordinates based on operation
        if operation == "union":
            combined = self._union_coords(shapes)
        elif operation == "intersection":
            combined = self._intersection_coords(shapes)
        else:
            combined = self._transform_coords(shapes)

        # Create composite topology
        topology = TopologyFeature(
            name=f"constellation_{operation}",
            feature_type=TopologyType.MANIFOLD,
            dimensions=len(combined),
            genus=len(shapes) - 1,  # Holes equal to merged shapes - 1
        )

        # Merge attributes
        attributes = self._merge_attributes(shapes)

        # Create composite anchor
        anchor = self.attributor._create_anchor(combined)

        # Build constellation
        constellation = GeometryPacket(
            name=name or f"constellation_{len(shapes)}",
            topology=topology,
            attributes=attributes,
            anchor=anchor,
            parent_ids=parent_ids,
        )
        constellation.calculate_entropy()

        logger.info(f"Built constellation: {constellation.name} from {len(shapes)} shapes")
        return constellation

    def _union_coords(self, shapes: List[GeometryPacket]) -> List[float]:
        """Combine coordinates via union (centroid of all)."""
        all_coords = []
        for shape in shapes:
            if shape.anchor:
                all_coords.append(shape.anchor.coordinates)

        if not all_coords:
            return []

        # Calculate centroid
        n = len(all_coords)
        dim = max(len(c) for c in all_coords)
        centroid = []
        for i in range(dim):
            values = [c[i] if i < len(c) else 0 for c in all_coords]
            centroid.append(sum(values) / n)

        return centroid

    def _intersection_coords(self, shapes: List[GeometryPacket]) -> List[float]:
        """Combine coordinates via intersection (minimum envelope)."""
        all_coords = []
        for shape in shapes:
            if shape.anchor:
                all_coords.append(shape.anchor.coordinates)

        if not all_coords:
            return []

        dim = min(len(c) for c in all_coords)
        intersection = []
        for i in range(dim):
            values = [c[i] for c in all_coords if i < len(c)]
            intersection.append(min(values))

        return intersection

    def _transform_coords(self, shapes: List[GeometryPacket]) -> List[float]:
        """Combine coordinates via transformation (sequential application)."""
        if not shapes:
            return []

        # Start with first shape's coordinates
        result = shapes[0].anchor.coordinates if shapes[0].anchor else []

        # Apply subsequent shapes as transformations
        for shape in shapes[1:]:
            if shape.anchor:
                transform = shape.anchor.coordinates
                result = [
                    r * t if i < len(transform) else r
                    for i, (r, t) in enumerate(zip(result, transform + [1.0] * len(result)))
                ]

        return result

    def _merge_attributes(self, shapes: List[GeometryPacket]) -> List[ShapeAttribute]:
        """Merge attributes from multiple shapes."""
        all_attrs = {}

        for shape in shapes:
            for attr in shape.attributes:
                key = attr.name
                if key in all_attrs:
                    # Average confidence-weighted values
                    existing = all_attrs[key]
                    if isinstance(existing.value, (int, float)) and isinstance(attr.value, (int, float)):
                        total_conf = existing.confidence + attr.confidence
                        existing.value = (
                            existing.value * existing.confidence +
                            attr.value * attr.confidence
                        ) / total_conf
                        existing.confidence = total_conf / 2
                else:
                    all_attrs[key] = ShapeAttribute(
                        name=attr.name,
                        value=attr.value,
                        confidence=attr.confidence,
                        invariant=attr.invariant,
                        grounded=attr.grounded,
                        source="composite",
                    )

        return list(all_attrs.values())
