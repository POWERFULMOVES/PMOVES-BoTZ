#!/usr/bin/env python3
"""
Sync Skills to Claude Code Directory

Copies all skills from repos to the .claude/skills directory for
direct Claude Code access. Run this after adding new skill repos.

Usage:
    python sync_skills.py [--target TARGET_DIR]
"""

import argparse
import shutil
from pathlib import Path


def sync_skills(base_path: Path, target_path: Path) -> int:
    """Sync all skills to target directory.

    Args:
        base_path: Base path containing library/ and repos/
        target_path: Target directory for synced skills

    Returns:
        Number of skills synced
    """
    # Skill sources to sync
    # Format: (source_name, path, structure_type)
    # structure_type: "flat" = skill-name/SKILL.md, "nested" = pkg/skills/skill-name/, "root" = SKILL.md at path
    sources = [
        ("library", base_path / "library", "flat"),
        ("anthropics", base_path / "repos" / "anthropics-skills" / "skills", "flat"),
        ("huggingface", base_path / "repos" / "huggingface-skills", "nested"),
        ("skillcreator", base_path / "repos" / "skillcreator-skills" / "skills", "flat"),
        ("aws", base_path / "repos" / "aws-skills" / "skills", "flat"),
        ("playwright", base_path / "repos" / "playwright-skill" / "skills", "flat"),
        ("d3js", base_path / "repos" / "d3js-skill", "root"),
        ("epub", base_path / "repos" / "epub-skill" / "markdown-to-epub", "root"),
        ("obsidian", base_path / "repos" / "obsidian-plugin-skill" / ".claude" / "skills", "flat"),
        ("marketplace-code", base_path / "repos" / "skills-marketplace" / "code-operations-plugin" / "skills", "flat"),
        ("marketplace-eng", base_path / "repos" / "skills-marketplace" / "engineering-workflow-plugin" / "skills", "flat"),
        ("marketplace-prod", base_path / "repos" / "skills-marketplace" / "productivity-skills-plugin" / "skills", "flat"),
        ("marketplace-visual", base_path / "repos" / "skills-marketplace" / "visual-documentation-plugin" / "skills", "flat"),
    ]

    # Clear and recreate target (handle Windows/OneDrive permission issues)
    if target_path.exists():
        try:
            shutil.rmtree(target_path)
        except PermissionError:
            # On Windows, try removing files individually
            import time
            for item in target_path.rglob("*"):
                if item.is_file():
                    try:
                        item.unlink()
                    except PermissionError:
                        time.sleep(0.1)
                        item.unlink()
            for item in sorted(target_path.rglob("*"), key=lambda x: len(str(x)), reverse=True):
                if item.is_dir():
                    try:
                        item.rmdir()
                    except (PermissionError, OSError):
                        pass
            try:
                target_path.rmdir()
            except (PermissionError, OSError):
                pass
    target_path.mkdir(parents=True, exist_ok=True)

    synced = 0
    seen_skills = set()

    def sync_skill(skill_dir: Path, source: str) -> bool:
        """Sync a single skill directory."""
        nonlocal synced
        skill_name = skill_dir.name
        if skill_name not in seen_skills:
            target_skill = target_path / skill_name
            shutil.copytree(skill_dir, target_skill)
            seen_skills.add(skill_name)
            synced += 1
            print(f"  Synced: {skill_name} ({source})")
            return True
        return False

    for source_name, source_path, structure_type in sources:
        if not source_path.exists():
            print(f"  Skipping {source_name}: path not found")
            continue

        if structure_type == "root":
            # Single skill at root: SKILL.md directly in source_path
            if (source_path / "SKILL.md").exists():
                sync_skill(source_path, source_name)
        elif structure_type == "nested":
            # Nested structures like huggingface: hf-*/skills/*/SKILL.md
            for pkg in source_path.iterdir():
                if not pkg.is_dir() or pkg.name.startswith("."):
                    continue
                skills_dir = pkg / "skills"
                if skills_dir.exists():
                    for skill_dir in skills_dir.iterdir():
                        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                            sync_skill(skill_dir, source_name)
        else:  # flat
            # Flat structure: skill-name/SKILL.md directly in source_path
            for item in source_path.iterdir():
                if not item.is_dir() or item.name.startswith("."):
                    continue
                if (item / "SKILL.md").exists():
                    sync_skill(item, source_name)

    return synced


def main():
    parser = argparse.ArgumentParser(description="Sync skills to Claude Code directory")
    parser.add_argument(
        "--target",
        default=str(Path(__file__).parent.parent.parent / ".claude" / "skills"),
        help="Target directory for synced skills"
    )
    args = parser.parse_args()

    base_path = Path(__file__).parent
    target_path = Path(args.target)

    print(f"Syncing skills from {base_path}")
    print(f"Target: {target_path}\n")

    count = sync_skills(base_path, target_path)
    print(f"\nSynced {count} skills to {target_path}")


if __name__ == "__main__":
    main()
