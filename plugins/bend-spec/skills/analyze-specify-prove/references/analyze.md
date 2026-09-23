# Analyze: what the project actually proves and does

The worked examples are ez's `docs/rfc/ez-law-inventory.md` (read at
`f009e42`) and bolt's `docs/rfc/bolt-law-inventory.md` (read at `a38e87a`).
Open one of them before you write your own; the shape below is theirs.

## Contents

- The inventory document
- Classifying laws
- Checking requirements against the code
- Tracing what a command reads
- Exercising the real binary
- Root-causing against the reference implementation
- Sorting the findings
- For a linter: rules against their headers

## The inventory document

Name it `docs/rfc/<project>-law-inventory.md`. It is the companion to the
RFC, and the RFC cites it for every verdict. State at the top the commit it
was read at, the bend version, and how the gate and linter were run, so a
reader can tell stale evidence from current.

Sections, in this order:

1. **How to read the tables.** Define every column value (below).
2. **The gate and the linter on the project itself.** Run every PROOF.bend
   and record the first line of output, the exit status and the time; run
   the pinned bolt over the tree. bolt's inventory found that its own
   self-lint said "clean" only because the strict rule was off, which is
   the kind of thing this section exists to surface.
3. **Summary.** Per LAWS.bend: laws, quantified, closed, quantified proved
   by `{==}`, and anything project-specific (bolt counted closed laws that
   pin message text). Then one paragraph: "what the project proves today".
   ez's was one real guarantee; bolt's was "nothing about the linter".
   Writing that paragraph honestly is most of the value of the audit.
4. **Inventory.** One table per LAWS.bend.
5. **Coverage by requirement.** Each draft requirement and the laws that
   point toward it.
6. **Requirements against code.** Verdicts, below.
7. **What each command reads.** Below.
8. **Findings.** Sorted, below.

Later it gains a progress section per rollout phase (ez: "Phase three
progress", one row per work package with state and what landed). Keep it
current in every PR; it is how the maintainer and the next agent know where
things stand. When the rollout ends, fold what still matters into the RFC
and delete the file.

## Classifying laws

| Column | Values |
| :---- | :---- |
| Kind | `Q` quantified (at least one `for` or `exs` binder), `C` closed |
| Proof | `{==}` (or `refl`) when the whole proof is `{==}`, `struct` when it matches, recurses or rewrites |
| Claim | what the law states, in one line, about the input it is really about |
| Points toward | the requirement ID it supports, `new: <short name>` for behavior the draft should add, or `none (<reason>)` |

Reasons for `none` that recurred: `helper pin` (one private helper on one
input), `wording` (pins text nobody depends on), `definitional` (restates a
definition), `wiring` (restates how two defs compose), `refactor-eq` (holds
a rewrite equal to the old definition it replaced), `fixture` (a law about
test scaffolding), `core library` (code the binary does not run).

Why these columns matter:

- A closed claim is about one input even when its name reads like a
  general statement (`add_twice_is_once` over one fixed ledger). Write the
  claim so that is visible.
- A quantified law proved by `{==}` never inspects its binders. It passes
  bolt's closed-law rules and proves only how a definition unfolds. Count
  these separately; some are fine lemmas, but none is a guarantee.
- A `for` binder the statement never uses makes a closed law look
  quantified. bolt's `closed` accepted this; check by reading.
- Refactor-equivalence laws (`new == old` for a rewrite) keep a second
  specification alive that nobody reads. ez deleted all 13 with their
  `old.*` definitions.

Do the counting with a script if the files are large, but read every law.
The "points toward" column is a judgment, and it is what the rollout uses
to decide what to delete and what each new law replaces.

## Checking requirements against the code

For each requirement in the draft (or in the README, if there is no
draft), give a verdict with file and line evidence:

| Verdict | Meaning |
| :---- | :---- |
| holds | the code does this for every input you can see |
| partly | it does for some inputs; say which fail |
| fails | it does not; say what it does instead |
| as trusted | it is about another program; nothing to check here |

Read the code, then confirm the interesting verdicts by running the binary
(below), and mark which ones you confirmed and which are "by reading". A
verdict of partly or fails becomes either a reworded requirement or a
decided behavior change in stage 2; a verdict alone never changes code.

## Tracing what a command reads

For each command in scope, list every input it observes, with the line
that reads it: files (tracked or not), environment variables, other
programs' output, the network, caches, the clock. ez's table for `ez lock`
had one row per read with a decision column, and it showed that the lock
read `.ez/origins.toml`, `BEND_HUB`, untracked `.bend` files and
`bend version`, none of which a fresh clone has. That table became the
definition of the World, and the reads outside it became decided behavior
changes.

While tracing, note every place a failed or missing read turns into a
default value (ez's `read.git` turned a missing manifest into an empty
file list and exited 0), every walk that stops silently when its fuel runs
out, and every decision function called with a constant where a real value
belongs (ez's `U.judge` was always called with agreement fixed to true, so
its drift arm was dead). Each of these is a bug a law would catch once the
decision is pure.

## Exercising the real binary

Build the binary from a fresh copy of the tree and run each command the
way a user would, in scratch directories. This found more real bugs than
every existing test and law put together, in both projects. The recipe and
the side-by-side comparison are in `debugging.md`. Try at least:

- every documented install and build step, literally, on a clean checkout
  (a missing `bin/` directory broke ez's README build);
- each command in an empty directory, in a project with no dependencies,
  and twice in a row (`ez init` overwrote an existing ledger; every command
  created `.ez` and `bin`; `ez doctor` failed a project with no deps);
- inputs just outside the happy path: non-ASCII file contents, relative
  paths from a subdirectory, names that collide, a missing config file
  (`ez remove` with no ledger created one);
- the headline guarantee directly: for ez, delete the lock in a fresh
  clone, relock, and `cmp`.

Record each result as "Confirmed" in the findings, with the command.

## Root-causing against the reference implementation

When the project and another tool disagree, find out which is right from
the other tool's source, not from the project's docs or comments. ez's
"sha256" folded each character to its low byte. The RFC first kept the
fold, believing bend did the same. Reading bend's own source (the JS is
embedded in the bend binary; `strings $(which bend) | grep -n createHash`
finds it) showed `createHash("sha256").update(text)`, which hashes UTF-8,
and a publish of a non-ASCII file confirmed it. The REVIEW item was marked
"resolved, then reversed" with that evidence.

The same check applies before designing a behavior that depends on another
tool. The RFC wanted `ez publish` to compare hashes before uploading. bend
2.0.25 has no way to report the hash without uploading, so the item was
resolved as "no change", documented in the requirement's wording, and the
workaround that did exist (a dead hub address and a scraped progress line)
was rejected in writing because it relies on output bend does not promise.

## Sorting the findings

Put each finding under one heading, with "Confirmed" or "by reading":

- **Behavior the code guarantees that no requirement mentions.** Often
  good quantified laws with no row (ez's ledger model laws became
  EZ-LED-1 to 5).
- **Behavior that looks accidental.** Candidates for a fix, a row, or
  nothing. Do not decide here; list them for the maintainer.
- **Requirements with no corresponding code.** The draft promised
  something nobody built (ez's `ez: <area>:` error prefix).
- **Bugs.** The code breaks a requirement everyone agrees on.

Keep findings "recorded, not resolved". The RFC carries a REVIEW item for
each one a requirement depends on.

## For a linter: rules against their headers

bolt's rules each have a header comment saying what they report. Its
audit read each header as the requirement and checked the code against it,
with a scratch project per rule. Every correctness rule but one and every
suspicious rule but one had a confirmed false positive or false negative.
Two outcomes are possible per rule, and REVIEW-2 decided the policy: fix
the code where the header states the intent users rely on, and narrow the
header where the code's behavior is a deliberate heuristic (`fuel`
matching by parameter name). Stating the broad header as a requirement
would make the row fail forever.

A run over sibling repositories (ez, eztoml, ezhttp, ezjson, snap, shake)
is a good way to find a rule's false positives. It is a development tool,
not evidence: a corpus snapshot is a closed law on a bigger input. Treat
each false positive it surfaces as a counterexample the row's law must
rule out.
