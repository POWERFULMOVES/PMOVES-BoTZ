"""
Cost Tracker Hook

Tracks token usage and API costs for agent operations.
Stores metrics for analytics and budgeting.

Storage:
- Local: ~/.pmoves/metrics/cost_tracking.jsonl
- Supabase: agent_cost_metrics table
- ClickHouse: TensorZero observability

Usage:
    # As a function
    await track_cost(model, tokens_in, tokens_out, agent_id)

    # As CLI (for hook command)
    python -m pmoves_botz.features.agent_sdk.hooks.cost_tracker --agent-id xxx
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# Approximate costs per 1K tokens (USD)
MODEL_COSTS = {
    # Anthropic
    "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
    "claude-opus-4": {"input": 0.015, "output": 0.075},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},

    # OpenAI via OpenRouter
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},

    # Local models (free)
    "qwen3:8b": {"input": 0, "output": 0},
    "qwen3:32b": {"input": 0, "output": 0},
    "llama3.1": {"input": 0, "output": 0},
    "phi3": {"input": 0, "output": 0},

    # Gemini
    "gemini-2.0-flash": {"input": 0.00015, "output": 0.0006},
    "gemini-3-flash-preview": {"input": 0.0001, "output": 0.0004},
}


class CostTrackerHook:
    """
    Cost tracking hook for API usage monitoring.

    Tracks:
    - Token counts (input/output)
    - Estimated costs per model
    - Cumulative session costs
    - Budget alerts

    Attributes:
        agent_id: Agent identifier
        session_id: Session for aggregation
        budget_limit: Optional spending limit
    """

    METRICS_DIR = Path(os.path.expanduser("~/.pmoves/metrics"))
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")

    def __init__(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        budget_limit: Optional[float] = None,
    ):
        """
        Initialize cost tracker.

        Args:
            agent_id: Agent identifier
            session_id: Optional session ID for grouping
            budget_limit: Optional spending limit (USD)
        """
        self.agent_id = agent_id
        self.session_id = session_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.budget_limit = budget_limit

        self.METRICS_DIR.mkdir(parents=True, exist_ok=True)

        self.session_costs = {"total": 0.0, "by_model": {}}

    async def post_tool_use(
        self,
        tool_name: str,
        input_data: dict,
        result: Any,
        duration_ms: float,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Track costs after tool use.

        Currently tracks LLM-related tool costs.

        Args:
            tool_name: Tool name
            input_data: Tool input
            result: Tool result
            duration_ms: Execution time
            context: Execution context

        Returns:
            Cost info or empty dict
        """
        # Extract token counts from result if available
        if isinstance(result, dict) and "usage" in result:
            usage = result["usage"]
            model = result.get("model", "unknown")

            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)

            cost = await self.track_tokens(model, tokens_in, tokens_out)

            if self.budget_limit and self.session_costs["total"] > self.budget_limit:
                return {"warning": f"Budget limit exceeded: ${self.session_costs['total']:.4f} > ${self.budget_limit}"}

            return {"cost_usd": cost}

        return {}

    async def track_tokens(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        metadata: Optional[dict] = None,
    ) -> float:
        """
        Track token usage and calculate cost.

        Args:
            model: Model name
            tokens_in: Input tokens
            tokens_out: Output tokens
            metadata: Additional metadata

        Returns:
            Estimated cost in USD
        """
        # Normalize model name
        model_key = self._normalize_model_name(model)
        costs = MODEL_COSTS.get(model_key, {"input": 0, "output": 0})

        cost_in = (tokens_in / 1000) * costs["input"]
        cost_out = (tokens_out / 1000) * costs["output"]
        total_cost = cost_in + cost_out

        # Update session totals
        self.session_costs["total"] += total_cost
        if model_key not in self.session_costs["by_model"]:
            self.session_costs["by_model"][model_key] = {"tokens_in": 0, "tokens_out": 0, "cost": 0}
        self.session_costs["by_model"][model_key]["tokens_in"] += tokens_in
        self.session_costs["by_model"][model_key]["tokens_out"] += tokens_out
        self.session_costs["by_model"][model_key]["cost"] += total_cost

        # Log entry
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "model": model_key,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": total_cost,
            "session_total_usd": self.session_costs["total"],
            "metadata": metadata,
        }

        await self._write_metrics(entry)
        return total_cost

    def _normalize_model_name(self, model: str) -> str:
        """Normalize model name for cost lookup."""
        # Handle provider::model syntax
        if "::" in model:
            model = model.split("::")[-1]

        # Remove version suffixes
        for suffix in ["-20250514", "-20250120", "-preview"]:
            model = model.replace(suffix, "")

        return model

    async def _write_metrics(self, entry: dict) -> None:
        """Write metrics to storage."""
        # Write to local file
        metrics_file = self.METRICS_DIR / "cost_tracking.jsonl"
        with open(metrics_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Write to Supabase if configured
        if self.SUPABASE_URL:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.SUPABASE_URL}/rest/v1/agent_cost_metrics",
                        json=entry,
                    )
            except Exception:
                pass

    def get_session_summary(self) -> dict:
        """Get summary of session costs."""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "total_cost_usd": self.session_costs["total"],
            "by_model": self.session_costs["by_model"],
            "budget_limit": self.budget_limit,
            "budget_remaining": (
                self.budget_limit - self.session_costs["total"]
                if self.budget_limit else None
            ),
        }


async def track_cost(
    model: str,
    tokens_in: int,
    tokens_out: int,
    agent_id: str,
) -> float:
    """
    Convenience function to track cost.

    Args:
        model: Model name
        tokens_in: Input tokens
        tokens_out: Output tokens
        agent_id: Agent ID

    Returns:
        Cost in USD
    """
    tracker = CostTrackerHook(agent_id)
    return await tracker.track_tokens(model, tokens_in, tokens_out)


def main():
    """CLI entry point for hook command."""
    parser = argparse.ArgumentParser(description="PMOVES Cost Tracker Hook")
    parser.add_argument("--agent-id", required=True, help="Agent identifier")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--tokens-in", type=int, default=0)
    parser.add_argument("--tokens-out", type=int, default=0)

    args = parser.parse_args()

    # Read input from stdin
    input_json = sys.stdin.read() if not sys.stdin.isatty() else "{}"

    try:
        data = json.loads(input_json)
    except json.JSONDecodeError:
        data = {}

    # Extract usage if present
    usage = data.get("result", {}).get("usage", {})
    tokens_in = args.tokens_in or usage.get("prompt_tokens", 0)
    tokens_out = args.tokens_out or usage.get("completion_tokens", 0)
    model = args.model or data.get("result", {}).get("model", "unknown")

    # Calculate cost
    tracker = CostTrackerHook(args.agent_id)
    model_key = tracker._normalize_model_name(model)
    costs = MODEL_COSTS.get(model_key, {"input": 0, "output": 0})
    cost = (tokens_in / 1000) * costs["input"] + (tokens_out / 1000) * costs["output"]

    # Write metrics
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "agent_id": args.agent_id,
        "model": model_key,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost,
    }

    metrics_dir = Path(os.path.expanduser("~/.pmoves/metrics"))
    metrics_dir.mkdir(parents=True, exist_ok=True)
    with open(metrics_dir / "cost_tracking.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Output cost info
    print(json.dumps({"cost_usd": cost}))


if __name__ == "__main__":
    main()
