import sys
from typing import Any, Callable

from .tools import hirag, nats, tensorzero, supabase
try:
    from .tools import hirag, nats, tensorzero, supabase
except ImportError:
    # When run directly, use absolute imports
    from tools import hirag, nats, tensorzero, supabase
