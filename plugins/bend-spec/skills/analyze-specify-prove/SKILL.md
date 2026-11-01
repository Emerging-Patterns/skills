---
name: analyze-specify-prove
description: Bring an existing Bend project (or a large area of one) under a machine-checked spec, the way ez and bolt were. Audit what its laws, tests and docs actually prove against the code and the real binary, write the RFC and one law file per guarantee, settle the behavior changes with the maintainer, then roll out quantified laws across many PRs, fixing the real bugs found along the way, until every guarantee is a law file `bend PROOF.bend` checks and the headline guarantees are proved. Use this whenever the spec, the laws and the behavior of a repo disagree or nobody knows what is proved, for requests like "bring eztoml under spec", "audit the laws in snap", "our tests don't catch anything", "fix this repo's spec", "make shake's guarantees provable", "spec overhaul", "most of these laws are closed", "write an RFC for what X guarantees", or "put the rest of ez's commands in planner form". For adding one feature to a project whose laws are already trustworthy, use spec-first-feature instead.
---

# Analyze, specify, prove

This is how a Bend project whose docs, laws and behavior disagree ends up
with one law file per guarantee under `laws/`, each proved by quantified
laws or saying in its prose what is left, and every assumption the gate
cannot check written on the code that makes it. ez and bolt both went
through it. The method has three
stages, and debugging runs through all of them:

1. **Analyze**: find out what the project actually does and what its laws
   actually prove, from the code and the running binary, not from the docs.
2. **Specify**: write the guarantees, decide every disagreement with the
   maintainer, and record the decisions in an RFC and the law files.
3. **Prove**: retire the laws that prove nothing, move decisions out of IO
   so laws can reach them, and land quantified laws PR by PR until the
   guarantees are proved.

It is a different job from `spec-first-feature` (in this plugin), which
adds one behavior to a project whose laws are already trustworthy. This
skill is what makes them trustworthy in the first place. Once a project is
through it, new work follows spec-first-feature. Read that skill's SKILL.md
now if you have not: its vocabulary (law file, guarantee, prose, frame law,
`# toward` trail, proof gate, trusted comment, planner and interpreter) is
used here without being redefined, and its steps 2 to 6 are how each
guarantee in the rollout gets proved. Its `references/adopting.md` covers
moving a project that already has SPEC.md to the law layout.

## The positions this method rests on

Both ez and bolt reached these, and the rest of the skill follows from
them. Adopt them explicitly in the RFC so the maintainer can disagree
early rather than late.

- **Proved, or trusted on the code.** A guarantee is a law file whose
  quantified laws pass the proof gate. What the gate cannot check (another
  program, foreign code, a property across releases, the checker itself)
  is not a guarantee: it is a `# Trusted, not proved:` comment on the code
  that assumes it, or a citation of a dependency's law file. A guarantee
  proved only in part says so in its prose; that is not a third level.
  Intermediate levels ("checked on examples", "agrees with an oracle")
  were tried and abandoned in both RFCs: they are tests under another name,
  and they make readers overestimate what is guaranteed.
- **A closed law has no standing.** A law with no binder is a unit test
  the checker runs. It is too weak to protect a behavior (a refactor that
  breaks every other input passes) and too strong to let it change (it
  pins wording nobody depends on). ez found 122 closed laws out of 269 and
  bolt 257 out of 271, and in both the real guarantees were a handful.
- **A test is never evidence for a guarantee.** What a law cannot state
  is trusted, and said on the code, not tested. Tests stay only for host
  and integration checks, and nothing under `laws/` depends on them.
- **Laws only reach values.** A decision made inside IO cannot be proved.
  Every real bug the audits found was "the program decided the wrong thing
  inside IO", so the proving stage is mostly moving decisions into pure
  planners.
- **One headline guarantee drives priorities.** For ez it was EZ-DOC-3,
  "the lock is reproducible from committed inputs". Name it early; it
  decides which inputs a command may read, which behavior changes matter,
  and which command gets converted first.

## 0. Orient and scope

Read the project's AGENTS.md or CLAUDE.md, README, any existing LAWS.bend,
SPEC.md or RFC, `bolt.bend`, the flake checks and the CI workflow. Find out
which bolt the project pins, since the rules available (`closed`,
`quantify`) and whether it finds law files by following imports (bolt#257)
depend on it (spec-first-feature step 0 has the details).

Then agree the scope with the user: the whole project, or one area (one
command, the lint rules, the parser). A scope that is too wide produces an
inventory nobody finishes. ez did the whole tool in one RFC but converted
one command per phase; bolt did the whole linter and ordered the
guarantees by proof cost.

Work in the target repo on a branch per PR, starting from current main,
not a tagged release. The method runs over many PRs and days, so keep the
progress in the repo (the inventory), not in your head.

## 1. Analyze

The goal is ground truth: what every law claims, what the code does, and
where they and the docs disagree. Details and templates are in
`references/analyze.md`. The essentials:

- **Inventory every law.** One row per law: kind (Q quantified, C closed),
  proof shape (`{==}` or structural), what it actually claims in one line,
  and which guarantee it points toward (`none` with a reason when it
  serves nothing). Count them per file. This table is what makes "most of
  our laws prove nothing" a fact the maintainer can check instead of your
  opinion. A quantified law proved by `{==}` usually restates a
  definition; flag it.
- **Check each draft requirement against the code, not the docs.** Give
  each one a verdict (holds, partly, fails, as trusted) with file and line
  evidence. The first ez draft was written from the README without the
  source, and several of its requirements were false.
- **Trace what each command reads.** List every input with its source
  line. The headline guarantee is usually decided by this table: ez's lock
  turned out to read untracked files, an environment variable and a cache
  file a fresh clone does not have.
- **Run the real binary from a fresh clone.** Most of the real bugs were
  found this way and not by the existing tests: a hash that disagreed with
  the publisher on non-ASCII files, a README build step that failed because
  `bin/` did not exist, two dependencies both named `main`, a relative path
  fetched from the wrong directory, `ez init` overwriting a ledger. The
  recipe is in `references/debugging.md`.
- **Root-cause against the reference implementation.** When ez and bend
  disagree about a hash, read bend's source (it is embedded in the binary;
  `strings` extracts it) rather than guessing which is right. Before you
  design a behavior, check the other tool can support it (bend cannot
  report a publish hash without uploading, so "compare before upload" was
  dropped and documented).
- **Sort each finding.** Behavior the code guarantees that no requirement
  mentions; behavior that looks accidental; requirements with no code; and
  bugs. Do not decide yet which accidents become requirements; that is the
  maintainer's call in stage 2.

Deliver stage 1 as a PR with the inventory (`docs/rfc/<project>-law-inventory.md`)
and the RFC draft together, with no behavior change. The inventory is the
evidence the RFC cites.

## 2. Specify

Write the RFC (`docs/rfc/<project>-spec.md`) and, once its decisions are
in, the law files. Format and style details are in `references/specify.md`.

- **RFC style.** We-voice prose, no em dashes, no numbered headers. A Draft
  Status section at the top holds every open decision as
  `- [ ] <!-- REVIEW: ... -->`, resolved in place as
  `- [x] <!-- REVIEW (resolved): ... -->` with the decision and its
  evidence, so the history of each decision stays readable. ASCII
  diagrams go in single-cell tables. Keep Abandoned Ideas: each one records
  an argument the next agent will make again (for tests, for keeping closed
  laws, for proving in Lean).
- **Guarantees.** Wording rules are spec-first-feature step 2: every
  input, "exactly" when both directions matter, name the decision rather
  than the IO. Each trusted assumption gets its reason in the comment on
  the code. A guarantee proved in a pinned dependency is cited by its law
  file from this side, never proved again.
- **Give the maintainer a decision list, with a recommendation per item.**
  They will usually approve in bulk, which is only safe if each item states
  the evidence, the options and your pick. Base contested choices on
  established tools: ez's dependency naming follows cargo (package name
  first, `--rename` to override) instead of an invented rule.
- **Separate accidents from guarantees, per case.** Some bugs become
  guarantees (ez's refusals and naming, EZ-LED-6 to 8); others are fixed
  with laws stated in proof files and a note in the inventory (directory
  creation, `doctor` on an empty project). A law file is a promise to keep
  the behavior forever, so padding `laws/` with incidental guarantees hides
  the real ones.
- **Collect decided behavior changes in their own RFC section.** Each lands
  as its own PR, separate from the rollout, and a guarantee that depends
  on one stays partly proved until it lands.
- **`laws/` is the single list of guarantees,** one file each, named for
  the behavior, imported from the root LAWS.bend, in bolt's and eztoml's
  layout. The RFC keeps the reasoning and names each guarantee by its file.
  Where bolt's rules do not fit the layout, ask bolt's maintainers for a
  rule change (an issue or PR) instead of bending the layout around the
  gap.
- **Fold decisions in as they are made.** Every decision reached later, in
  a design doc or a PR, goes into the RFC and the law files in the same
  change.
  The maintainer had to ask whether recent decisions had been folded in;
  do not make them ask.

## 3. Prove

The rollout runs in phases, each leaving the repo consistent. Phase order,
the World and planner pattern, and law quality checks are in
`references/rollout.md`. The outline:

1. **Lint first, if needed.** Make the tree clean under the bolt you will
   use, with the law rules at warn, so later PRs are not buried in style
   noise. Stay on an older bolt while a newer one's rules would fail you,
   record why in the RFC, and plan the exit (ez stayed on v0.9.0 while its
   `# toward` trails existed, and moved to a bolt with strict `closed` in
   the change that deleted them).
2. **Retire closed laws and land the law files.** Delete the closed laws
   that point toward nothing, and move the laws that already prove a
   guarantee into its law file. For the rest, recommend deleting them all
   at once and ask the maintainer.
   bolt deleted all 257 in one PR, because they encoded wrong assumptions
   about Bend. ez first kept 53 as `# toward` trails, then deleted the
   last 40 in one change once the unproved guarantees' real laws were
   written down in accepted design docs, because the trails no longer told anyone
   what to prove and they held ez on an old bolt. The inventory's "points
   toward" column keeps the useful part, the map, either way.
3. **Put the proof gate in CI,** exactly "the first line `bend PROOF.bend`
   prints is `ALL PROOFS CHECK`", and bolt over the whole tree with
   `closed` at error.
4. **Convert the IO areas to planner form,** most important guarantee
   first: a World holding only what the command reads, a pure planner
   returning a Plan (effects plus outcome), a thin interpreter trusted to
   be faithful. Before converting, write a design doc with a spike that
   proves the riskiest law against the real checker, get the maintainer's
   decisions on its open questions, and split it into work packages with a
   dependency DAG.
5. **Prove the guarantees,** cheap structural ones first (order
   independence, framing, refusals), content properties later. Each one
   follows spec-first-feature steps 3 to 6.

For every law, check it is not vacuous: break its proof on purpose and
watch the gate fail. Be suspicious of a law that is true by construction,
and pair it with one that has real content (ez's `lock_reproducible` holds
by construction; `clone_reproduces` is the one with content). Give every
command that can refuse the frame law "a refused plan writes nothing".

## Debugging along the way

Stages 2 and 3 keep finding bugs, and each one is also a test of the spec.
`references/debugging.md` has the fresh-clone recipe, the side-by-side
comparison of master's binary with the branch's, and the catalog of what
ez and bolt found. The habits that matter:

- Run every behavior change end to end against master's binary and the
  branch's, and put both results in the PR.
- Turn a manual check that caught a bug into CI. ez gained an offline nix
  check that rebuilds the lock from a clean copy and `cmp`s it (the direct
  check of its headline guarantee) and a non-nix job that follows the
  README literally.
- Verify claims about the tool you depend on against the version you pin.
  bolt retired its `shadow` rule because the failure it guarded against no
  longer exists in bend 2.0.25.
- When a proof will not go through, read `references/bend-gotchas.md`
  before doubting the law. Most failures are one of those.
- Plant the bug a law is meant to catch and watch it fail there. When an
  older law fails first, `scripts/isolate_mutant.py` shows whether the new
  one catches it by itself.
- Stating a law precisely is itself a bug hunt: shake's PARSE-5 and
  PARSE-10 laws each found a walker bug, and PARSE-1's found its own
  wording wrong about flags. Fix the code (or the prose) first, in the same
  PR.

## Running it with subagents

The rollout is many PRs, and parallel agents help once the DAG is known.
`references/orchestration.md` covers the lead's loop: one PR per coherent
change, one worktree and build script per agent, independent verification
from a fresh clone before pushing, reading CI logs to confirm each check
ran, and reviewing agent output for things like absolute paths in
committed files. Two rules without exceptions: never publish to a package
hub to test something, and never put model identifiers in repo artifacts.

## When it is done

The RFC names its own finish line (ez's: every guarantee in the EZ-DOC and
EZ-RES groups proved, every closed law deleted, and an internal rewrite
mergeable on the proof gate alone). Around it:

- the proof gate, whole-tree bolt and any fresh-clone check in CI, all
  green.
- Every closed law deleted, strict `closed` on at error, and any
  temporary pin on an old bolt lifted.
- The inventory folded into the RFC (what still matters: findings, the
  reads table, measurements) and deleted, since it was a progress tracker.
- New work in the project goes through spec-first-feature.

## Reporting

After each PR and at each phase boundary, tell the user plainly: law
files added, reworded or now fully proved; laws landed and whether each is
frame or direct; trails or closed laws deleted; behavior changes and how they were
checked against master; bugs found and whether each became a guarantee or
a fix with no law file; trusted assumptions added or removed; and what is next in
the DAG. Keep
the inventory's progress section saying the same thing.
