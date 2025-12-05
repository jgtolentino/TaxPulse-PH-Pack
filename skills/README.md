# TaxPulse Skills for Coding Agents

This directory contains skill definitions for AI coding agents (Claude Code, Codex, Gemini, etc.) working with the TaxPulse ecosystem.

## What are Skills?

Skills are structured prompts that give AI agents specialized knowledge and workflows for specific tasks. Each skill:

- Defines a **role and scope** (what the agent can do)
- Provides a **competency matrix** (what it should know)
- Documents a **default workflow** (how to approach tasks)
- Lists **examples** (when to use the skill)
- Sets **guardrails** (what to avoid)

## Available Skills

| Skill | Description | Use When |
|-------|-------------|----------|
| `sap-odoo18-taxpulse-certified` | Full ERP + tax intelligence expertise | Building/refactoring TaxPulse, Odoo modules, or SAP-like flows |
| `taxpulse-repo-audit` | Repository architecture audit | Reviewing TaxPulse repos for compliance and correctness |
| `odoo-18-oca-architect` | Odoo 18 CE/OCA patterns | Building OCA-compliant modules |

## Skill Structure

Each skill follows this pattern:

```
skills/
└── skill-name/
    └── SKILL.md
```

### SKILL.md Format

```markdown
---
name: skill-name
description: Brief description of when to use this skill
tags:
  - relevant
  - tags
agent_hint: coding-only|research|planning
version: 1.0.0
---

# Skill: Display Name

## 1. Role & Scope
What the agent should do with this skill.

## 2. Competency Matrix
What the agent must know/demonstrate.

## 3. Default Workflow
Step-by-step process to follow.

## 4. Examples
When to use this skill.

## 5. Guidelines & Guardrails
What to avoid and prioritize.
```

## Using Skills with Claude Code

Skills in this directory can be:

1. **Manually loaded** - Copy the SKILL.md content into your conversation
2. **Auto-discovered** - Claude Code can scan `skills/**/SKILL.md`
3. **Tool-invoked** - Use a skill loader to inject skills on demand

### Example: Loading a Skill

```bash
# In Claude Code CLI
claude --skill sap-odoo18-taxpulse-certified "Extend TaxPulse to support 2550M form"
```

### Example: Skill Loader (conceptual)

```python
def load_skill(skill_name: str) -> str:
    """Load a skill from the skills directory."""
    path = f"skills/{skill_name}/SKILL.md"
    with open(path) as f:
        return f.read()

# Inject into agent context
context = load_skill("sap-odoo18-taxpulse-certified")
```

## Adding New Skills

1. Create a new directory: `skills/your-skill-name/`
2. Add `SKILL.md` with proper frontmatter
3. Test the skill with sample prompts
4. Document examples of when to use it

## Skill Governance

- **Version control** - Skills are tracked in git like code
- **Review changes** - Treat skill updates as PRs requiring review
- **Test skills** - Verify skill effectiveness with real tasks
- **Document evolution** - Track version history in frontmatter

## Related Files

- `config/tax_pulse_sources.yaml` - Authority sources for RAG
- `engine/finance_tax_pulse_orchestrator.md` - AI orchestrator prompt
- `specs/` - Product requirements and specifications

## Contributing

When contributing skills:

1. Follow the SKILL.md format exactly
2. Include comprehensive examples
3. Test with actual coding tasks
4. Update this README with new skills
