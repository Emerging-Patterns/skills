# skills

Shared Claude Code skills for Emerging-Patterns Bend projects, packaged as a
plugin marketplace.

## Install

```
/plugin marketplace add Emerging-Patterns/skills
/plugin install bend-spec@emerging-patterns
```

To make every contributor's session in a repo offer it, add this to that repo's
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "emerging-patterns": { "source": { "source": "github", "repo": "Emerging-Patterns/skills" } }
  },
  "enabledPlugins": { "bend-spec@emerging-patterns": true }
}
```

## Plugins

| Plugin | Skill | What it does |
| :-- | :-- | :-- |
| `bend-spec` | `spec-first-feature` | New or changed behavior in a project with SPEC.md and LAWS.bend/PROOF.bend: the requirement row first, then a quantified tagged law, the proof, the status flip, and a clean proof gate plus bolt `trace`. Per-repo detail is in `references/` (bolt rules, ez planners, bringing a sibling library under the convention). |

## Changing a skill

The skills here encode the conventions in each repo's SPEC.md, AGENTS.md and
`docs/rfc/*-spec.md`. Those files win when they disagree, so when a
convention changes there, update the skill here in the same week. Each skill
keeps its test prompts in `evals/evals.json`. Re-run them with the
skill-creator skill after a substantive edit, and bump the plugin's
`version` in `.claude-plugin/plugin.json` so installed copies update.
