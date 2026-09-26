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
the gate (every PROOF.bend `All terms check`, `ez test`, `nix flake check`),
and "open a PR, don't merge". Keep publishing and merging in the parent, so
every hub upload and release goes through one place in dependency order.
Forward new tags and hashes to a waiting subagent as they are published.
