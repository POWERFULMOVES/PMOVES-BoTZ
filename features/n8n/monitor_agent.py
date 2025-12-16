#!/usr/bin/env python3
"""
PMOVES n8n Monitor Agent - Review Learnings & Execution Tracking

Subscribes to code review events and tool execution events via NATS,
stores learnings in cipher memory, and tracks workflow execution outcomes
to improve future suggestions.

NATS Subjects:
- claude.code.tool.executed.v1 - Claude CLI tool executions
- n8n.workflow.executed.v1 - n8n workflow execution results
- code.review.completed.v1 - Code review outcomes

TensorZero Integration:
- Uses local models for learning extraction
- Analyzes execution outcomes for patterns
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

try:
    import nats
    from nats.aio.client import Client as NATSClient
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    NATSClient = None


class TensorZeroClient:
    """Client for TensorZero gateway LLM inference."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("TENSORZERO_BASE_URL", "http://tensorzero-gateway:3030")
        ).rstrip("/")
        self.model = model or os.environ.get("TENSORZERO_MODEL", "qwen2_5_14b")
        self.api_key = os.environ.get("TENSORZERO_API_KEY", "")

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Send a chat completion request to TensorZero."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[TensorZero error] {e}"


class LearningStore:
    """In-memory learning store with persistence capabilities."""

    def __init__(self) -> None:
        self.learnings: List[Dict[str, Any]] = []
        self.execution_outcomes: List[Dict[str, Any]] = []
        self.review_feedback: List[Dict[str, Any]] = []

    def add_learning(self, learning: Dict[str, Any]) -> None:
        """Add a new learning entry."""
        learning["timestamp"] = datetime.utcnow().isoformat()
        self.learnings.append(learning)

    def add_execution_outcome(self, outcome: Dict[str, Any]) -> None:
        """Track workflow execution outcome."""
        outcome["timestamp"] = datetime.utcnow().isoformat()
        self.execution_outcomes.append(outcome)

    def add_review_feedback(self, feedback: Dict[str, Any]) -> None:
        """Store code review feedback."""
        feedback["timestamp"] = datetime.utcnow().isoformat()
        self.review_feedback.append(feedback)

    def get_recent_learnings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent learnings."""
        return self.learnings[-limit:]

    def get_success_patterns(self) -> List[Dict[str, Any]]:
        """Get patterns from successful executions."""
        return [
            o for o in self.execution_outcomes
            if o.get("status") == "success"
        ]

    def export_to_json(self) -> str:
        """Export all data as JSON."""
        return json.dumps({
            "learnings": self.learnings,
            "execution_outcomes": self.execution_outcomes,
            "review_feedback": self.review_feedback,
        }, indent=2)


class MonitorAgent:
    """NATS-based monitor agent for tracking learnings."""

    def __init__(self) -> None:
        self.nats_url = os.environ.get("NATS_URL", "nats://localhost:4222")
        self.nc: Optional[NATSClient] = None
        self.llm = TensorZeroClient()
        self.store = LearningStore()
        self.running = False

    async def connect(self) -> None:
        """Connect to NATS server."""
        if not NATS_AVAILABLE:
            print("[MonitorAgent] NATS not available, running in mock mode")
            return

        try:
            self.nc = await nats.connect(self.nats_url)
            print(f"[MonitorAgent] Connected to NATS at {self.nats_url}")
        except Exception as e:
            print(f"[MonitorAgent] Failed to connect to NATS: {e}")

    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            print("[MonitorAgent] Disconnected from NATS")

    async def handle_tool_executed(self, msg) -> None:
        """Handle Claude Code tool execution events."""
        try:
            data = json.loads(msg.data.decode())
            tool_name = data.get("tool", "unknown")
            result = data.get("result", {})
            success = data.get("success", True)

            # Extract learning from tool execution
            if tool_name.startswith("n8n_"):
                learning = {
                    "type": "tool_execution",
                    "tool": tool_name,
                    "success": success,
                    "context": data.get("context", ""),
                }
                self.store.add_learning(learning)

                # Use LLM to analyze patterns
                if len(self.store.learnings) % 10 == 0:
                    await self._analyze_patterns()

            print(f"[MonitorAgent] Tracked tool: {tool_name} (success: {success})")
        except Exception as e:
            print(f"[MonitorAgent] Error handling tool event: {e}")

    async def handle_workflow_executed(self, msg) -> None:
        """Handle n8n workflow execution events."""
        try:
            data = json.loads(msg.data.decode())
            workflow_id = data.get("workflow_id", "unknown")
            workflow_name = data.get("workflow_name", "unknown")
            status = data.get("status", "unknown")
            execution_time = data.get("execution_time_ms", 0)

            outcome = {
                "type": "workflow_execution",
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "status": status,
                "execution_time_ms": execution_time,
                "error": data.get("error"),
            }
            self.store.add_execution_outcome(outcome)

            print(f"[MonitorAgent] Tracked workflow: {workflow_name} ({status})")
        except Exception as e:
            print(f"[MonitorAgent] Error handling workflow event: {e}")

    async def handle_review_completed(self, msg) -> None:
        """Handle code review completion events."""
        try:
            data = json.loads(msg.data.decode())
            pr_number = data.get("pr_number", "unknown")
            review_result = data.get("result", "unknown")
            comments = data.get("comments", [])

            feedback = {
                "type": "code_review",
                "pr_number": pr_number,
                "result": review_result,
                "comment_count": len(comments),
                "key_feedback": [c.get("body", "")[:200] for c in comments[:5]],
            }
            self.store.add_review_feedback(feedback)

            # Extract learnings from review feedback
            if comments:
                await self._extract_review_learnings(comments)

            print(f"[MonitorAgent] Tracked review: PR #{pr_number} ({review_result})")
        except Exception as e:
            print(f"[MonitorAgent] Error handling review event: {e}")

    async def _analyze_patterns(self) -> None:
        """Use LLM to analyze execution patterns."""
        recent = self.store.get_recent_learnings(20)
        if not recent:
            return

        system_prompt = """You are an automation pattern analyst.
Analyze tool execution patterns and identify:
1. Common successful patterns
2. Failure patterns to avoid
3. Optimization opportunities
Be concise and actionable."""

        prompt = f"""Analyze these recent tool executions:
{json.dumps(recent, indent=2)}

What patterns do you see? What can be improved?"""

        analysis = await self.llm.chat(prompt, system_prompt=system_prompt)
        self.store.add_learning({
            "type": "pattern_analysis",
            "analysis": analysis,
        })
        print(f"[MonitorAgent] Pattern analysis: {analysis[:200]}...")

    async def _extract_review_learnings(self, comments: List[Dict[str, Any]]) -> None:
        """Extract learnings from code review comments."""
        system_prompt = """You are a code review learning extractor.
Extract actionable learnings from code review feedback.
Focus on:
1. Common issues to avoid
2. Best practices mentioned
3. Automation opportunities
Be concise."""

        comment_texts = [c.get("body", "") for c in comments if c.get("body")]
        if not comment_texts:
            return

        prompt = f"""Extract learnings from these code review comments:
{json.dumps(comment_texts[:10], indent=2)}

What should we learn and remember?"""

        learnings = await self.llm.chat(prompt, system_prompt=system_prompt)
        self.store.add_learning({
            "type": "review_learning",
            "learnings": learnings,
        })
        print(f"[MonitorAgent] Review learnings extracted: {learnings[:200]}...")

    async def subscribe_all(self) -> None:
        """Subscribe to all relevant NATS subjects."""
        if not self.nc:
            print("[MonitorAgent] Not connected to NATS, skipping subscriptions")
            return

        subjects = [
            ("claude.code.tool.executed.v1", self.handle_tool_executed),
            ("n8n.workflow.executed.v1", self.handle_workflow_executed),
            ("code.review.completed.v1", self.handle_review_completed),
        ]

        for subject, handler in subjects:
            await self.nc.subscribe(subject, cb=handler)
            print(f"[MonitorAgent] Subscribed to: {subject}")

    async def run(self) -> None:
        """Run the monitor agent."""
        self.running = True
        await self.connect()
        await self.subscribe_all()

        print("[MonitorAgent] Running... Press Ctrl+C to stop")

        while self.running:
            await asyncio.sleep(1)

        await self.disconnect()

    def stop(self) -> None:
        """Stop the monitor agent."""
        self.running = False
        print("[MonitorAgent] Stopping...")


async def main() -> None:
    """Main entry point."""
    agent = MonitorAgent()

    # Handle signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        agent.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
