#!/usr/bin/env python3
"""
PMOVES Skills MCP Server

Provides skill management capabilities for all BoTZ agents via MCP.
Integrates with Cipher Memory for skill persistence and learning.

Skills are instruction-based SKILL.md files that teach agents how to perform tasks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from mcp import Tool
from mcp.server import Server
from mcp.types import CallToolResult, TextContent
import mcp.server.stdio


class SkillManager:
    """Manages skill loading, indexing, and retrieval.

    Skills are stored in multiple directories as SKILL.md files with
    YAML frontmatter containing metadata (name, description, license).
    Supports multiple skill repositories for aggregated indexing.
    """

    # Default skill sources to search: (name, path, structure_type)
    # structure_type: "flat" = skill-name/SKILL.md, "nested" = pkg/skills/skill-name/, "root" = SKILL.md at path
    DEFAULT_SKILL_SOURCES = [
        ("library", "library", "flat"),
        ("anthropics", "repos/anthropics-skills/skills", "flat"),
        ("huggingface", "repos/huggingface-skills", "nested"),
        ("skillcreator", "repos/skillcreator-skills/skills", "flat"),
        ("aws", "repos/aws-skills/skills", "flat"),
        ("playwright", "repos/playwright-skill/skills", "flat"),
        ("d3js", "repos/d3js-skill", "root"),
        ("epub", "repos/epub-skill/markdown-to-epub", "root"),
        ("obsidian", "repos/obsidian-plugin-skill/.claude/skills", "flat"),
        ("marketplace-code", "repos/skills-marketplace/code-operations-plugin/skills", "flat"),
        ("marketplace-eng", "repos/skills-marketplace/engineering-workflow-plugin/skills", "flat"),
        ("marketplace-prod", "repos/skills-marketplace/productivity-skills-plugin/skills", "flat"),
        ("marketplace-visual", "repos/skills-marketplace/visual-documentation-plugin/skills", "flat"),
    ]

    def __init__(self, skills_path: Optional[str] = None, sources: Optional[List[tuple]] = None) -> None:
        """Initialize skill manager.

        Args:
            skills_path: Base path for skills (contains library/ and repos/)
            sources: List of (source_name, relative_path) tuples to index
        """
        self.base_path = Path(skills_path) if skills_path else Path(__file__).parent
        self.sources = sources or self.DEFAULT_SKILL_SOURCES
        self._skill_index: Dict[str, Dict[str, Any]] = {}
        self._build_index()

    def _parse_skill_file(self, skill_path: Path, source: str = "unknown") -> Dict[str, Any]:
        """Parse a SKILL.md file and extract metadata + instructions.

        Args:
            skill_path: Path to SKILL.md file
            source: Name of the skill source repository

        Returns:
            Dict with name, description, instructions, path, and source
        """
        content = skill_path.read_text(encoding="utf-8")

        # Parse YAML frontmatter
        frontmatter = {}
        instructions = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    instructions = parts[2].strip()
                except yaml.YAMLError:
                    pass

        return {
            "name": frontmatter.get("name", skill_path.parent.name),
            "description": frontmatter.get("description", ""),
            "license": frontmatter.get("license", ""),
            "instructions": instructions,
            "path": str(skill_path.parent),
            "files": self._list_skill_files(skill_path.parent),
            "source": source,
        }

    def _list_skill_files(self, skill_dir: Path) -> List[str]:
        """List all files in a skill directory.

        Args:
            skill_dir: Path to skill directory

        Returns:
            List of relative file paths
        """
        files = []
        for item in skill_dir.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                files.append(str(item.relative_to(skill_dir)))
        return files

    def _index_skill_directory(self, skill_dir: Path, source: str) -> None:
        """Index a single skill directory.

        Args:
            skill_dir: Path to skill directory
            source: Name of the skill source
        """
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            try:
                skill_data = self._parse_skill_file(skill_file, source)
                skill_name = skill_data["name"]
                # Prefer library skills over repo skills (allow override)
                if skill_name not in self._skill_index or source == "library":
                    self._skill_index[skill_name] = skill_data
            except Exception as e:
                print(f"Warning: Failed to parse {skill_file}: {e}")

    def _build_index(self) -> None:
        """Build index of all available skills from all sources."""
        self._skill_index = {}

        for source_entry in self.sources:
            # Support (name, path, structure_type) format
            if len(source_entry) == 3:
                source_name, relative_path, structure_type = source_entry
            else:
                source_name, relative_path = source_entry
                structure_type = "flat"

            source_path = self.base_path / relative_path
            if not source_path.exists():
                continue

            if structure_type == "root":
                # Single skill at root: SKILL.md directly in source_path
                if (source_path / "SKILL.md").exists():
                    self._index_skill_directory(source_path, source_name)
            elif structure_type == "nested":
                # Nested structure: pkg/skills/skill-name/SKILL.md
                for pkg in source_path.iterdir():
                    if not pkg.is_dir() or pkg.name.startswith("."):
                        continue
                    skills_dir = pkg / "skills"
                    if skills_dir.exists():
                        for skill_dir in skills_dir.iterdir():
                            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                                self._index_skill_directory(skill_dir, source_name)
            else:  # flat
                # Flat structure: skill-name/SKILL.md directly in source_path
                for item in source_path.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        if (item / "SKILL.md").exists():
                            self._index_skill_directory(item, source_name)

    def list_skills(self) -> List[Dict[str, str]]:
        """List all available skills with names, descriptions, and sources.

        Returns:
            List of skill summaries (name, description, source)
        """
        return [
            {"name": skill["name"], "description": skill["description"], "source": skill["source"]}
            for skill in sorted(self._skill_index.values(), key=lambda x: x["name"])
        ]

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Get full skill details including instructions.

        Args:
            name: Skill name to retrieve

        Returns:
            Full skill data or None if not found
        """
        return self._skill_index.get(name)

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """Search skills by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching skills
        """
        query_lower = query.lower()
        results = []

        for skill in self._skill_index.values():
            score = 0
            name_lower = skill["name"].lower()
            desc_lower = skill["description"].lower()

            # Exact name match
            if query_lower == name_lower:
                score = 100
            # Name contains query
            elif query_lower in name_lower:
                score = 80
            # Description contains query
            elif query_lower in desc_lower:
                score = 60
            # Any word matches
            else:
                query_words = set(query_lower.split())
                name_words = set(name_lower.split("-"))
                desc_words = set(re.findall(r'\w+', desc_lower))

                name_matches = query_words & name_words
                desc_matches = query_words & desc_words

                if name_matches:
                    score = 40 + len(name_matches) * 10
                elif desc_matches:
                    score = 20 + len(desc_matches) * 5

            if score > 0:
                results.append({**skill, "relevance": score})

        return sorted(results, key=lambda x: x["relevance"], reverse=True)

    def get_skill_file(self, skill_name: str, file_path: str) -> Optional[str]:
        """Get contents of a specific file from a skill.

        Args:
            skill_name: Name of the skill
            file_path: Relative path to file within skill

        Returns:
            File contents or None if not found
        """
        skill = self._skill_index.get(skill_name)
        if not skill:
            return None

        full_path = Path(skill["path"]) / file_path
        if full_path.exists() and full_path.is_file():
            try:
                return full_path.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def refresh_index(self) -> int:
        """Refresh the skill index.

        Returns:
            Number of skills indexed
        """
        self._build_index()
        return len(self._skill_index)


class SkillServer:
    """MCP server providing skill management tools.

    Tools:
    - skill_list: List all available skills
    - skill_get: Get full skill instructions
    - skill_search: Search skills by keyword
    - skill_file: Get a specific file from a skill
    - skill_refresh: Refresh the skill index
    """

    def __init__(self) -> None:
        """Initialize MCP server with skill manager."""
        self.server = Server("pmoves-skills")
        self.manager = SkillManager()

    def setup_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="skill_list",
                    description="List all available agent skills with names and descriptions",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="skill_get",
                    description="Get full skill instructions by name. Returns the complete SKILL.md content and list of associated files.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name of the skill to retrieve"
                            }
                        },
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="skill_search",
                    description="Search skills by keyword in name or description. Returns matching skills ranked by relevance.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'document', 'testing', 'mcp')"
                            }
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="skill_file",
                    description="Get contents of a specific file from a skill (e.g., templates, scripts, reference docs)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "skill_name": {
                                "type": "string",
                                "description": "Name of the skill"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to the file within the skill"
                            }
                        },
                        "required": ["skill_name", "file_path"],
                    },
                ),
                Tool(
                    name="skill_refresh",
                    description="Refresh the skill index to pick up newly added skills",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            try:
                if name == "skill_list":
                    skills = self.manager.list_skills()
                    output = json.dumps(skills, indent=2)
                    return CallToolResult(
                        content=[TextContent(type="text", text=output)],
                        isError=False
                    )

                if name == "skill_get":
                    skill = self.manager.get_skill(arguments["name"])
                    if skill:
                        output = json.dumps(skill, indent=2)
                        return CallToolResult(
                            content=[TextContent(type="text", text=output)],
                            isError=False
                        )
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Skill not found: {arguments['name']}")],
                        isError=True
                    )

                if name == "skill_search":
                    results = self.manager.search_skills(arguments["query"])
                    # Return summary without full instructions for search results
                    summary = [
                        {"name": r["name"], "description": r["description"], "source": r["source"], "relevance": r["relevance"]}
                        for r in results
                    ]
                    output = json.dumps(summary, indent=2)
                    return CallToolResult(
                        content=[TextContent(type="text", text=output)],
                        isError=False
                    )

                if name == "skill_file":
                    content = self.manager.get_skill_file(
                        arguments["skill_name"],
                        arguments["file_path"]
                    )
                    if content is not None:
                        return CallToolResult(
                            content=[TextContent(type="text", text=content)],
                            isError=False
                        )
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"File not found: {arguments['file_path']} in skill {arguments['skill_name']}")],
                        isError=True
                    )

                if name == "skill_refresh":
                    count = self.manager.refresh_index()
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Refreshed index: {count} skills available")],
                        isError=False
                    )

                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                    isError=True
                )

            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {e}")],
                    isError=True
                )


async def run_stdio_server(server: SkillServer) -> None:
    """Run the skill server with stdio transport."""
    server.setup_handlers()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for the skill server."""
    parser = argparse.ArgumentParser(description="PMOVES Skills MCP Server")
    parser.add_argument("--transport", choices=["stdio"], default="stdio")
    parser.add_argument("--skills-path", help="Path to skills library")
    args = parser.parse_args()

    server = SkillServer()
    if args.skills_path:
        server.manager = SkillManager(args.skills_path)

    asyncio.run(run_stdio_server(server))


if __name__ == "__main__":
    main()
