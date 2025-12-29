"""
PMOVES Subagents

Specialized agents for specific task domains:
- Researcher: Deep research via SupaSerch + Hi-RAG + DeepResearch
- CodeReviewer: Security-focused code analysis
- MediaProcessor: Video/audio processing workflows
- KnowledgeManager: Hi-RAG knowledge base operations

Each subagent can be used standalone or orchestrated by PMOVESAgent.

Usage:
    from pmoves_botz.features.agent_sdk.subagents import (
        ResearcherAgent,
        CodeReviewerAgent,
        MediaProcessorAgent,
        KnowledgeManagerAgent,
    )

    async with ResearcherAgent("research-1") as agent:
        results = await agent.research("quantum computing trends 2025")
"""

from .researcher import ResearcherAgent
from .code_reviewer import CodeReviewerAgent
from .media_processor import MediaProcessorAgent
from .knowledge_manager import KnowledgeManagerAgent

__all__ = [
    "ResearcherAgent",
    "CodeReviewerAgent",
    "MediaProcessorAgent",
    "KnowledgeManagerAgent",
]
