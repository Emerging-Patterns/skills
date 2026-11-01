---
name: spec-first-feature
description: Add or change behavior in a Bend project that keeps its guarantees as law files under bolt (ez, bolt, and siblings such as eztoml, ezhttp, ezjson, snap, shake) the spec-first way. The guarantee's law file comes first (its prose and its quantified laws, imported from LAWS.bend), then its proof file imported from PROOF.bend, a `bend PROOF.bend` run that fails, the proof, and a clean bolt run. Use this whenever the task is a new command, flag, lint rule, library function or guarantee, a change to what an existing one does, or a fix for a bug where the program decided the wrong thing, in any repo with LAWS.bend/PROOF.bend files. Use it even when the user only says "add X to ez", "new bolt rule for Y" or "fix ez add fetching a relative path from the wrong directory", without mentioning specs or laws.
---

# Spec-first features in ez + bolt projects

In these projects a behavior is guaranteed only if a law file states it and
`bend PROOF.bend` proves it. Each guarantee is one file, `laws/<Name>.bend`:
its prose as the opening comment, then its quantified laws. The file of the
same name under `proofs/` fills them. `LAWS.bend` and `PROOF.bend` at the
package root hold nothing but the imports of those files. The file name is
the guarantee's identity; there are no requirement IDs and no status
fields. Proved means `bend PROOF.bend` prints `ALL PROOFS CHECK` as its
first line, and bolt's `closed` (L002) rejects a law with no binder.
Together they make "is this feature trustworthy?" a question the gate
answers. So new work is done in an order that lets the gate answer it:
guarantee, then law, then code.

The consolidation that set this up (the spec audits of ez and bolt) is why
the rules below exist. It deleted hundreds of closed laws that looked like
evidence and proved nothing, and it found bugs that were all "the program
decided the wrong thing inside IO, where no law could reach". The steps are
there to stop both of those coming back.

## 0. Orient: the repo's own files win

Read these before you plan anything. When they disagree with this skill,
follow them, because they change faster than this skill does:

- `AGENTS.md` / `CLAUDE.md`: the hard rules, the gate commands, the Bend
  gotchas, and the Conventions section on the law layout (bolt's is the
  model).
- The root `LAWS.bend` header (what the laws cover, which shared
  definitions they use) and the `laws/` listing: find the guarantee your
  change belongs to before writing a new one.
- The bolt the project pins (`[tools.bolt]` in ez.toml, or the flake
  input), not bolt's main. The rule names and codes this skill mentions are
  current bolt's. bolt decides which files are law files and which are
  proof files by following imports from LAWS.bend and PROOF.bend, never by
  path: a file LAWS.bend reaches is a law file, a file only PROOF.bend
  reaches is a proof file, and whatever main.bend reaches is code, even
  when a law imports it.
- `bolt.bend` at the root: are `closed` and `coverage` errors? A
  `def trace()` there is left from the SPEC.md layout; on a bolt with #257
  it is an unknown-setting finding (C011), so delete it.
- `docs/rfc/*-spec.md`: the World/planner design and the decided behavior
  changes, if your change touches a command. Older RFCs name guarantees by
  the requirement IDs they had before `laws/`.

Then read the reference file for the repo you're in:

- ez, or any tool that does IO through a World/planner split:
  `references/ez.md`
- bolt, and especially a new lint rule: `references/bolt.md`
- a project that still keeps SPEC.md and mega LAWS.bend/PROOF.bend files,
  or has no laws yet: `references/adopting.md`
- a project (or a large area of one) whose laws and behavior disagree,
  where the job is the audit and the rollout rather than one feature: the
  `analyze-specify-prove` skill in this plugin

## 1. Classify the change

Which of these it is decides what you are allowed to edit:

| Kind | What changes under laws/ |
| :-- | :-- |
| New behavior | A new law file, or new laws in the file of the guarantee it extends |
| Change to a guaranteed behavior | The file's prose and its laws, together. This is a behavior change, so say so in the PR |
| Bug where code breaks a guarantee | Nothing. The guarantee was only partly proved, or the bug is in code that is trusted, not proved. Find out which |
| Bug where the guarantee was missing or wrong | A new or reworded law file stating the class of bugs this one belongs to, not this case alone |
| Bug in internal behavior, not interface | A law file for the class of behavior the bug broke; its prose says it is internal, not interface |
| Refactor | Nothing. Proof files and lemmas may be rewritten |

Law files are written by agents, never by the user, but each one is a
claim the user owns: behavior that must not change without review. That
covers the interface a library guarantees and internal behavior alike; the
prose says which it is. Ask the user before changing what an existing law
file says. Don't edit a law to make its proof pass: when a proof won't go
through, the code or the plan is usually wrong, not the claim. There are
exceptions. A law still being written in this change is a draft, and it
can move while you find out what it should say. An existing law can also
be wrong for a good reason: it overstated what the code can keep, or it
pinned an accident. Change it then, say why in the PR, and have it
reviewed. Deleting a law,
narrowing a file's prose, or moving a claim from a law to a trusted
comment weakens a guarantee, so it is also a behavior change that needs
review.

`laws/` is not only the interface. Anything that should not change
without someone deciding it should, a fixed bug included, gets a law file,
whether or not callers see it. What sets interface apart is the prose: a
law file says when it states internal behavior (a module under `src/`, a
helper's contract), so a reader knows it holds code in place rather than
promising callers anything. A law stated in a proof file is scaffolding
for a proof: the gate checks it, but it holds nothing in place, so never
put behavior there to keep it out of `laws/`. Message wording and other
output nobody should rely on gets no law at all.

Not every bug gets a law of its own. The pull is to write a law and proof
that only pin the fix for that one bug, the input that failed, instead of
the class of bugs it belongs to. Find the property the bug broke and state
it for every input. Often an existing guarantee was only partly proved and
the class belongs in its file; otherwise write the law for the class. A
law that only says "this input no longer fails" adds a file and holds
almost nothing in place.

## 2. Write the guarantee's prose first

Create `laws/<Name>.bend` before any code, starting with the prose, and
show it to the user if the wording involves a choice. The prose is the
design review. It is much cheaper to argue about one sentence than about a
diff.

- **Name.** CamelCase, describing the behavior: `GetFindsFirstPair`,
  `SpaceReportsBlanksAndWidth`. The name is the identity, so pick one that
  still fits when the laws grow.
- **Wording.** State it for every input, precisely enough that a law can be
  written from the prose alone. Use "exactly" when both directions matter
  (every instance is reported, and nothing else is). Say what is left
  unchanged, not just what changes. Name the decision, not the IO: "`ez init`
  on a world that already has a ledger plans no write", not "`ez init` checks
  whether ez.toml exists".
- **Partly proved.** If the laws will cover only part of it, the prose says
  which part is proved and what is still missing.
- **What it rests on.** A law several guarantees rest on gets its own law
  file, and each guarantee that uses it says `# also rests on:
  laws/X.bend` in its prose. A dependency's guarantee is cited by its law
  file (`eztoml's laws/GetFindsFirstPair.bend`). Trust a dependency's proved
  guarantees and never prove its internals.

Weak: "`ez add` names dependencies sensibly." Strong: "Two dependencies
added from different sources get different names in the ledger."

Some claims are outside the gate: another program's output (git, nix,
bend, the hub), foreign C/JS code, a property across releases, evaluation
order. Those get no law and no file. One that rests on a dependency is a
citation of the dependency's law file. One that holds for every Bend
project (the checker's soundness, the gate runner) is not written down at
all. One specific to this project is a comment on the code that assumes it,
in that module's header: `# Trusted, not proved: ...`. The PR description
justifies every new one. Each is a place where the gate stops looking, so
they should be rare and narrow.

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
  exists. If you have to parse it, the format assumption is trusted, and
  the parsing module's header says so.
- Don't reimplement an external tool (git plumbing, NAR, bend's parser)
  without a clear reason. Each one is a new place to diverge, and usually
  a new trusted assumption.

## 4. Write the laws, watch them fail

Under the prose in `laws/<Name>.bend`:

```
# <the guarantee, for every input, in plain words>
import Base
import ../src/<module>.bend as M

# LAW: <one-line plain statement>
law <snake_name>:
  for <binders>
  {<statement> : <Type>}
```

Then add `import ./laws/<Name>.bend as <Name>` to LAWS.bend. Definitions
several law files use go in `laws/defs/<Topic>.bend`, named for what they
hold, starting with a one-line comment saying what it is. Check that each
law actually says something:

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
- One guarantee may need several laws (eztoml's `GetFindsFirstPair` has
  five).

Then write `proofs/<Name>.bend`, starting `# proofs of laws/<Name>.bend`,
importing its law file as `Laws` and filling each law
(`def Laws.<snake_name>(...)`), and add
`import ./proofs/<Name>.bend as P<Name>` to PROOF.bend. Lemmas several
proofs use go in `proofs/lemmas/<Topic>.bend`, named and headed the same
way as defs. Neither kind of shared file gets a list of who uses it, or a
numbered name. A proof file may state lemma laws of its own: only PROOF.bend
reaches it, so bolt reads it as a proof file.

Fill the proof with a hole or a wrong term first and run `bend PROOF.bend`.
Watching it fail confirms the gate sees the law, and that the law isn't
trivially true.

## 5. Implement and prove

Write the code, then the proof. Follow the repo's Bend gotchas in AGENTS.md.
Most failed checks are one of those, not a real problem with the law.

If the proof can't land in this change, the law file lands with the laws
that are proved, and its prose says what is left and the plan (or an issue
linked from the PR). A partly proved guarantee is a normal state, not a
failure. Its laws are checked; a claim that only lives in an issue is
protected by nothing.

What never lands is a feature backed only by examples. That means no closed
law, no `# toward` trail (that was migration scaffolding, and ez and bolt
have deleted all of theirs), and no `tests/*.bend` for a claim Bend can
state. Tests belong only to the stay list of host/integration checks named
in AGENTS.md, and a test is never evidence for a guarantee.

## 6. Run the gate, read every finding

From the repo root, inside `nix develop`:

1. The proof gate: `bend PROOF.bend`, or whatever AGENTS.md names
   (`ez prove`). Its first line must be exactly `ALL PROOFS CHECK`.
2. bolt over the whole tree (`bolt`, no file arguments, because project
   rules only run on a whole-tree lint). In bolt, lint with the binary this
   tree just built, not the one on PATH.
3. `nix flake check`, which is what CI runs, and any job CI runs without
   nix. The repo's reference file and CI workflow list them.

Fix every finding. Don't lower a level in bolt.bend to get green. That is a
policy change for the user to decide, not a fix.

## 7. Report

In the PR description (or to the user), give:

- the law files added or reworded, by name;
- the laws in them, and whether each is a frame law or a direct law;
- any trusted assumption added, where its comment lives, and why;
- whether this is a behavior change to a released guarantee;
- anything only partly proved, and the plan for it.

Write it plainly. This is the record reviewers use to check that the change
kept the project's guarantees without re-running anything.
