# Prove: the rollout

The worked examples are the Rollout sections of ez's and bolt's RFCs, and
ez's `docs/rfc/ez-lock-planner.md`, the design for converting `ez lock`.
The ez PRs #51 to #69 are the rollout as it happened, in order; their
descriptions are good models for your own.

## Contents

- Phases
- Retiring closed laws
- The World, the planner and the interpreter
- The design doc, the spike and the work packages
- Law quality
- Linter rules as requirements
- The gates in CI
- Tool pins

## Phases

Each phase leaves the repo consistent: gate green, lint clean, SPEC.md
honest about what is pending. Decided behavior changes land as their own
PRs alongside the phases; the only ordering is that a row cannot be proved
before the change it depends on.

| Phase | ez | bolt |
| :---- | :---- | :---- |
| Preliminary | lint clean under bolt v0.8.1 with the law rules at warn, `mkLint` in the flake checks (#52) | a branch ruleset on `main` so the gate binds anything (a repository setting, not a PR) |
| One | SPEC.md from the RFC; 67 closed laws and the last 8 refactor-equivalence laws deleted; 53 kept as `# toward` trails; `hash_perm` tagged (#51); strict closed-law rule on (#53) | SPEC.md; all 257 closed laws deleted; `closed` made strict; law files moved so they cover the code |
| Two | the traceability rule on | the cheap rows that need no World (config, output, CLI) |
| Three | the World and planner for the most important command, then its rows | token rules, then tree rules by how often they fire |
| Later | one command per phase, each ending with its rows proved | the lint planner, `trace`, the checker oracle, the LSP |

Order the proving by cost, cheap and structural first: order independence,
framing, refusals, then content properties like round trips. This proves
the cheap rows early and tells you how expensive the hard ones really are.
A row that turns out too expensive moves to Trusted with a written reason,
which is a visible weakening the maintainer approves, never a silent one.

Behavior changes in ez came in between: the proof gate as its own command
(#54), the lock's inputs (#55), the gitignore allowlist (#56), tag
selection (#57), UTF-8 hashing (#58), bootstrap without nix (#59), the
fresh-clone CI check (#61), the tool cache key (#62), the ledger fixes
(#67). Each one proved its decision function with quantified laws even
when the row stayed pending, and each PR listed what it left pending.

## Retiring closed laws

Delete first the closed laws that point toward no requirement: wording
pins, helper pins, tests of the test runner, vectors for Trusted claims,
and refactor-equivalence laws with their `old.*` definitions. They pin
behavior nobody decided to guarantee.

For closed laws that illustrate a pending row there are two options, and
the maintainer picks:

- **Delete them all at once** (bolt, and in the end ez). Recommended. A
  closed law's only useful content is the map of what it was reaching for,
  and the inventory's "points toward" column keeps that. bolt's also
  encoded wrong assumptions about Bend (`report_import` pinned a location
  format bend no longer prints), so keeping them would have pointed the
  next author at the wrong behavior.
- **Keep them as `# toward <ID>` trails** until the row's quantified law
  lands, deleting each in that PR. ez did this for 53 laws under bolt
  v0.9.0's `quantify`, which exempted a trail. It kept ez on an old bolt,
  and once every pending row's real law was written in an accepted design
  doc, the trails told nobody anything. ez deleted the last 40 in one
  change (#69) and moved to strict `closed` and `trace`.

A law file whose laws all go is deleted with its PROOF.bend and any
fixtures only it used. Keep a closed law's helper only if a quantified
proof uses it as a lemma, and then move it into PROOF.bend next to that
proof (ez's `comp_dot`).

## The World, the planner and the interpreter

Laws only reach values, so every IO area in scope is split three ways:

- a **World**: a value holding only what the command reads, one World per
  command. Every extra field is an input a law has to account for, and a
  field the command does not read is one the law can silently depend on
  later;
- a **planner**: a pure total function from the World to a Plan, which is
  a list of effects plus an outcome (`Success{}` or `Refused{why}`; `Done`
  is taken by Bend's Base). It decides everything: what to write, with
  what bytes, and the exit status;
- an **interpreter**: reads the World, executes the plan's effects in
  order, and decides nothing. Its faithfulness is one Trusted row, so keep
  it small enough to review line by line.

When the planner's inputs depend on earlier answers (an import graph, a
remote's tags), do not prefetch everything. Use an ask and answer loop:
`wants(w)` returns the questions still open, the interpreter answers each
with one IO action and appends the replies to the World, and when `wants`
is empty it calls `plan(w)` once. An answer keeps the other program's
output as printed, so parsing it is the planner's decision. A law ties the
halves together: when `wants(w)` is empty, `plan` asks nothing. The
details, with types, are in spec-first-feature's `references/ez.md`.

The same shape serves a linter: bolt's per-file rules are already pure
functions of the parsed source, the lint run becomes a planner over
listings and file texts, and the LSP becomes a step function from messages
to replies and asks.

## The design doc, the spike and the work packages

Before converting a large area, write a design doc
(`docs/rfc/<project>-<area>-planner.md`) and get it accepted. ez's has:

- what the area reads today, with source lines, and which reads the World
  keeps;
- the World, Plan, Effect and Outcome types, and how the interpreter
  gathers each field;
- which effects and outputs are contractual and which are incidental;
- the module layout, and how much existing code moves unchanged;
- per requirement: the law statement, which existing laws it reuses,
  which closed laws it replaces, and an effort estimate (small, medium,
  large, with line counts where you can);
- a **spike**: the riskiest law proved against the real checker, in a
  directory nothing imports, inside the proof gate. ez's spike proved
  `clone_reproduces` and the hardest string lemmas of the lock round trip,
  which is why the design could say no row in the phase looked expensive
  enough to move to Trusted. Delete the spike when the real planner lands;
- open questions as REVIEW items with a recommendation each, all resolved
  by the maintainer before work starts;
- **work packages** with a dependency DAG (an ASCII diagram in a
  single-cell table) and a table of scope, needs and effort. Start the
  independent ones in parallel. ez's WP0 (shared lemmas), WP1 (plain
  planner) and WP8 (an independent hash law) started at once;
- risks, including cost. ez measured the demand loop's cost in WP1 before
  WP2 built on it (0.21 s to 0.53 s on its own lock), and recorded it.

Add an Update note at the top of the design doc as packages land, saying
where the code differs from the sketches, and keep the inventory's
progress table current.

## Law quality

spec-first-feature step 4 has the basic checks (every binder matters,
frame laws, both directions for "exactly"). At rollout scale, also:

- **Break every new proof on purpose** (replace it with `{==}` or a wrong
  term) and watch the gate fail, then restore it. Put "the proof fails if
  replaced by `{==}`" in the PR description. This is the cheapest evidence
  that the law says something.
- **Suspect laws that are true by construction.** ez's `lock_reproducible`
  holds by congruence because the planner is written as a function of
  `inputs(w)`. It still matters (it stops failing the moment the planner
  reads something outside `inputs`), but pair it with a law with real
  content: `clone_reproduces`, that a working checkout locks exactly as a
  fresh clone, proved by induction over the replies.
- **Give every refusing command the frame law** "a refused plan writes
  nothing" (EZ-OUT-2). It is small if every refusing arm builds its plan
  without write effects, and it is what makes partial writes impossible.
- **State order independence with permutations** and a distinctness
  premise, and reuse one sorting proof. ez proved `sort_perm` once for a
  concrete sort and reused it for the hash, the NAR directory and the lock
  render; a generic sort by key does not work in Bend (function values are
  linear), so render to a concrete type the proved sort already handles.
- **Do not prove a rule equal to a reference implementation** as the main
  law. The reference can share the implementation's misreading, which is
  the refactor-equivalence pattern both projects deleted. State the
  property instead.
- **A law can be partial.** Tag it with the row's ID, list it in the Law
  cell, and say what is left in "Left to prove". A tagged partial law is
  checked by `trace`; an untagged one is protected by nothing.
- **Isolate the catch.** A mutant that an older law already catches fails
  the gate there first, which says nothing about the new law. Run
  `scripts/isolate_mutant.py` in a scratch copy to see the new proof fail
  by itself, and name both in the PR ("fails `wk.walk_plain` first, and
  `values_given`'s own proof with the earlier laws set aside").

### Laws over a state machine (shake's walker)

A parser, a tokenizer or any fold over input is a state machine, and
replaying the whole input in each law does not scale. shake's walker laws
took these shapes, and every row of its parse group was proved with them:

- **Premise form.** A step law holds wherever the words before leave the
  walker in the state it names: `for pre, st, h_at: {walk(pre, start) == st}`,
  then the claim about the next word from `st`. It never replays `pre`, and
  it covers every reachable state at once (REVIEW-W1 in shake's
  `docs/rfc/shake-walker-proofs.md`).
- **One lemma per arm, composed along the dispatch.** For each function
  the step dispatches through, a lemma with that function's parameters
  plus the invariant's premises, proved by matching its first Bool or
  constructor and calling the next arm's lemma. The arm lemmas are long
  but mechanical; shake has two families (`gw.*` for the shape of the
  state, `gv.*` for the values in it).
- **A walk invariant as a Bool.** `good(st, ws) == True` kept by every arm
  (`gv.step`), so by every walk (`gv.walk`, induction on the words with
  the words before as a list that grows), then read at the end through the
  finished state's frame. A Bool invariant copies and splits with
  `and`/`or` lemmas; a sigma or a function premise does neither (see
  bend-gotchas.md).
- **Frame premises for "the command at this path".** When a law is about
  one part of the final result, take the final state's split as a premise
  (shake's `fin.Framed`: the finished frame is `qs ++ Level{args, bs} <>
  up` under `path ++ ms`) and prove one lemma that reads that part of the
  result from it (`fin.at`). Every per-command law then reuses it.
- **Refusals through one lemma.** A step that fails leaves the walker
  failed for the rest of the words (`fail_stays`), so each refusal law is
  "this step fails from the state named", through one general `refused`.

## Linter rules as requirements

For a lint rule's row, write two kinds of law, tagged with the rule's ID
(bolt's `put_counts`, `nat_counts`, `param_counts`, `escape_counts`):

- **completeness as a count equality**: for every token list (or tree) and
  path, the number of findings equals a small independent counter of the
  pattern;
- **frame**: zero findings where the pattern is absent or the path is
  exempt.

Refactor the rule so the law can be stated over a pure function of the
token list and path (bolt's `check.on`), with its output unchanged. When
writing the law exposes a bug in the rule, fix it in the same PR and say
so (bolt's `put` hid a definition behind a keyword read two tokens at a
time). Before a rule's default goes above warn, run it over the sibling
repositories and read every finding; see spec-first-feature's
`references/bolt.md`.

## The gates in CI

- **The proof gate** as its own command, run in CI: for every PROOF.bend,
  the first line of output is exactly `All terms check.` Exit status alone
  is not enough, because bend exits 0 and prints `All terms check, but N
  defs rely on unsafe or foreign code:` when a proof leans on an unchecked
  def. ez added `ez prove` for this (#54) and dropped its unit tests.
- **bolt over the whole tree** with the pinned version, `closed` and
  `trace` at error. `trace` only runs on a whole-tree lint.
- **A direct check of the headline guarantee** where one exists. ez's
  `fresh` flake check copies the tracked files into a new repo, fills
  BEND_LIB offline, builds the README's way, deletes the lock, relocks and
  `cmp`s. It backs the law end to end, including the trusted interpreter.
- **A non-nix job that follows the README literally**, for users without
  nix. ez's `readme` job installs the pinned bend release by checksum, runs
  `sh bootstrap.sh`, builds and runs the proof gate. A bootstrap script
  replaced vendoring a dependency to break the build cycle.

Read each CI job's log after the first run of a new check to confirm it
actually ran its steps; a check that silently skips is worse than none.

## Tool pins

A newer linter can fail a tree that the rollout has not finished
cleaning. Stay on the old pin, write down why and what ends it (ez: "stays
on v0.9.0 while any `# toward` trail remains"), and move in the change
that removes the reason. When you need a linter change that has merged but
not been released, pin the commit, say so in the PR, and re-pin to the tag
when it ships. Let the project's own upgrade command compute the pin's
hash, and check it independently.
