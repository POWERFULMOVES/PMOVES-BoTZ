"""
Agent Card Generation for PMOVES-BoTZ.

Builds the Agent Card (/.well-known/agent.json) from:
- MCP Catalog configuration
- Gateway upstream server definitions
- Runtime capability discovery

Reference: docs/agents/AI Agent Integration and Best Practices.md (Section 3.2.1)
"""

import os
from typing import Any, Dict, List, Optional

from .types import AgentCard, AgentCapability, AgentSkill


# Default PMOVES-BoTZ Agent Card configuration
DEFAULT_AGENT_NAME = "PMOVES-BoTZ Gateway"
DEFAULT_AGENT_VERSION = "2.0.0"
DEFAULT_DESCRIPTION = """
PMOVES-BoTZ Unified Agent Gateway - A multi-capability agent providing:
- Document processing and conversion (Docling)
- Persistent memory and reasoning (Cipher Memory)
- Secure code execution (E2B Sandbox)
- Vision-language processing (VL Sentinel)
- API testing automation (Postman)
- Workflow automation (n8n)
- Infrastructure management (Hostinger)
- Discord channel reading and message retrieval

Part of the PMOVES.AI agentic ecosystem.
"""


def build_capabilities_from_upstream(upstream_servers: Dict[str, Dict]) -> List[AgentCapability]:
    """Build capability list from upstream MCP server definitions."""
    capabilities = []

    capability_map = {
        "n8n-agent": AgentCapability(
            name="workflow_automation",
            description="Create and execute n8n workflows for process automation"
        ),
        "hostinger": AgentCapability(
            name="infrastructure_management",
            description="Manage VPS, DNS, and domain configurations via Hostinger"
        ),
        "cipher-memory": AgentCapability(
            name="persistent_memory",
            description="Store and recall information with dual-layer memory system"
        ),
        "e2b": AgentCapability(
            name="code_execution",
            description="Execute Python and JavaScript code in secure sandboxed environments"
        ),
        "vl-sentinel": AgentCapability(
            name="vision_language",
            description="Analyze images with visual grounding and OCR capabilities"
        ),
        "docling": AgentCapability(
            name="document_processing",
            description="Convert and extract data from PDF, DOCX, HTML, and images"
        ),
        "postman": AgentCapability(
            name="api_testing",
            description="Execute API collections and manage request automation"
        ),
        "discord": AgentCapability(
            name="discord_channel_reader",
            description="Read and search Discord channel message history"
        ),
    }

    for server_name in upstream_servers:
        if server_name in capability_map:
            capabilities.append(capability_map[server_name])

    return capabilities


def build_skills_from_tools(tools: List[Dict]) -> List[AgentSkill]:
    """Build skill definitions from MCP tools list."""
    skills = []

    for tool in tools:
        tool_name = tool.get("name", tool.get("id", "unknown"))
        server = tool.get("_server", "gateway")

        skill = AgentSkill(
            id=f"{server}:{tool_name}",
            name=tool_name,
            description=tool.get("description", f"Execute {tool_name} tool"),
            input_schema=tool.get("inputSchema", {}),
            tags=[server, "mcp-tool"],
        )
        skills.append(skill)

    return skills


def build_agent_card(
    upstream_servers: Dict[str, Dict],
    tools: Optional[List[Dict]] = None,
    name: Optional[str] = None,
    version: Optional[str] = None,
    description: Optional[str] = None,
) -> AgentCard:
    """
    Build complete Agent Card from gateway configuration.

    Args:
        upstream_servers: Dict of upstream MCP server configurations
        tools: Optional list of discovered tools
        name: Optional custom agent name
        version: Optional custom version
        description: Optional custom description

    Returns:
        AgentCard ready for JSON serialization
    """
    capabilities = build_capabilities_from_upstream(upstream_servers)
    skills = build_skills_from_tools(tools or [])

    # Add core gateway capabilities
    capabilities.insert(0, AgentCapability(
        name="mcp_gateway",
        description="Unified MCP tool routing and aggregation"
    ))

    # Add A2A capability
    capabilities.append(AgentCapability(
        name="a2a_protocol",
        description="Agent-to-Agent protocol for task delegation and collaboration"
    ))

    return AgentCard(
        name=name or os.environ.get("AGENT_NAME", DEFAULT_AGENT_NAME),
        description=description or DEFAULT_DESCRIPTION.strip(),
        version=version or os.environ.get("AGENT_VERSION", DEFAULT_AGENT_VERSION),
        capabilities=capabilities,
        skills=skills,
        input_modalities=["text/plain", "application/json", "multipart/form-data"],
        output_modalities=["text/plain", "application/json", "text/markdown", "text/event-stream"],
        authentication={
            "type": os.environ.get("A2A_AUTH_TYPE", "none"),
            "description": "Authentication required for task execution",
        },
        metadata={
            "protocol_version": "a2a/1.0",
            "ecosystem": "pmoves.ai",
            "deployment_mode": os.environ.get("PMOVES_DOCKED_MODE", "standalone"),
            "mcp_gateway_port": int(os.environ.get("PORT", "2091")),
            "a2a_port": int(os.environ.get("A2A_PORT", "7000")),
        },
    )


# Cached agent card instance
_cached_card: Optional[AgentCard] = None


def get_agent_card(
    upstream_servers: Dict[str, Dict],
    tools: Optional[List[Dict]] = None,
    force_rebuild: bool = False,
) -> AgentCard:
    """
    Get or build the Agent Card (with caching).

    Args:
        upstream_servers: Dict of upstream MCP server configurations
        tools: Optional list of discovered tools
        force_rebuild: Force rebuild even if cached

    Returns:
        AgentCard instance
    """
    global _cached_card

    if _cached_card is None or force_rebuild:
        _cached_card = build_agent_card(upstream_servers, tools)

    return _cached_card
