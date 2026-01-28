# Geometry Skill - Shape-Attribution & MACA Consensus

**Slice:** `slices/geometry/`
**Type:** Geometric Cognitive Architecture

## Purpose

Advanced reasoning through topology-based concept encoding. Use this skill when:
- Complex concepts need mathematical representation
- Multi-agent consensus is required
- Bandwidth-efficient communication is needed (edge networks)

## Components

### 1. Shape-Attribution Pipeline

Transforms data into Geometry Packets (CGPs):

```python
from slices.geometry import ShapeAttributor, GeometryNormalizer

# Create attributor
attributor = ShapeAttributor()

# Attribute data as geometry
packet = attributor.attribute(
    data=[1.2, 3.4, 5.6],  # Any numerical data
    name="market_trend",
    data_type="timeseries",
)

print(f"Topology: {packet.topology.feature_type}")
print(f"Entropy: {packet.entropy}")
```

### 2. CHIT Geometry Bus

Bandwidth-efficient inter-agent communication:

```python
from slices.geometry import CHITBus

# Create bus
bus = CHITBus(agent_id="agent-1")

# Publish shape
message = await bus.publish(packet, subject="chit.geometry.v1")
print(f"Compression: {message.compression_ratio:.1%}")

# Subscribe to shapes
async def handler(msg):
    reconstructed = bus.reconstruct_packet(msg)
    print(f"Received: {reconstructed.name}")

await bus.subscribe("chit.geometry.v1", handler)
```

### 3. MACA Consensus

Entropy-based multi-agent agreement:

```python
from slices.geometry import MACAConsensus

# Create consensus mechanism
maca = MACAConsensus(agent_id="agent-1", threshold=0.6)

# Propose shape
maca.propose(packet, participants=["agent-2", "agent-3"])

# Vote with transformation
maca.vote(
    packet.id,
    score=0.8,
    transformation={"scale": 1.2, "rotate": 0.1},
)

# Finalize
result = maca.finalize(packet.id)
if result.entropy_metric.converged:
    print(f"Consensus reached! ΔS = {result.entropy_metric.delta}")
```

## Key Concepts

### Entropy Reduction

MACA value is defined by entropy change:

```
ΔS = S_initial - S_final
```

- **ΔS > 0**: Consensus converged (uncertainty reduced)
- **ΔS < 0**: Divergence (more uncertainty)
- **ΔS = 0**: No change

### Anchor Vectors

Holographic compression of geometry:

| Original | Anchor Vector | Compression |
|----------|---------------|-------------|
| Full JSON | Coordinates + coefficients | ~80% smaller |
| 1KB packet | ~200 bytes | Ideal for LoRa |

### Topology Types

| Type | Use Case |
|------|----------|
| MANIFOLD | 3D meshes, surfaces |
| SIMPLEX | Point clouds |
| GRAPH | Networks, relations |
| FIELD | Time-series, gradients |
| WAVEFORM | Audio, signals |

## Pipeline Stages

```
Input Data
    ↓
[Geometry Normalizer] → Common coordinate system
    ↓
[Shape Attributor] → Topology + attributes
    ↓
[Composite Builder] → Constellation (merged shapes)
    ↓
[CHIT Bus] → Compressed transmission
    ↓
[MACA Consensus] → Entropy-based agreement
```

## Integration

### NATS Subjects

| Subject | Purpose |
|---------|---------|
| `chit.geometry.v1` | General geometry packets |
| `chit.consensus.v1` | MACA votes |
| `chit.query.v1` | Packet queries |

### Edge Networks

CHIT is designed for constrained networks:
- LoRa (250 bps - 50 kbps)
- MANETs (mobile ad-hoc)
- Satellite links

## Example: Multi-Agent Shape Debate

```python
# Agent 1: Proposes a shape
packet1 = attributor.attribute(market_data, name="bull_trend")
maca.propose(packet1)

# Agent 2: Counters with transformation
maca.vote(
    packet1.id,
    score=0.5,
    transformation={"scale": 0.8},  # Reduce magnitude
    voter_id="agent-2",
)

# Agent 3: Supports with refinement
maca.vote(
    packet1.id,
    score=0.9,
    transformation={"translate": [0.1, 0, 0]},  # Shift phase
    voter_id="agent-3",
)

# Finalize: weighted transformations applied
result = maca.finalize(packet1.id)
# Result combines all transformations weighted by votes
```

## References

- docs/agents/PMOVES.AI Agentic Architecture Deep Dive.md (Section 5)
- Cymatic-Holographic Information Transfer (CHIT) specification
- Shannon entropy for consensus measurement
