# Bringing a project under the law layout

For a project that still keeps SPEC.md and mega LAWS.bend/PROOF.bend files
(the layout eztoml and bolt had before eztoml#90 and bolt's
feat/law-imports), or a sibling library or new Bend project with laws but
no layout at all. Do this as its own change before the feature, not mixed
into one. bolt and eztoml are the models: read their root LAWS.bend header,
a few `laws/*.bend` and `proofs/*.bend` files, and bolt's AGENTS.md
Conventions section first.

The end state, whichever way you get there:

- `LAWS.bend` and `PROOF.bend` at the package root, holding only imports
  (`import ./laws/<Name>.bend as <Name>`; `import ./LAWS.bend as Laws` and
  `import ./proofs/<Name>.bend as P<Name>`), one pair per repo. A
  subdirectory gets no pair of its own.
- One guarantee per `laws/<Name>.bend`, its prose on top, and its proofs in
  `proofs/<Name>.bend`. Shared definitions in `laws/defs/<Topic>.bend`,
  shared lemmas in `proofs/lemmas/<Topic>.bend`, each named for what it
  holds and starting with a one-line comment saying what it is.
- No requirement IDs, no tag lines, no status fields, and no trust table.
  A migrated project keeps its old table as `docs/SPEC.md`, a record the
  RFCs' IDs point into; nothing reads it.

## Migrating from SPEC.md

`scripts/split_laws.py` is the converter that moved eztoml and bolt. It
reads one LAWS.bend/PROOF.bend pair and the SPEC.md rows that name its
laws, and writes the per-guarantee files for that pair.

```
split_laws.py <pair-dir> <names.json> [--spec SPEC.md] [--group-names g.json] [--dump out.json] [--write]
```

1. **Pin a bolt with #257.** It removed `trace` (L005), so a `def trace()`
   left in bolt.bend is an unknown-setting finding (C011); delete it in this
   change. It also stopped `space` (S002) counting import lines. Until #257
   is in a release, pin the commit and say so in the PR.
2. **Choose the names.** `names.json` maps each Proved row's ID to its file
   name: `{"TOML-GET-1": "GetFindsFirstPair"}`. Names are CamelCase and
   describe the behavior. A row mapped to `""` is dropped: its guarantee is
   gone, and a law only it cited is treated like a law no row cites.
   Trusted rows need no name.
3. **Run it without `--write`** to see the plan: how many law, proof,
   lemma and def files it would write, the largest ones, the helpers
   nothing reaches (which it drops), the trust rows and Trusted requirement
   rows left for you to place, and the IDs still cited in moved comments
   that no law file replaces. Pass `--spec` when SPEC.md is not in the pair
   directory. Read the plan before going on: a law cited by several rows,
   or by none, gets a file of its own named after the law, and each row
   that rests on it gets an `also rests on:` line. Check those names read
   as behaviors.
4. **Name the shared groups.** Helpers that several files use are grouped
   by the exact set of files that use them, and small groups are folded
   into wider ones where that makes no import cycle. Left alone, a group is
   named after its commonest dotted prefix, which gives names like
   `Common18`. Run with `--dump groups.json` to list each group (its key,
   the files that use it, its size and its items), then write `g.json`
   mapping each key to `{"name": "PairPresence", "about": "<one line>"}`,
   and rerun with `--group-names g.json`. The `about` line becomes the
   file's opening comment.
5. **Run it with `--write`.** It writes `laws/`, `proofs/`, `laws/defs/` and
   `proofs/lemmas/` under the pair directory, replaces LAWS.bend and
   PROOF.bend with their imports, and lists the dropped helpers in
   `.split_dropped.txt`. Read that list, then delete the file.
6. **Merge nested pairs into the root.** The converter works one pair
   directory at a time. A repo with pairs in subdirectories runs it once per
   pair (with `--spec` pointing at the root SPEC.md), then moves every
   generated file to the root `laws/` and `proofs/`, fixes their relative
   imports, adds their imports to the root LAWS.bend and PROOF.bend, and
   deletes the nested pairs. Fix the `also stated in:` lines the converter
   writes for a row whose laws were split across pairs: after the merge
   they are one file.
7. **Edit the prose.** Write the root LAWS.bend header the way bolt's and
   eztoml's read: what the laws cover, the gate, and where the reasoning
   lives (an RFC that names guarantees by their old IDs says so). A row the
   converter marked pending says in its prose what is proved and what is
   left.
8. **Move the trust rows into the code.** Each trust row, and each
   Trusted requirement row, goes one of three ways. One that holds for every
   Bend project (the checker is sound, the gate runner reads the first line)
   is dropped. One that rests on a dependency becomes a citation of that
   dependency's law file in the prose of the guarantee that uses it. One
   specific to this project becomes a comment on the code that assumes it,
   in that module's header: `# Trusted, not proved: ...`.
9. **Remove the IDs.** The converter rewrites an ID it has a name for into
   the law file's path; replace the ones it reports by hand. Then move
   SPEC.md to `docs/SPEC.md` (its links into `docs/` lose that prefix),
   point the root LAWS.bend header at it as the table the files replaced,
   and update AGENTS.md, the README and CI where they mention SPEC.md, its
   rows, or `trace`.
10. **Gate, then lint.** `bend PROOF.bend` prints `ALL PROOFS CHECK` as its
    first line, then `bolt` over the whole tree is clean. The converter
    folds lines over 120 wide; a parameter line it cannot fold gets a
    `# noqa: S002`.
11. **Downstream.** A dependent that cited this project's SPEC row IDs
    cites the law files instead (`eztoml's laws/GetFindsFirstPair.bend`).

## A project with laws but no SPEC.md

For eztoml, ezhttp, ezjson, snap, shake, or a new Bend library whose laws
sit in a LAWS.bend/PROOF.bend pair with no requirement list. Write the law
files by hand.

1. **Inventory, don't invent.** List what the existing quantified laws
   actually prove, and give each guarantee its law file, with the laws that
   prove it. List what the README promises that no law proves: each is a
   law file whose prose says it is not proved yet, with whatever laws prove
   part of it. Closed laws are not evidence: note them in the PR and plan
   their deletion. Libraries that implement a standard (TOML 1.0, RFC 9110,
   RFC 3986) name the standard's section in the prose.
2. **What it trusts.** Cite each pinned dependency's law files this project
   rests on, and put a `# Trusted, not proved:` comment on any code whose
   behavior is assumed rather than proved.
3. **Turn on the rules.** In the root bolt.bend, add `def closed() ->
   String: "error"`. Get `bolt` clean over the whole tree.
4. **Layout and pins.** Current ez expects `main.bend` at the root as the
   whole interface and every other file under `src/`: consumers import only
   `main.bend`, and everything under `src/` may change in any release
   (shake and ezjson are laid out this way). Mark each undotted IO def or
   re-export in `main.bend` `# noqa: L001 <reason>` (e.g. `IO wrapper,
   trusted, not proved` or `re-export of Qs.get, laws in laws/`) so
   `coverage` does not ask for a law no one can state, then set `coverage`
   to error. Dotted defs (`http.get`, `text.fill`) are helpers that bolt
   never grades for coverage, so a noqa on one is itself an S005 finding.
   Don't keep an `ENTRY.bend` of wrapper laws: a file importing foreign code
   can only print `SOME PROOFS FAIL`, so its check proves nothing.
   Pin the linter in the lock (`[tools.bolt]` in ez.toml) and relock with
   the pinned ez, so CI's bolt is the one you ran. A command-line program
   also trusts what the compiled Bend runtime does to argv before `main`
   (it takes the first `--`, `--help`, `--threads` and `--gpu`): say so in
   a `# Trusted, not proved:` comment on the code that reads argv, and in
   the README.

This is the short form, for a library whose laws are few and mostly
quantified already. When the inventory turns up many closed laws, IO
decisions no law can reach, or behavior the maintainer has to rule on, use
the `analyze-specify-prove` skill instead: it covers the full audit, the
RFC and the rollout.

After this, new features in the project follow SKILL.md like any other.
