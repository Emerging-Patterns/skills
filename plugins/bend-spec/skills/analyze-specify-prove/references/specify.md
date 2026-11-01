# Specify: the RFC, the decisions, and the law files

The worked examples are ez's `docs/rfc/ez-spec.md` and bolt's
`docs/rfc/bolt-spec.md`. bolt's RFC was written second and says which
positions it carried over from ez; read its "Two levels, and the positions
carried over from ez" section if the project you are working on depends on
either of them.

## Contents

- The RFC's shape
- Draft Status and REVIEW items
- The decision list
- Writing guarantees
- What is trusted
- Decided behavior changes
- The law files
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
| Glossary | every term a reader needs: ledger, World, planner, interpreter, closed and quantified law, proof gate, guarantee, law file, trusted |
| Background | what the project does; how it proves things today; why that leaves us unsure what is proved |
| Problem Statement | the two questions every behavior must answer (what is guaranteed; proved or assumed), goals and non-goals |
| Proposal | proved or trusted, and why nothing in between; the proof gate; the World model and how far each command is from it; guarantees by group, each followed by the evidence and the law sketch; retiring closed laws; the law layout; refactoring contract; what is trusted; decided behavior changes; how we will know it worked |
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
- [x] <!-- REVIEW (resolved): `owner/repo` allows `.` in both segments, so `vercel/next.js` is GitHub. The resolve guarantee (EZ-RES-3) states the new behavior. -->
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

Decide per case which accidents become guarantees. The pattern ez's
decisions followed: a behavior users will rely on and that a refactor could
silently break becomes a guarantee (refusing to overwrite a ledger, how a
dependency is named); a behavior that was simply wrong and that nobody
should rely on either way is fixed with a law stated in a proof file and a
line in the inventory (creating `.ez` in the current directory). Some
accidents had only closed laws as their record (ez's doctor drift report);
rather than lose the record when the closed laws go, they became
guarantees (EZ-VEN-5).

## Writing guarantees

spec-first-feature step 2 has the wording rules. What is different at
audit scale:

- **Group by area with a shared name prefix** (bolt's `Cli`, `Config`,
  `Lsp`, `Output`; the rule guarantees as `<Slug>Reports<What>`). The file
  name is the guarantee's identity, so the RFC cites it by that name.
- **Write each guarantee from the verdict, not the README.** Where the
  verdict was partly or fails, the prose states the decided behavior and
  the RFC says the guarantee depends on a behavior change.
- **Choose one headline guarantee** and say so in the RFC. It is the one
  whose failure would make the tool pointless (ez: the lock is reproducible
  from committed inputs). Its law is usually a frame property, and stating
  it forces you to define exactly what the command may read: ez's `inputs`
  projection became part of the specification.
- **Contractual versus incidental output.** Guarantees talk about exit
  statuses, bytes of written files, and plans; never about message wording.
  ez dropped a draft requirement for an error-message prefix the code did
  not implement, and its RFC says planners return structured outcomes that
  a renderer turns into text, so rewording touches no law.
- **For a linter, one guarantee per rule**, worded from the header: "`nat`
  reports exactly one finding for each token the lexer reads as a Nat
  literal of 1000 or more, and none for any other token." Add cross-rule
  guarantees where they matter (bolt's `ExemptPathsYieldNoFindings`:
  an exempt path gets no findings; `CodeRulesIgnoreCommentsAndStrings`:
  comment and string contents do not change a code rule's findings).
- **A property that spans releases cannot be a law,** since a law sees one
  version. Split it: bolt's "codes are stable" became
  `OutputCodesMapOneToOne` (slug to code is one-to-one, proved) and a
  comment on `src/codes.bend` that a released code is never renumbered,
  which review keeps.

## What is trusted

What the gate cannot check gets no law and no file. Each assumption goes
one of three ways:

- one that holds for every Bend project is not written down: the Bend
  checker is sound, the proof-gate runner reads the first line correctly;
- one that rests on a pinned dependency is a citation of that dependency's
  law file in the prose of the guarantee that uses it
  (`eztoml's laws/GetFindsFirstPair.bend`);
- one specific to this project is a comment on the code that assumes it,
  in that module's header: `# Trusted, not proved: ...`. The usual ones:
  each interpreter reads the World and executes plans faithfully (said in
  the PR that introduces the interpreter); each other program's answers
  (git's refs, nix's hash, the publisher's hash); foreign code, such as
  bolt's directory walk in `src/walk/disk.bend`.

A repository setting the gate relies on (bolt's branch protection, which
did not exist when the audit checked) has no code to sit on, so bolt's
AGENTS.md says it.

Narrow a trusted assumption whenever the project can check the answer
itself. ez checks every hub body against its hash, so "the hub serves what
was published" reduced to availability. Every one is a place the gate
stops looking, so the PR that adds one must justify it.

## Decided behavior changes

A section of the RFC listing every change the decisions imply, grouped by
the guarantee that needs it. Each lands as its own PR, separate from the
rollout phases, and its PR description lists the change and how it was
checked against master's binary. A guarantee that depends on a change
stays partly proved until the change lands. Later design docs add to this section
rather than keeping their own list (ez's lock-planner design added five).

## The law files

`laws/` is the single list of guarantees, in the layout bolt and eztoml
use (spec-first-feature's SKILL.md and `references/adopting.md`):

- LAWS.bend and PROOF.bend at the package root hold only imports, one pair
  per repo;
- each guarantee is `laws/<Name>.bend`, its prose on top and its quantified
  laws under it, proved by `proofs/<Name>.bend`;
- a guarantee proved only in part says in its prose what is proved and what
  is missing;
- shared definitions go in `laws/defs/`, shared lemmas in `proofs/lemmas/`;
- the root LAWS.bend header says what the laws cover, the gate, and where
  the reasoning lives.

Land the law files in the first rollout phase, from the RFC, with the laws
that already prove a guarantee moved into its file. The RFC keeps the
reasoning; `laws/` keeps the list.

## Keeping documents in step

Three documents move together, and a PR that changes one usually changes
all three:

| Document | Changes when |
| :---- | :---- |
| RFC | a decision is made or reversed; a guarantee is added or reworded; the rollout plan changes |
| law files | a guarantee is added, reworded or proved further; a trusted assumption is added or removed |
| inventory | a law is added, deleted or moved; a finding is fixed; a work package changes state |

Fold decisions in as they are made, including ones made in a design doc
or in a PR discussion. The maintainer should never have to ask whether a
decision reached the spec. The inventory is a progress tracker: at the end
of the rollout, fold what still matters into the RFC and delete it.

## Asking the linter for changes

When bolt's rules do not fit the spec, change bolt, not the spec. ez asked
for an opt-in strict closed-law rule (bolt v0.9.0's `quantify`), and the
move to one law file per guarantee needed bolt to find law and proof files
by following imports (bolt#257, which also removed `trace`).
File an issue or a PR in bolt with the concrete case, pin the bolt commit
that has the change, and re-pin to the release tag when it ships.
