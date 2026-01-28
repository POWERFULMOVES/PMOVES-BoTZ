"""
Vertical Slices Architecture for PMOVES Agent SDK.

Each slice is a self-contained feature module with its own:
- api.py: External interfaces and endpoints
- service.py: Business logic and orchestration
- models.py: Data structures and schemas
- SKILL.md: Pivot file for AI agent context

Reference: docs/agents/AI Agent Integration and Best Practices.md (Section 5.4)
"""

from typing import Dict, Type

# Slice registry for dynamic loading
_SLICE_REGISTRY: Dict[str, Type] = {}


def register_slice(name: str):
    """Decorator to register a slice service class."""
    def decorator(cls):
        _SLICE_REGISTRY[name] = cls
        return cls
    return decorator


def get_slice(name: str):
    """Get a registered slice by name."""
    return _SLICE_REGISTRY.get(name)


def list_slices() -> list:
    """List all registered slices."""
    return list(_SLICE_REGISTRY.keys())


# Import slices to trigger registration
from . import research
from . import code_review
from . import media
from . import knowledge
from . import a2a
from . import geometry

__all__ = [
    "register_slice",
    "get_slice",
    "list_slices",
    "research",
    "code_review",
    "media",
    "knowledge",
    "a2a",
    "geometry",
]
