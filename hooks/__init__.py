"""
PMOVES-BoTZ Security Hooks
==========================

Pre-execution validation and probabilistic scanning for AI agent safety.

Hooks:
  - pre_command.py: Deterministic regex-based command validation
  - prompt_scan.py: LLM-based probabilistic prompt/command analysis

Reference: docs/agents/Aligning AI Agents with Indy Dev Dan.md
"""

__version__ = "1.0.0"
__author__ = "POWERFULMOVES"
