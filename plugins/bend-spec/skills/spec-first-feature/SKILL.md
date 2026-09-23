---
name: spec-first-feature
description: Add or change behavior in a Bend project that keeps a SPEC.md traced by bolt (ez, bolt, and siblings such as eztoml, ezhttp, ezjson, snap, shake) the spec-first way. The SPEC.md requirement row comes first, then a quantified law in LAWS.bend, the proof in PROOF.bend, the tag and status flip, and a clean proof gate plus bolt `trace` run. Use this whenever the task is a new command, flag, lint rule, library function or guarantee, a change to what an existing one does, or a fix for a bug where the program decided the wrong thing, in any repo with SPEC.md and LAWS.bend/PROOF.bend files. Use it even when the user only says "add X to ez", "new bolt rule for Y" or "fix ez add fetching a relative path from the wrong directory", without mentioning specs or laws.
---

# Spec-first features in ez + bolt projects

In these projects a behavior is guaranteed only if SPEC.md names it and a
quantified law proves it (or the trust boundary names it). bolt's `trace`
rule (L005, BOLT-LAW-5) checks mechanically that the SPEC.md rows and the law
tags agree, and `closed` (L002) rejects laws with no binder (`quantify`,
L004, in bolt v0.9.0 and older pins). Together they
make "is this feature trustworthy?" a question the gate answers. So new work
is done in an order that lets the gate answer it: requirement, then law, then
code.

The consolidation that set this up (the spec audits of ez and bolt) is why
the rules below exist. It deleted hundreds of closed laws that looked like
evidence and proved nothing, and it found bugs that were all "the program
decided the wrong thing inside IO, where no law could reach". The steps are
there to stop both of those coming back.

## 0. Orient: the repo's own files win

Read these before you plan anything. When they disagree with this skill,
follow them, because they change faster than this skill does:

- `AGENTS.md` / `CLAUDE.md`: the hard rules, the gate commands, the Bend
  gotchas.
- `SPEC.md`: the Format/Tagging section (the exact table headers, ID
  pattern, tag placement), the group your change belongs in, and the trust
  boundary.
- The bolt the project pins (`[tools.bolt]` in ez.toml, or the flake
  input), not bolt's main. The rule names and codes this skill mentions are
  current bolt's. ez, for example, stays on v0.9.0 with `quantify` (L004)
  until its last `# toward` trail is gone, and has no `trace` yet.
- `bolt.bend` at the root: is `trace` on, and at what level? Are `closed` (or
  `quantify`) and `coverage` errors? If `trace` is off or at warn, the project hasn't reached
  the consolidation finish line. Do the work the same way anyway, but tell
  the user the gate won't catch a mismatch.
- `docs/rfc/*-spec.md`: the World/planner design and the decided behavior
  changes, if your change touches a command.

Then read the reference file for the repo you're in:

- ez, or any tool that does IO through a World/planner split:
  `references/ez.md`
- bolt, and especially a new lint rule: `references/bolt.md`
- a sibling library with no SPEC.md yet: `references/adopting.md`

`scripts/spec_rows.py SPEC.md` lists the rows by group, the pending ones, and
the next free ID for a prefix. Use it to pick IDs and to check your row
parses as the tables expect.

## 1. Classify the change

Which of these it is decides what you are allowed to edit:

| Kind | What changes in SPEC.md | What may change in LAWS.bend |
| :-- | :-- | :-- |
| New behavior | New row(s) | New tagged laws |
| Change to a guaranteed behavior | The row's wording. This is a behavior change, so say so in the PR | The tagged law's statement, to match the new row |
| Bug where code breaks a Proved row | Nothing | Nothing. The law was pending, or the bug is in trusted code. Find out which |
| Bug where the requirement was missing or wrong | New or reworded row | New tagged law that would have caught the bug |
| Accidental behavior not worth guaranteeing | Nothing. Note it in the law inventory (`docs/rfc/*-law-inventory.md`) | Fix it, with an untagged quantified law |
| Refactor | Nothing | Nothing tagged. Proofs may be rewritten, untagged laws may change |

The refactoring contract behind this: a tagged law's statement in LAWS.bend
is human-owned. It changes only when its SPEC.md row changes. Never edit one
to make a proof pass. If the proof won't go through, the code or the plan is
wrong, not the claim. Moving a row from Proved to Trusted weakens a
guarantee, so it is also a behavior change that needs review.

Not every bug earns a row. A row is a promise to keep the behavior forever.
If the old behavior was an accident and nobody should rely on the new one
either, fix it without a row: ez did this for `.ez`/`bin` being created in
the current directory, and for `ez doctor` on a project with no deps. Ask
the user when it isn't clear which kind a bug is. Padding SPEC.md with
incidental rows makes the real guarantees harder to find.

## 2. Write the requirement row first

Add the row before any code, with status `pending`, and show it to the user
if the wording involves a choice. The row is the design review. It is much
cheaper to argue about one sentence than about a diff.

- **ID.** Next free number in the group (`spec_rows.py --next EZ-RES`). IDs
  are never reused, even for retired rows. A new area gets a new group
  prefix in the same style.
- **Level.** `Proved` unless the claim is genuinely about something outside
  the gate: another program's output (git, nix, bend, the hub), foreign
  C/JS code, a property across releases, or evaluation order. A Trusted row
  goes in both the requirement table and the trust table, with a real "why",
  and the PR description has to justify the trust boundary growing. Every
  Trusted row is a place where the gate stops looking, so they should be
  rare and narrow.
- **Wording.** State it for every input, precisely enough that a law can be
  written from the sentence alone. Use "exactly" when both directions matter
  (every instance is reported, and nothing else is). Say what is left
  unchanged, not just what changes. Name the decision, not the IO: "`ez init`
  on a world that already has a ledger plans no write", not "`ez init` checks
  whether ez.toml exists".

Weak: "`ez add` names dependencies sensibly." Strong: "Two dependencies
added from different sources get different names in the ledger."

## 3. Design so the law can reach the decision

A law can only quantify over values. If the decision is made inside an IO
function, nothing can prove it. That is the one structural lesson of the
consolidation. So before writing code:

- Put every decision in a pure function of explicit inputs: a planner that
  takes the world it can see and returns the plan (effects plus outcome plus
  exit status). The IO wrapper reads the inputs, runs the plan, and decides
  nothing.
- New IO goes in planner form from the start, even if the command next to it
  isn't converted yet. Otherwise you add to the conversion backlog.
- Don't turn a missing or failed read into a default value inside IO (the
  `read.git` bug: a missing manifest silently became an empty file list).
  Make it an explicit input or outcome the planner handles.
- Don't string-match another program's output when a structured answer
  exists. If you have to parse it, the format assumption is a Trusted row.
- Don't reimplement an external tool (git plumbing, NAR, bend's parser)
  without a clear reason. Each one is a new place to diverge, and usually
  a new Trusted row.

## 4. Write the law, watch it fail

In the LAWS.bend of the project directory that owns the code:

```
# LAW: <one-line plain statement, usually the requirement's own words>
# EZ-XXX-N
law <snake_name>:
  for <binders>
  {<statement> : <Type>}
```

The tag line `# <ID>` sits alone on its line, inside the unbroken comment
block directly above `law`. A law can carry several tags, one per line.

Then check that the law actually says something:

- **Every binder is used in a way that matters.** A law whose proof is
  `{==}` over binders the statement never inspects is a closed law in
  disguise. It passes `closed`, and it proves nothing. If the proof goes
  through by `{==}` straight away, suspect the law before you celebrate.
- **Frame laws.** For anything that writes or reports, state what it leaves
  alone as well as what it does. Examples: every other line is
  byte-identical; the plan writes nothing outside the project root; the rule
  reports nothing on code without the pattern.
- **Both directions for "exactly".** Prove the count or set equality, not
  just "at least one finding".
- One requirement may need several laws (EZ-RES-3 has eight). List them all
  in the Law cell.

Fill PROOF.bend with a hole or a wrong proof and run the proof gate. Watching
it fail first confirms the gate sees the law, and that the law isn't
trivially true.

## 5. Implement and prove

Write the code, then the proof. Follow the repo's Bend gotchas in AGENTS.md.
Most failed checks are one of those, not a real problem with the law.

If the proof can't land in this change, the row lands `pending` with a
stated plan: ez's "Left to prove" table, or an issue linked from the PR.

Pending with partial laws is a normal state, not a failure. When a law
proves part of a pending row, tag it with the row's ID, list it in the Law
cell, and say in "Left to prove" what is proved so far and what is missing
(EZ-VEN-1 is the model). A tagged partial law is checked. An untagged one
isn't protected by anything.
What never lands is a feature backed only by examples. That means no closed
law, no new `# toward` trail (those are migration scaffolding and are being
deleted), and no `tests/*.bend` for a claim Bend can state. Tests belong
only to the stay list of host/integration checks named in AGENTS.md, and a
test is never evidence for a row.

## 6. Flip the row

When the last law for the row lands, set status `proved` in the same change.
The Law cell lists every law as a `<path> <law>` entry relative to SPEC.md,
entries separated by `; ` (`ez/LAWS.bend a; ez/LAWS.bend b`, not
`ez/LAWS.bend a, b`). If "Left to prove" had a row for it, delete that row.

`trace` reports a proved row whose law is missing, has no binder, or lacks
the tag. bolt's `trace` as released also reports a tag on a pending row,
and a Law cell on a pending row. That clashes with partial laws above, and
the intended fix is in the rule, which should check tags on a pending row
the same way it checks a proved row. Until the project's pinned bolt has
that fix, a project that tags partial laws can't run `trace` at error. Say
so to the user, and don't untag partial laws to get it green.

## 7. Run the gate, read every finding

From the repo root, inside `nix develop`:

1. The proof gate: `ez prove`, or whatever AGENTS.md names
   (`ez test --unit-only` in bolt today). Every PROOF.bend must print exactly
   `All terms check.` as its first line.
2. bolt over the whole tree (`bolt`, no file arguments, because `trace` only
   runs on a whole-tree lint). In bolt, lint with the binary this tree just
   built, not the one on PATH.
3. `nix flake check`, which is what CI runs, and any job CI runs without
   nix. The repo's reference file and CI workflow list them.

Fix every finding. Don't lower a level in bolt.bend to get green. That is a
policy change for the user to decide, not a fix.

## 8. Report

In the PR description (or to the user), give:

- the row(s) added or reworded, with ID, level and status;
- the laws that prove them, and whether each is a frame law or a direct law;
- whether the trust boundary grew, and if it did, why;
- whether this is a behavior change to a released guarantee;
- anything left pending, and the plan for it.

Write it plainly. This is the record reviewers use to check that the change
kept the project's guarantees without re-running anything.
