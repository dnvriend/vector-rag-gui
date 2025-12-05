# Claude Code Marketplace and Plugin Guide

## Overview

This project includes a pre-configured Claude Code marketplace and plugin structure that enables:
- **Slash Commands**: Quick CLI invocations (e.g., `/vector-rag-gui:help`)
- **Skills**: Comprehensive documentation with progressive disclosure (e.g., `/skill-vector-rag-gui`)

## Structure

```
vector-rag-gui/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace definition
└── plugins/
    └── vector-rag-gui/
        ├── .claude-plugin/
        │   └── plugin.json       # Plugin metadata
        ├── commands/              # Slash commands (SHORT)
        │   └── help.md           # General help command
        └── skills/                # Skills (COMPREHENSIVE)
            └── vector-rag-gui/
                └── SKILL.md      # Comprehensive skill documentation
```

## Marketplace Configuration

**File**: `.claude-plugin/marketplace.json`

Contains:
- Owner information (name, email, GitHub URL)
- Marketplace metadata (description, version)
- Plugin references

## Plugin Configuration

**File**: `plugins/vector-rag-gui/.claude-plugin/plugin.json`

Contains:
- Plugin name and description
- Version number
- Author information

## Slash Commands

**Location**: `plugins/vector-rag-gui/commands/`

**Purpose**: Short, focused command documentation

**Format**:
```markdown
---
description: Command description (≤ 50 chars)
argument-hint: arg-name
---

Brief explanation.

## Usage
## Arguments
## Examples
## Output
```

**Default Command**: `help.md` - Shows CLI help information

**Adding New Commands**:
1. Create `plugins/vector-rag-gui/commands/<command>.md`
2. Add frontmatter with description and argument-hint
3. Keep it short (≤ 1 screen)
4. Include 2-3 practical examples

**Usage in Claude Code**:
```
/vector-rag-gui:help
/vector-rag-gui:command "argument"
```

## Skills

**Location**: `plugins/vector-rag-gui/skills/vector-rag-gui/SKILL.md`

**Purpose**: Comprehensive documentation with progressive disclosure

**Key Sections**:
- **When to use**: Brief bullet points
- **Purpose**: Tool overview
- **When to Use This Skill**: Scenarios and anti-patterns
- **Installation**: Standard installation instructions
- **Quick Start**: 2-3 practical examples
- **Progressive Disclosure**: Collapsible sections with detailed content
  - 📖 Core Commands
  - ⚙️ Advanced Features
  - 🔧 Troubleshooting
- **Best Practices**: Guidelines for using the tool
- **Resources**: Links to GitHub, documentation, etc.

**Updating the Skill**:

The included `SKILL.md` is a skeleton with TODO comments. As your CLI tool evolves, update it by:

1. Adding specific use cases in the "When to use" section
2. Expanding the Purpose section with tool capabilities
3. Adding detailed command documentation in the "Core Commands" section
4. Documenting advanced features (verbosity, pipelines, etc.)
5. Adding troubleshooting guidance for common issues
6. Updating best practices based on user feedback
7. Adding links to actual documentation and resources

**Usage in Claude Code**:
```
/skill-vector-rag-gui
```

Or:
```
Use the skill-vector-rag-gui to help me understand this tool
```

## Critical Requirements

1. **Description Length**: Keep descriptions in frontmatter ≤ 50 characters (hard limit)
2. **Progressive Disclosure**: Use `<details>` tags in skills to keep content manageable
3. **Explicit Invocation**: Always invoke skills explicitly (implicit activation is unreliable)
4. **Separation of Concerns**:
   - Slash commands → Quick reference
   - Skills → Comprehensive guidance

## When to Use Each

| Use Slash Command When | Use Skill When |
|------------------------|----------------|
| Quick CLI invocation needed | Comprehensive guidance needed |
| User knows exact arguments | User needs examples and patterns |
| 1-2 line explanation sufficient | Multiple sections of info required |
| Direct mapping to CLI command | Teaching/reference material |

## Adding New Commands

When you add a new CLI command:

1. **Update the slash command** (optional):
   - Create `plugins/vector-rag-gui/commands/<command>.md`
   - Follow the short format template
   - Keep it ≤ 1 screen

2. **Update the skill** (recommended):
   - Add command documentation to the "Core Commands" section
   - Include detailed usage, arguments, examples, and output
   - Add troubleshooting tips if needed
   - Update best practices if applicable

## Version Synchronization

Keep versions synchronized across:
1. `pyproject.toml` → `[project] version = "X.Y.Z"`
2. `.claude-plugin/marketplace.json` → `metadata.version`
3. `plugins/vector-rag-gui/.claude-plugin/plugin.json` → `version`

## Testing

### Verify Structure
```bash
# Check marketplace
cat .claude-plugin/marketplace.json | jq '.'

# Check plugin
cat plugins/vector-rag-gui/.claude-plugin/plugin.json | jq '.'

# List commands
ls plugins/vector-rag-gui/commands/

# Check skill
cat plugins/vector-rag-gui/skills/vector-rag-gui/SKILL.md
```

### Test in Claude Code
1. Open your project in Claude Code
2. Try slash command: `/vector-rag-gui:help`
3. Try skill: `/skill-vector-rag-gui`

## Resources

- **Claude Code Documentation**: https://docs.anthropic.com/claude-code
- **Example Repository**: https://github.com/dnvriend/aws-knowledge-tool
- **MCP Specification**: https://modelcontextprotocol.io

## Summary

This skeleton provides a foundation for Claude Code integration:
- ✅ Marketplace and plugin structure pre-configured
- ✅ Default help command included
- ✅ Comprehensive skill template with TODO instructions
- ✅ Ready to customize as your CLI evolves

As you add commands to your CLI, update the slash commands and skill documentation to keep them in sync.
