#!/usr/bin/env python3
"""
Test script for skills indexing.
Runs without MCP dependencies.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def parse_skill_file(skill_path: Path, source: str = "unknown") -> Dict[str, Any]:
    """Parse a SKILL.md file."""
    content = skill_path.read_text(encoding="utf-8")
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
        "source": source,
    }


def index_skills(base_path: Path) -> List[Dict[str, Any]]:
    """Index all skills from all sources."""
    sources = [
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

    skills = []
    seen = set()

    for source_name, relative_path, structure_type in sources:
        source_path = base_path / relative_path
        if not source_path.exists():
            continue

        if structure_type == "root":
            skill_file = source_path / "SKILL.md"
            if skill_file.exists():
                try:
                    skill = parse_skill_file(skill_file, source_name)
                    if skill["name"] not in seen:
                        skills.append(skill)
                        seen.add(skill["name"])
                except Exception as e:
                    print(f"  Warning: {skill_file}: {e}")
        elif structure_type == "nested":
            for pkg in source_path.iterdir():
                if not pkg.is_dir() or pkg.name.startswith("."):
                    continue
                skills_dir = pkg / "skills"
                if skills_dir.exists():
                    for skill_dir in skills_dir.iterdir():
                        skill_file = skill_dir / "SKILL.md"
                        if skill_file.exists():
                            try:
                                skill = parse_skill_file(skill_file, source_name)
                                if skill["name"] not in seen:
                                    skills.append(skill)
                                    seen.add(skill["name"])
                            except Exception as e:
                                print(f"  Warning: {skill_file}: {e}")
        else:  # flat
            for item in source_path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    skill_file = item / "SKILL.md"
                    if skill_file.exists():
                        try:
                            skill = parse_skill_file(skill_file, source_name)
                            if skill["name"] not in seen:
                                skills.append(skill)
                                seen.add(skill["name"])
                        except Exception as e:
                            print(f"  Warning: {skill_file}: {e}")

    return sorted(skills, key=lambda x: x["name"])


def main():
    base_path = Path(__file__).parent
    print("Testing Skills Indexing\n")
    print(f"Base path: {base_path}\n")

    skills = index_skills(base_path)

    print(f"Total skills indexed: {len(skills)}\n")

    # Count by source
    sources = {}
    for s in skills:
        src = s.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print("Skills by source:")
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}")

    print("\nAll skills:")
    for s in skills:
        desc = s.get("description", "")[:50]
        print(f"  - {s['name']} ({s['source']})")

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(skills)} skills from {len(sources)} sources")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
