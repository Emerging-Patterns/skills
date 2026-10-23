# Porting a dependent across a breaking release

Most bumps are a hash and a path. A breaking release (a `!` in the
dependency's CHANGELOG) can need real work in the dependent, including its
proofs. shake 0.2.0 was one: per-command bindings, repeated options refused
unless declared with `many`, `get` answering `Maybe<String>`, `NeedHelp`
replaced by `help_path`, and every internal moved under `src/`.

## Find the size first

Pin the old version of the breaking dependency and the new versions of the
rest, then check. If that passes, the breaking dependency is the only port.
Count references per file (`grep -c 'Dep\.'`). References in PROOF.bend that
reach into the dependency's internals are the expensive part, and usually
the wrong design (below).

## Trust, don't re-prove

A dependent's laws are about the dependent. When a proof unfolds the
dependency's parser to show something about the dependent, replace that
reasoning with the dependency's proved guarantee:

- import only the dependency's public entry (`0x…/main.bend`);
- add the rows you rely on (e.g. `SHAKE-PARSE-1`) to the dependent's SPEC.md
  trust section, with the release they were proved at, the way ezjson's
  `JSON-TRUST-*` rows record what it takes from Bend;
- state the dependent's law as resting on that row, with a comment citing
  it;
- move laws that were really about the dependency out. If the dependency
  lacks a proved row the dependent needs, open that upstream as a proof to
  add there.

This shrinks the dependent's proof base. Each fact is then proved once, in
the package that owns it, and dependents stop breaking when the dependency
refactors its internals.

## With subagents

One subagent per dependent repo, each with: the repo path and branch, the
new dependency tag and hash, the latest ez binary path, the trust rule above,
the gate (every PROOF.bend prints `ALL PROOFS CHECK`, `ez test`, `nix flake check`),
and "open a PR, don't merge". Keep publishing and merging in the parent, so
every hub upload and release goes through one place in dependency order.
Forward new tags and hashes to a waiting subagent as they are published.

Write what every subagent shares into one brief file in the scratchpad and
give each one only its repo and what is particular to it ("read and follow
<brief>; your repo: …; known breaks: …; commit type: …"). The brief holds:

- the tool paths (target bend, an ez built on the target, the skill);
- the target pin (bend commit and its linux-x64 archive sha256) and what
  to mirror (the previous pin commit, found with `git log --grep`);
- the current release table: tag, hub name and hash for every package.
  Rebuild it before each wave from `fleet_graph.py` and the hub's
  `/name/<name>@X.Y.Z.0`; other sessions release while you run, and a
  stale table sends agents to old versions;
- the breaks to expect, from the release notes and the survey;
- the rules: honest proofs, trust a dependency's rows, the commit type
  decides the release, refresh with `merge --ff-only`, which token pushes
  workflow files, don't merge or publish, wait for green CI, and what the
  report must say.

Agents report in their own words; check each claim that matters (a PR's
checks, a hash on the hub, a README snippet) before acting on it. An agent
stopped by auto mode partway through a decision the parent made for the
user stays stopped: take the decision to the user, not around the block.
