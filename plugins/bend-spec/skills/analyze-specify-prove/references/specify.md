# Specify: the RFC, the decisions, and SPEC.md

The worked examples are ez's `docs/rfc/ez-spec.md` and bolt's
`docs/rfc/bolt-spec.md`. bolt's RFC was written second and says which
positions it carried over from ez; read its "Two levels, and the positions
carried over from ez" section if the project you are working on depends on
either of them.

## Contents

- The RFC's shape
- Draft Status and REVIEW items
- The decision list
- Writing requirements
- The trust boundary
- Decided behavior changes
- SPEC.md
- Keeping documents in step
- Asking the linter for changes

## The RFC's shape

Name it `docs/rfc/<project>-spec.md`. Write in the we-voice, plain
sentences, no em dashes, no numbered headers; this is the style of the
lemieux/rfc-skills RFC skills, so use them if they are installed. Sections,
as both RFCs have them:

| Section | What goes in it |
| :---- | :---- |
| Draft Status | the state (Draft, Accepted), what the draft was written from (the commit, the inventory), and every REVIEW item |
| Abstract | the law counts and the one-sentence problem: what the gate passing tells us today, and what it should |
| Glossary | every term a reader needs: ledger, World, planner, interpreter, closed and quantified law, proof gate, Proved, Trusted, pending |
| Background | what the project does; how it proves things today; why that leaves us unsure what is proved |
| Problem Statement | the two questions every behavior must answer (what is guaranteed; proved or assumed), goals and non-goals |
| Proposal | two levels and why only two; the proof gate; the World model and how far each command is from it; requirements by group, each table followed by the evidence and the law sketch; retiring closed laws; tagging and traceability; refactoring contract; trust boundary; decided behavior changes; how we will know it worked |
| Abandoned Ideas | each alternative with its real merits and why we did not take it |
| Rollout | the phases, and what each leaves true |
| Risks | proof effort, model divergence, the spec encoding accidents, the headline guarantee needing a behavior change, pressure to reintroduce tests, checker soundness |
| Future Steps | cross-command guarantees, siblings adopting the same format |

ASCII diagrams go in single-cell tables so they render the same everywhere:

```
|  |
|:---:|
| <pre>real system ──read──▶ World ──▶ planner ──▶ Plan ──▶ interpreter</pre> |
| Caption: All behavior lives in the planner, where laws apply. |
```

Law sketches in the RFC use real names where the definition exists and
say so where it does not ("Names used in this document" in ez's RFC).
Placeholder names were the first REVIEW item ez resolved, because a reader
cannot check a sketch against code that is not there.

Why keep Abandoned Ideas: every one of them is an argument the next agent
will make again. "Keep the tests as part of the assurance story",
"formalize it in Lean instead", "prove each rule equal to a reference
implementation", "check rules against a corpus". Writing down why each was
rejected, with its real merits, settles the argument once.

## Draft Status and REVIEW items

Each open decision is one HTML comment in a checklist, so it is invisible
in rendered markdown but greppable and diffable:

```
- [ ] <!-- REVIEW: `owner/repo` rejects dots, so `vercel/next.js` is a path. Recommend: allow `.` in both segments, and make a second segment ending in `.bend` a path. -->
```

Resolve it in place, keeping the history:

```
- [x] <!-- REVIEW (resolved): `owner/repo` allows `.` in both segments, so `vercel/next.js` is GitHub. EZ-RES-3 states the new behavior. -->
```

When a resolution turns out wrong, say so rather than rewriting it:
`REVIEW (resolved, then reversed)`, with the evidence that reversed it
(ez's hash fold). A reader then sees both the decision and why it changed.

bolt numbered its items (`REVIEW-1` to `REVIEW-14`) and put the one every
other decision depended on first. Do that when items depend on each other.

## The decision list

When the RFC draft is ready, give the maintainer the open items as a list
they can answer in one reply. For each item:

- what the code does now, with the evidence (inventory row, confirmed run);
- the options, briefly;
- your recommendation and why, citing an established tool where the
  choice is a convention (ez took cargo's dependency naming: the package's
  own name first, `--rename` to override; bolt took ez's positions);
- whether it is a behavior change, and what it breaks.

Maintainers approve such lists in bulk ("accept every recommendation"),
which is efficient and only safe because each item carried its evidence.
Then fold every answer into the RFC in the same change, and note in Draft
Status that the items are resolved.

Decide per case which accidents become requirements. The pattern ez's
decisions followed: a behavior users will rely on and that a refactor could
silently break becomes a row (refusing to overwrite a ledger, how a
dependency is named); a behavior that was simply wrong and that nobody
should rely on either way is fixed with an untagged law and a line in the
inventory (creating `.ez` in the current directory). Some accidents had
only closed laws as their record (ez's doctor drift report); rather than
lose the record when the closed laws go, they became rows (EZ-VEN-5).

## Writing requirements

spec-first-feature step 2 has the wording rules. What is different at
audit scale:

- **Group by area with a short prefix** (EZ-HASH, EZ-LED, BOLT-RULE,
  BOLT-CFG). IDs are never reused, even for retired rows; bolt keeps L004
  reserved after retiring `quantify`.
- **Write each row from the verdict, not the README.** Where the verdict
  was partly or fails, the row states the decided behavior and the RFC
  says the row depends on a behavior change.
- **Choose one headline guarantee** and say so in the RFC. It is the row
  whose failure would make the tool pointless (ez: the lock is reproducible
  from committed inputs). Its law is usually a frame property, and stating
  it forces you to define exactly what the command may read: ez's `inputs`
  projection became part of the specification.
- **Contractual versus incidental output.** Requirements talk about exit
  statuses, bytes of written files, and plans; never about message wording.
  ez dropped a draft requirement for an error-message prefix the code did
  not implement, and its RFC says planners return structured outcomes that
  a renderer turns into text, so rewording touches no law.
- **For a linter, one row per rule**, worded from the header: "`nat`
  reports exactly one finding for each token the lexer reads as a Nat
  literal of 1000 or more, and none for any other token." Add cross-rule
  rows where they matter (BOLT-RULE-EXEMPT: an exempt path gets no
  findings; BOLT-RULE-INERT: comment and string contents do not change a
  code rule's findings).
- **A property that spans releases cannot be a law,** since a law sees one
  version. Split it: bolt's "codes are stable" became BOLT-OUT-1 (slug to
  code is one-to-one, Proved) and BOLT-OUT-6 (a released code is never
  renumbered, Trusted, enforced by review).

## The trust boundary

A table headed exactly `| ID | Assumption | Why it is trusted |`, listing
every Trusted row once. Common rows, all of which ez or bolt has:

- the Bend checker is sound (EZ-TRUST-1);
- the interpreter reads the World and executes plans faithfully
  (EZ-TRUST-2), one row per interpreter, each added in the PR that
  introduces it (bolt's REVIEW-14);
- the proof-gate runner reads the first line correctly (EZ-TRUST-4);
- each other program's answers (git's refs, nix's hash, the publisher's
  hash);
- each pinned dependency's proved guarantees, with the dependency and pin
  as the reason (EZ-TRUST-5, EZ-HASH-6);
- a repository setting the gate relies on (bolt's branch protection,
  which did not exist when the audit checked, BOLT-TRUST-7).

Narrow a trusted row whenever the project can check the answer itself. ez
checks every hub body against its hash, so "the hub serves what was
published" reduced to availability. Every Trusted row is a place the gate
stops looking, so the PR that adds one must justify it.

## Decided behavior changes

A section of the RFC listing every change the decisions imply, grouped by
the requirement that needs it. Each lands as its own PR, separate from the
rollout phases, and its PR description lists the change and how it was
checked against master's binary. A row that depends on a change stays
pending until the change lands. Later design docs add to this section
rather than keeping their own list (ez's lock-planner design added five).

## SPEC.md

SPEC.md at the repo root is the single requirement list. Use bolt's format
exactly, since bolt's `trace` rule reads it:

- requirement tables headed `| ID | Requirement | Level | Status | Law |`;
- Level `Proved` or `Trusted`; Status `proved` or `pending` for Proved,
  empty for Trusted;
- the Law cell as `<path> <law>` entries relative to SPEC.md, joined by
  `; ` (ez#64 fixed cells written as one path and a comma list, which
  `trace` misreads);
- a pending row may name tagged laws that prove part of it, and a "Left to
  prove" section says, per such row, what is proved and what is missing;
- a Format or Tagging section stating all of this in prose, plus which
  bolt rules enforce it and at what level;
- the trust boundary table at the end.

Land SPEC.md in the first rollout phase, from the RFC's tables, with the
laws that already prove a row tagged. The RFC keeps the reasoning; SPEC.md
keeps the list. spec-first-feature's `scripts/spec_rows.py` lists rows,
pending rows and next free IDs, which helps when checking a large SPEC.md.

## Keeping documents in step

Three documents move together, and a PR that changes one usually changes
all three:

| Document | Changes when |
| :---- | :---- |
| RFC | a decision is made or reversed; a row is added or reworded; the rollout plan changes |
| SPEC.md | a row is added, reworded or flipped; a Law cell changes; the trust boundary moves |
| inventory | a law is added, deleted or retagged; a finding is fixed; a work package changes state |

Fold decisions in as they are made, including ones made in a design doc
or in a PR discussion. The maintainer should never have to ask whether a
decision reached the spec. The inventory is a progress tracker: at the end
of the rollout, fold what still matters into the RFC and delete it.

## Asking the linter for changes

When bolt's rules do not fit the spec, change bolt, not the spec. ez asked
for an opt-in strict closed-law rule (bolt v0.9.0's `quantify`), for the
`trace` rule (bolt#44), and for tagged partial laws on pending rows
(bolt#106, after ez's SPEC.md needed them for EZ-VEN-1 and EZ-LED-6 to 8).
File an issue or a PR in bolt with the concrete case, pin the bolt commit
that has the change, and re-pin to the release tag when it ships.
