# PMOVES BoTZ Skills Integration

This document describes the Agent Skills integration in PMOVES BoTZ, providing 71+ skills for all agents through a unified MCP server.

## Overview

Agent Skills are instruction-based guides that teach AI agents how to perform specialized tasks. Unlike code libraries, skills are text files that agents read and follow like recipes.

### Key Benefits

- **Universal Access**: All BoTZ agents can access skills via MCP Gateway
- **Multi-Source**: Skills aggregated from Anthropic, HuggingFace, SkillCreator, and community repos
- **Cipher Integration**: Skills stored in Cipher Memory for cross-session learning
- **Claude Code Support**: Skills synced to `.claude/skills/` for direct access

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PMOVES BoTZ Agents                       │
│  (Agent Zero, n8n, VL Sentinel, Docling, E2B, etc.)        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCP Gateway (:2091)                       │
│              Unified Tool Routing & Access                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐
│   Skills MCP Server │  │   Cipher Memory     │
│   (pmz-skills)      │  │   (pmz-cipher)      │
│                     │  │                     │
│ • skill_list        │  │ • Store skills      │
│ • skill_get         │  │ • Search patterns   │
│ • skill_search      │  │ • Learn outcomes    │
│ • skill_file        │  │                     │
└─────────┬───────────┘  └─────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Skills Library                           │
│  features/skills/                                          │
│  ├── library/         (16 Anthropic base skills)           │
│  └── repos/           (Git submodules)                     │
│      ├── anthropics-skills/                                │
│      ├── huggingface-skills/                               │
│      ├── skillcreator-skills/                              │
│      ├── aws-skills/                                       │
│      ├── d3js-skill/                                       │
│      ├── playwright-skill/                                 │
│      ├── obsidian-plugin-skill/                            │
│      ├── epub-skill/                                       │
│      └── skills-marketplace/                               │
└─────────────────────────────────────────────────────────────┘
```

## Available Skills (71 Total)

### Document Processing (5)
| Skill | Source | Description |
|-------|--------|-------------|
| docx | anthropics | Create, edit, analyze Word documents with tracked changes |
| xlsx | anthropics | Spreadsheet manipulation: formulas, charts, data transformations |
| pptx | anthropics | Read, generate, adjust slides, layouts, templates |
| pdf | anthropics | Extract text, tables, metadata from PDFs |
| markdown-to-epub | epub | Convert markdown documents to professional EPUB ebooks |

### Development (18)
| Skill | Source | Description |
|-------|--------|-------------|
| mcp-builder | anthropics | Build MCP servers with best practices |
| skill-creator | anthropics | Create new agent skills |
| backend-development | skillcreator | Backend development patterns |
| python-development | skillcreator | Python development best practices |
| javascript-typescript | skillcreator | JS/TS development |
| database-design | skillcreator | Database schema design |
| code-review | skillcreator | Code review workflows |
| code-refactoring | skillcreator | Code refactoring patterns |
| code-documentation | skillcreator | Documentation generation |
| llm-application-dev | skillcreator | LLM application development |
| obsidian | obsidian | Obsidian.md plugin development |
| code-execution | marketplace | Safe code execution patterns |
| code-refactor | marketplace | Advanced refactoring |
| code-transfer | marketplace | Code migration/transfer |
| file-operations | marketplace | File system operations |
| project-bootstrapper | marketplace | Project scaffolding |
| codebase-documenter | marketplace | Auto-documentation |
| code-auditor | marketplace | Security/quality audits |

### AWS & Cloud (4)
| Skill | Source | Description |
|-------|--------|-------------|
| aws-cdk-development | aws | AWS CDK best practices |
| aws-serverless-eda | aws | Serverless event-driven architecture |
| aws-cost-operations | aws | AWS cost optimization |
| aws-agentic-ai | aws | Building AI agents on AWS |

### ML/AI (5)
| Skill | Source | Description |
|-------|--------|-------------|
| model-trainer | huggingface | LLM fine-tuning and training |
| hugging-face-dataset-creator | huggingface | Dataset creation for ML |
| hugging-face-evaluation-manager | huggingface | Model evaluation orchestration |
| hf-tool-builder | huggingface | Build HuggingFace tools |
| hugging-face-paper-publisher | huggingface | Publish research papers |

### Testing & QA (4)
| Skill | Source | Description |
|-------|--------|-------------|
| webapp-testing | anthropics | Web application testing |
| qa-regression | skillcreator | QA regression testing |
| playwright-skill | playwright | Browser automation with Playwright |
| test-fixing | marketplace | Detect and fix failing tests |

### Visualization & Design (10)
| Skill | Source | Description |
|-------|--------|-------------|
| d3js-skill | d3js | D3.js charts and data visualizations |
| frontend-design | anthropics | Frontend UI/UX design |
| canvas-design | anthropics | Canvas-based visual design |
| algorithmic-art | anthropics | Generate algorithmic art |
| theme-factory | anthropics | Create themes and styles |
| architecture-diagram-creator | marketplace | System architecture diagrams |
| dashboard-creator | marketplace | Data dashboards |
| flowchart-creator | marketplace | Flowcharts and process diagrams |
| timeline-creator | marketplace | Timeline visualizations |
| technical-doc-creator | marketplace | Technical documentation |

### Engineering Workflow (4)
| Skill | Source | Description |
|-------|--------|-------------|
| git-pushing | marketplace | Git operations automation |
| feature-planning | marketplace | Feature planning workflow |
| review-implementing | marketplace | Code review implementation |
| changelog-generator | skillcreator | Auto changelog generation |

### Business & Productivity (12)
| Skill | Source | Description |
|-------|--------|-------------|
| brand-guidelines | anthropics | Brand identity guidelines |
| internal-comms | anthropics | Internal communications |
| doc-coauthoring | anthropics | Document co-authoring |
| jira-issues | skillcreator | Jira issue management |
| meeting-insights-analyzer | skillcreator | Meeting analysis |
| lead-research-assistant | skillcreator | Lead research |
| content-research-writer | skillcreator | Content research |
| file-organizer | skillcreator | File organization |
| invoice-organizer | skillcreator | Invoice management |
| job-application | skillcreator | Job application helper |
| conversation-analyzer | marketplace | Conversation analysis |
| ask-questions-if-underspecified | skillcreator | Requirements clarification |

### Creative (3)
| Skill | Source | Description |
|-------|--------|-------------|
| slack-gif-creator | anthropics | Create Slack GIFs |
| web-artifacts-builder | anthropics | Build web artifacts |
| image-enhancer | skillcreator | Image enhancement |

## MCP Tools

The Skills MCP Server provides these tools:

### skill_list
List all available skills with names, descriptions, and sources.

```json
{
  "name": "skill_list",
  "description": "List all available agent skills"
}
```

### skill_get
Get full skill instructions by name.

```json
{
  "name": "skill_get",
  "arguments": {
    "name": "docx"
  }
}
```

### skill_search
Search skills by keyword in name or description.

```json
{
  "name": "skill_search",
  "arguments": {
    "query": "visualization"
  }
}
```

### skill_file
Get contents of a specific file from a skill (templates, scripts, etc.).

```json
{
  "name": "skill_file",
  "arguments": {
    "skill_name": "mcp-builder",
    "file_path": "reference/python_mcp_server.md"
  }
}
```

### skill_refresh
Refresh the skill index to pick up newly added skills.

```json
{
  "name": "skill_refresh"
}
```

## Agent Modes

### skill-master
Primary mode for discovering and using skills.

```bash
# Access via MCP Gateway
curl http://localhost:2091/tools/skills:skill_list
```

### document-skills
Specialized for Office document processing (docx, xlsx, pptx, pdf).

### mcp-developer
Build MCP servers using the mcp-builder skill with best practices.

## Usage

### For All BoTZ Agents

1. Search for relevant skills before attempting unfamiliar tasks:
   ```
   skill_search("visualization")
   ```

2. Load full skill instructions:
   ```
   skill_get("d3js-skill")
   ```

3. Access skill templates and helper files:
   ```
   skill_file("mcp-builder", "reference/python_mcp_server.md")
   ```

4. Follow instructions step-by-step

5. Store learned patterns in Cipher Memory

### For Claude Code

Skills are automatically available in `.claude/skills/`:

```bash
# List skills
ls .claude/skills/

# Read a skill
cat .claude/skills/docx/SKILL.md
```

## Deployment

### Docker Compose

```bash
# Build skills service
docker compose -f core/docker-compose/base.yml build skills

# Start all services
docker compose -f core/docker-compose/base.yml up -d
```

### Sync Skills

After adding new skill repos:

```bash
# Sync to .claude/skills
python features/skills/sync_skills.py

# Load into Cipher Memory (optional)
python features/skills/skill_loader.py --all
```

### Add New Skill Repos

```bash
# Add as git submodule
cd features/skills/repos
git submodule add https://github.com/user/skill-repo.git skill-name

# Update sync_skills.py and skill_server.py with new source
# Run sync
python features/skills/sync_skills.py
```

## Skill Structure

Each skill follows this structure:

```
skill-name/
├── SKILL.md          # Required: Instructions and metadata
├── reference/        # Optional: Reference documentation
├── templates/        # Optional: Code/document templates
├── scripts/          # Optional: Helper scripts
└── examples/         # Optional: Usage examples
```

### SKILL.md Format

```markdown
---
name: skill-name
description: What this skill does and when to use it
license: MIT
---

# Skill Name

Detailed instructions for the agent...

## When to Use

- Use case 1
- Use case 2

## Instructions

Step-by-step guide...

## Examples

Real-world examples...
```

## Git Submodules

| Submodule | Source | Skills |
|-----------|--------|--------|
| anthropics-skills | github.com/anthropics/skills | 16 |
| huggingface-skills | github.com/huggingface/skills | 5 |
| skillcreator-skills | github.com/skillcreatorai/Ai-Agent-Skills | 40 |
| aws-skills | github.com/zxkane/aws-skills | 4 |
| d3js-skill | github.com/chrisvoncsefalvay/claude-d3js-skill | 1 |
| playwright-skill | github.com/lackeyjb/playwright-skill | 1 |
| obsidian-plugin-skill | github.com/gapmiss/obsidian-plugin-skill | 1 |
| epub-skill | github.com/smerchek/claude-epub-skill | 1 |
| skills-marketplace | github.com/mhattingpete/claude-skills-marketplace | 17 |

## Integration with MCP Tools

Skills complement existing MCP tools:

| Skill | MCP Tool | Integration |
|-------|----------|-------------|
| docx/xlsx/pptx | docling | Use docling to parse, skill for structure |
| playwright-skill | e2b | Run Playwright in E2B sandbox |
| d3js-skill | e2b | Execute D3 code in sandbox |
| aws-* | n8n | Automate AWS workflows |
| mcp-builder | gateway | Build new MCP servers |

## Troubleshooting

### Skills Not Loading
```bash
# Refresh skill index
docker exec pmz-skills python -c "from skill_server import SkillManager; m=SkillManager(); print(len(m.list_skills()))"

# Check submodules
git submodule update --init --recursive
```

### Sync Issues
```bash
# Re-sync skills
rm -rf .claude/skills
python features/skills/sync_skills.py
```

## References

- [Anthropic Skills Documentation](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
- [Claude Code Skills Guide](https://code.claude.com/docs/en/skills)
- [PMOVES Awesome Agent Skills](https://github.com/POWERFULMOVES/PMOVES-awesome-agent-skills)
