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
| `bend-spec` | `analyze-specify-prove` | Bringing an existing project, or a large area of one, under spec when its docs, laws and behavior disagree: audit every law and run the real binary from a fresh clone, write the RFC and SPEC.md with the maintainer's decisions, then roll out quantified laws and planner conversions across many PRs (optionally with subagents), fixing the bugs found on the way, until `trace` passes and the headline guarantees are proved. ez and bolt are the worked examples. |
| `bend-spec` | `perf-under-proof` | Making a proven Bend project faster without weakening a guarantee: profile with a per-stage bench, find the costly shape, write a faster def proven equal for every input (early exit, a sound index with a fallback scan, a proven twin of a pinned walk), measure one change at a time against a guard (proofs check, output unchanged), keep the research trail on an `autoresearch/` branch and only `perf(...)` commits on main, and hand a law that blocks further speed to the maintainer. bolt's lint (208 s to 20 s) is the worked example. |
| `bend-ecosystem` | `find-users` | Who outside the org uses bolt, ez or the ez libraries: code search by `org/pkg` and hub hash (paced for the 10/min limit), then a direct sweep of every Bend repo search can find (file tree for `ez.toml`/`bolt.bend`, README for mentions), since GitHub's code index misses young repos. `scripts/find_users.py` runs it; the skill says how to sort hits into depends, mentions, listing, upstream and noise, and what can't be seen. |

## Changing a skill

The skills here encode the conventions in each repo's SPEC.md, AGENTS.md and
`docs/rfc/*-spec.md`. Those files win when they disagree, so when a
convention changes there, update the skill here in the same week. Each skill
keeps its test prompts in `evals/evals.json`. Re-run them with the
skill-creator skill after a substantive edit, and bump the plugin's
`version` in `.claude-plugin/plugin.json` so installed copies update.
