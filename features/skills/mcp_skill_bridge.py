#!/usr/bin/env python3
"""
MCP-Skills Bridge

Combines agent skills with MCP tools for enhanced capabilities.
This module provides utilities to:
1. Match skills with appropriate MCP tools
2. Generate tool chains from skill instructions
3. Execute skill-guided workflows via MCP

Skills provide the "how" (instructions) while MCP tools provide the "what" (capabilities).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Skill-to-MCP tool mappings
SKILL_TOOL_MAPPINGS = {
    # Document skills -> docling + e2b
    "docx": ["docling:convert_document", "e2b:sandbox_run"],
    "xlsx": ["docling:convert_document", "docling:extract_tables", "e2b:sandbox_run"],
    "pptx": ["docling:convert_document", "e2b:sandbox_run"],
    "pdf": ["docling:convert_document", "docling:extract_tables"],
    "markdown-to-epub": ["e2b:sandbox_run"],

    # Visualization skills -> e2b (sandbox for rendering)
    "d3js-skill": ["e2b:sandbox_run", "e2b:sandbox_exec"],
    "algorithmic-art": ["e2b:sandbox_run"],
    "canvas-design": ["e2b:sandbox_run"],
    "architecture-diagram-creator": ["e2b:sandbox_run"],
    "flowchart-creator": ["e2b:sandbox_run"],
    "dashboard-creator": ["e2b:sandbox_run"],
    "timeline-creator": ["e2b:sandbox_run"],

    # Testing skills -> e2b + vl-sentinel
    "webapp-testing": ["e2b:sandbox_run", "vl-sentinel:vl_guide"],
    "playwright-skill": ["e2b:sandbox_run", "e2b:sandbox_exec"],
    "qa-regression": ["e2b:sandbox_run"],

    # Development skills -> e2b
    "mcp-builder": ["e2b:sandbox_run", "e2b:sandbox_exec"],
    "python-development": ["e2b:sandbox_run"],
    "javascript-typescript": ["e2b:sandbox_run"],
    "backend-development": ["e2b:sandbox_run"],
    "code-execution": ["e2b:sandbox_run", "e2b:sandbox_exec"],

    # AWS skills -> n8n (workflow automation)
    "aws-cdk-development": ["n8n-agent:n8n_execute_workflow", "e2b:sandbox_run"],
    "aws-serverless-eda": ["n8n-agent:n8n_execute_workflow"],
    "aws-cost-operations": ["n8n-agent:n8n_execute_workflow"],

    # Git/workflow skills -> n8n
    "git-pushing": ["n8n-agent:n8n_execute_workflow"],
    "changelog-generator": ["n8n-agent:n8n_execute_workflow"],

    # Image skills -> vl-sentinel
    "image-enhancer": ["vl-sentinel:vl_guide", "e2b:sandbox_run"],

    # API skills -> postman
    "llm-application-dev": ["postman:*", "e2b:sandbox_run"],
}

# Tool categories for skill matching
TOOL_CATEGORIES = {
    "code_execution": ["e2b:sandbox_run", "e2b:sandbox_exec"],
    "document_processing": ["docling:convert_document", "docling:extract_tables"],
    "visual_analysis": ["vl-sentinel:vl_guide"],
    "workflow_automation": ["n8n-agent:n8n_execute_workflow", "n8n-agent:n8n_create_workflow"],
    "api_testing": ["postman:*"],
    "memory": ["cipher-memory:store_memory", "cipher-memory:search_memory"],
}


@dataclass
class SkillToolChain:
    """Represents a skill with its associated MCP tools."""
    skill_name: str
    skill_description: str
    mcp_tools: List[str]
    workflow_steps: List[str]


def get_tools_for_skill(skill_name: str) -> List[str]:
    """Get recommended MCP tools for a skill.

    Args:
        skill_name: Name of the skill

    Returns:
        List of MCP tool identifiers
    """
    # Direct mapping
    if skill_name in SKILL_TOOL_MAPPINGS:
        return SKILL_TOOL_MAPPINGS[skill_name]

    # Fallback: infer from skill name
    tools = []
    name_lower = skill_name.lower()

    if any(kw in name_lower for kw in ["code", "python", "javascript", "typescript", "dev"]):
        tools.extend(TOOL_CATEGORIES["code_execution"])
    if any(kw in name_lower for kw in ["doc", "pdf", "xlsx", "docx", "pptx"]):
        tools.extend(TOOL_CATEGORIES["document_processing"])
    if any(kw in name_lower for kw in ["image", "visual", "diagram", "chart"]):
        tools.extend(TOOL_CATEGORIES["visual_analysis"])
    if any(kw in name_lower for kw in ["workflow", "automat", "git", "aws"]):
        tools.extend(TOOL_CATEGORIES["workflow_automation"])
    if any(kw in name_lower for kw in ["api", "test"]):
        tools.extend(TOOL_CATEGORIES["api_testing"])

    # Always include memory for learning
    tools.extend(TOOL_CATEGORIES["memory"])

    return list(set(tools))


def extract_workflow_steps(skill_instructions: str) -> List[str]:
    """Extract numbered workflow steps from skill instructions.

    Args:
        skill_instructions: Raw skill markdown instructions

    Returns:
        List of workflow step descriptions
    """
    steps = []

    # Match numbered lists (1. 2. 3. or 1) 2) 3))
    patterns = [
        r'^\s*(\d+)[.)]\s*(.+)$',  # 1. or 1)
        r'^\s*[-*]\s*(.+)$',       # - or *
    ]

    for line in skill_instructions.split('\n'):
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                step = match.groups()[-1].strip()
                if step and len(step) > 10:  # Filter out short items
                    steps.append(step)
                break

    return steps[:20]  # Limit to 20 steps


def create_tool_chain(
    skill_name: str,
    skill_description: str,
    skill_instructions: str
) -> SkillToolChain:
    """Create a tool chain from a skill.

    Args:
        skill_name: Skill identifier
        skill_description: Short description
        skill_instructions: Full instructions markdown

    Returns:
        SkillToolChain with tools and workflow steps
    """
    return SkillToolChain(
        skill_name=skill_name,
        skill_description=skill_description,
        mcp_tools=get_tools_for_skill(skill_name),
        workflow_steps=extract_workflow_steps(skill_instructions)
    )


def generate_execution_plan(
    skill_chain: SkillToolChain,
    user_request: str
) -> Dict[str, Any]:
    """Generate an execution plan combining skill instructions with MCP tools.

    Args:
        skill_chain: SkillToolChain from a skill
        user_request: User's specific request

    Returns:
        Execution plan dict with steps and tool calls
    """
    plan = {
        "skill": skill_chain.skill_name,
        "description": skill_chain.skill_description,
        "user_request": user_request,
        "available_tools": skill_chain.mcp_tools,
        "execution_steps": [],
    }

    # Map workflow steps to tools
    for i, step in enumerate(skill_chain.workflow_steps):
        step_plan = {
            "step": i + 1,
            "description": step,
            "suggested_tools": [],
        }

        # Match step to tools based on keywords
        step_lower = step.lower()
        if any(kw in step_lower for kw in ["run", "execute", "code", "script"]):
            step_plan["suggested_tools"].append("e2b:sandbox_run")
        if any(kw in step_lower for kw in ["parse", "extract", "convert", "document"]):
            step_plan["suggested_tools"].append("docling:convert_document")
        if any(kw in step_lower for kw in ["visual", "image", "check", "verify"]):
            step_plan["suggested_tools"].append("vl-sentinel:vl_guide")
        if any(kw in step_lower for kw in ["store", "save", "remember"]):
            step_plan["suggested_tools"].append("cipher-memory:store_memory")
        if any(kw in step_lower for kw in ["automate", "workflow"]):
            step_plan["suggested_tools"].append("n8n-agent:n8n_execute_workflow")

        plan["execution_steps"].append(step_plan)

    return plan


def get_skill_mcp_integration_prompt(skill_name: str, skill_data: Dict[str, Any]) -> str:
    """Generate a prompt for using a skill with MCP tools.

    Args:
        skill_name: Skill identifier
        skill_data: Full skill data including instructions

    Returns:
        Integration prompt string
    """
    tools = get_tools_for_skill(skill_name)

    prompt = f"""# Using {skill_name} Skill with MCP Tools

## Skill Description
{skill_data.get('description', 'No description')}

## Available MCP Tools
{chr(10).join(f'- {tool}' for tool in tools)}

## Integration Pattern

1. **Load skill instructions**: Use `skill_get("{skill_name}")` to get full instructions
2. **Follow skill workflow**: Execute each step using appropriate MCP tools
3. **Use sandbox for code**: Run any code snippets via `e2b:sandbox_run`
4. **Store learnings**: Save patterns to `cipher-memory:store_memory`

## Example Workflow

```python
# 1. Get skill instructions
skill = skill_get("{skill_name}")

# 2. For code execution steps
result = e2b_sandbox_run(code=generated_code, language="python")

# 3. For document processing
doc_content = docling_convert_document(file_path)

# 4. Store successful patterns
cipher_store_memory(content=f"Successfully used {skill_name}: {{outcome}}")
```

## Skill Files Available
{chr(10).join(f'- {f}' for f in skill_data.get('files', [])[:10])}

Use `skill_file("{skill_name}", "filename")` to access templates and references.
"""
    return prompt


if __name__ == "__main__":
    # Demo: Show tool mappings
    print("Skill-MCP Tool Mappings:\n")
    for skill, tools in sorted(SKILL_TOOL_MAPPINGS.items()):
        print(f"  {skill}:")
        for tool in tools:
            print(f"    - {tool}")
