#!/usr/bin/env python3
"""
Skill Loader for Cipher Memory

Imports skills from the library into Cipher Memory for cross-session
learning and pattern storage. Run this to populate Cipher with skill knowledge.

Usage:
    python skill_loader.py [--cipher-url URL] [--all | --skill NAME]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


def parse_skill_file(skill_path: Path) -> Dict[str, Any]:
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
        "instructions": instructions,
    }


def get_all_skills(library_path: Path) -> List[Dict[str, Any]]:
    """Get all skills from the library."""
    skills = []
    for skill_dir in library_path.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skills.append(parse_skill_file(skill_file))
    return skills


def store_skill_in_cipher(skill: Dict[str, Any], cipher_command: List[str]) -> bool:
    """Store a skill in Cipher Memory.

    Args:
        skill: Parsed skill data
        cipher_command: Command to invoke cipher CLI

    Returns:
        True if successful
    """
    # Create skill knowledge entry
    skill_entry = f"""
SKILL: {skill['name']}
DESCRIPTION: {skill['description']}

INSTRUCTIONS:
{skill['instructions'][:2000]}...  # Truncated for storage
"""

    try:
        result = subprocess.run(
            cipher_command + ["--mode", "cli", f"Store agent skill: {skill_entry}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"  Stored skill: {skill['name']}")
            return True
        else:
            print(f"  Failed to store {skill['name']}: {result.stderr}")
            return False
    except Exception as e:
        print(f"  Error storing {skill['name']}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Load skills into Cipher Memory")
    parser.add_argument(
        "--cipher-path",
        default=str(Path(__file__).parent.parent / "cipher" / "pmoves_cipher"),
        help="Path to cipher installation"
    )
    parser.add_argument(
        "--library",
        default=str(Path(__file__).parent / "library"),
        help="Path to skills library"
    )
    parser.add_argument("--all", action="store_true", help="Load all skills")
    parser.add_argument("--skill", help="Load specific skill by name")
    parser.add_argument("--list", action="store_true", help="List available skills")
    args = parser.parse_args()

    library_path = Path(args.library)
    if not library_path.exists():
        print(f"Error: Skills library not found at {library_path}")
        sys.exit(1)

    skills = get_all_skills(library_path)

    if args.list:
        print(f"Available skills ({len(skills)}):\n")
        for skill in skills:
            print(f"  - {skill['name']}: {skill['description'][:60]}...")
        return

    if not (args.all or args.skill):
        parser.print_help()
        return

    # Cipher CLI command
    cipher_binary = Path(args.cipher_path) / "dist" / "src" / "app" / "index.cjs"
    if not cipher_binary.exists():
        print(f"Warning: Cipher binary not found at {cipher_binary}")
        print("Skills will be indexed but not stored in Cipher Memory")
        cipher_command = None
    else:
        cipher_command = ["node", str(cipher_binary)]

    # Load skills
    if args.all:
        print(f"Loading {len(skills)} skills into Cipher Memory...\n")
        success_count = 0
        for skill in skills:
            if cipher_command:
                if store_skill_in_cipher(skill, cipher_command):
                    success_count += 1
            else:
                print(f"  Indexed: {skill['name']}")
                success_count += 1
        print(f"\nCompleted: {success_count}/{len(skills)} skills loaded")

    elif args.skill:
        skill = next((s for s in skills if s["name"] == args.skill), None)
        if skill:
            if cipher_command:
                store_skill_in_cipher(skill, cipher_command)
            else:
                print(f"Indexed: {skill['name']}")
        else:
            print(f"Skill not found: {args.skill}")
            sys.exit(1)


if __name__ == "__main__":
    main()
