# ez specifics

Read ez's README.md, SPEC.md (the Tagging section and "Left to prove") and
`docs/rfc/ez-spec.md` ("The World model") first.

## Commands are planners

Almost everything ez does is IO: git, the hub, BEND_LIB, the working tree.
Laws can't quantify over IO, so each command is being split into two parts:

```
real system ──read──▶ World ──▶ planner (pure, laws) ──▶ Plan ──▶ interpreter
```

- **World**: every input the command can see, as a value (the ledger text,
  committed tree, lib, env, bend version, hub answers, remotes). A command
  reads only the fields it needs.
- **Planner**: `def <cmd>_plan(w: World, a: <Cmd>Args) -> Pair(List(Effect), Outcome)`.
  It decides everything: what to pin, what to write and with what bytes,
  what to print, and the exit status.
- **Interpreter**: reads the World and performs the effects in order. It
  makes no decisions. Its faithfulness is one Trusted row (EZ-TRUST-2), so
  keep it small enough to review line by line.

A new command or flag is written in this form from the start. A change to a
command that isn't converted yet either converts the part it touches, or
puts its new decision in a pure helper with explicit inputs that the
eventual planner can call. Don't add new decisions inside IO functions.

Laws are stated over planners and quantify over worlds. The shapes that
would have caught ez's known bugs:

- "`init` on a world that has a ledger plans no write" (a no-clobber frame
  law)
- "two deps with different sources get different names" (injectivity)
- "a relative path target is read from the directory the row names, for
  every cwd" (EZ-RES-3's neighbour; decide which directory in the row)
- "no plan writes outside the project root" (a frame law over every
  Effect's path, for every command)
- "`doctor` on a project with no deps exits 0"

When you add an Effect constructor, extend the "writes nothing outside the
root" frame law to cover it.

## Where ez's trust lives

Trusted rows point at other programs: git (EZ-RES-7), nix (EZ-HASH-5),
`bend --publish` (EZ-HASH-4), the hub (EZ-TRUST-3), and pinned
dependencies' own proofs (EZ-TRUST-5, EZ-HASH-6). A feature that leans on a
new external answer needs a new Trusted row. Where possible, design it so
ez checks the answer instead. The hub is trusted only for availability,
because ez checks every body against its hash (EZ-FETCH-1). Do the same:
verify by content hash, and compare before acting instead of after.

Be wary of reimplementing git or NAR plumbing. Each reimplementation is a
new place to diverge from the real tool.

## End-to-end guarantees

Once two commands are both planners, cross-command laws become possible and
are the most valuable kind. For example: "`ez add` then `ez lock` on a fresh
clone reproduces the lock `ez add` wrote" (EZ-DOC-3's big sibling), and
"`ez lock --check` fails exactly when `ez lock` would change the lock". When
a feature makes one of these statable, add the row.

## Gate

`ez prove` is the proof gate. `nix flake check` is CI (mkProofs + mkLint).
bolt runs with `trace` over the tree. Never `ez publish` or
`bend --publish`: an upload is public and can't be undone.

## Migration leftovers

`# toward EZ-X-N` trails are closed laws kept during consolidation. Don't
add new ones. If your change lands a quantified law for a row that has a
trail, delete the trail in the same change.
