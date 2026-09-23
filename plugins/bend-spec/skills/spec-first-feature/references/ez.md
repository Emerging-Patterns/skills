# ez specifics

Read these first: ez's README.md; SPEC.md (the Tagging section and "Left to
prove"); `docs/rfc/ez-spec.md`; and `docs/rfc/ez-lock-planner.md`, which is
the worked example of a command in planner form. Where they disagree with
this file, they win.

## Commands are planners

Almost everything ez does is IO: git, the hub, BEND_LIB, the working tree.
Laws can't quantify over IO, so each command is split into a pure planner
and an interpreter that decides nothing.

**One World per command, holding only what that command reads.** There is
no shared World type with every input in it. `ez lock`'s World is its args,
the ledger text, the listing of committed `.bend` files, and the answers to
its questions. It has no environment, no clock, no `bend version`, no old
lock, no `.ez/origins.toml` and no untracked files, because the lock doesn't
read them, so there is nothing for a law to quantify over. When you design
a new command's World, list what the command must read, and put in nothing
else. Every extra field is an input a law has to account for.

**The planner asks, and the interpreter answers.** A command whose inputs
depend on earlier answers (an import graph, a remote's tags) doesn't get a
World with everything prefetched. It asks for what it needs:

```
wants(w: World) -> List<Ask>   # questions still open; no verification here
plan(w: World)  -> Plan        # effects + outcome, called once wants is empty
step(w: World)  -> Step        # Asking{asks} while wants(w) is non-empty, else Run{plan}
answer(ask: Ask) -> IO(Answer) # the interpreter: one IO action per Ask
```

The interpreter loops: call `wants`, answer each `Ask`, append the replies to
the World, and repeat until `wants` is empty. Then it calls `plan` and runs
the effects in order. An `Answer` keeps the other program's output as it was
printed, so reading that output is the planner's decision, not the
interpreter's. A law ties the two halves together: when `wants(w)` is empty,
`plan(w)` asks nothing. The interpreter's faithfulness is one Trusted row
(EZ-TRUST-2), so keep it small enough to review line by line.

A new command or flag is written in this form from the start. A change to a
command that hasn't been converted yet either converts the part it touches,
or puts its new decision in a pure helper that the eventual planner can call.

## Rows the known bugs became

The audit's IO bugs were each turned into a decided requirement. Read these
rows before writing a similar one, and extend them rather than adding a
near-duplicate:

- **EZ-LED-6**: `init` and `remove` refuse and write nothing, where they
  used to overwrite or guess.
- **EZ-LED-7**: how `ez add` names a dependency. This is a stated naming
  order plus `--rename`, not plain "different sources get different
  names".
- **EZ-LED-8**: a relative path target is kept in the ledger as typed.
- **EZ-OUT-2**: a refused command writes nothing. This is the frame law
  every command gets. A command whose plan can be `Refused` needs the law
  "a refused plan has no `Write`, `Lay` or `Drop` effect". When you add an
  Effect constructor that writes, add it to that law.

Some accidental behavior was fixed without becoming a row: `.ez` and `bin`
being created in the current directory, and `ez doctor` failing a project
with no deps. Those have untagged quantified laws and a note in
`docs/rfc/ez-law-inventory.md`. Treat similar incidental fixes the same way
(SKILL.md step 1).

## Where ez's trust lives

The Trusted rows point at other programs: git (EZ-RES-7), nix (EZ-HASH-5),
`bend --publish` (EZ-HASH-4), the hub (EZ-TRUST-3), and the proofs of pinned
dependencies (EZ-TRUST-5, EZ-HASH-6). A feature that leans on a new external
answer needs a new Trusted row. Where you can, design it so ez checks the
answer instead. The hub is trusted only for availability, because ez checks
every body against its hash (EZ-FETCH-1).

Compare before acting, not after. The one known exception is EZ-PUB-2:
`bend --publish` can't report the hash without uploading, so `ez publish`
can only compare bend's answer with its own hash after the upload has
happened. Don't copy that shape into a new command. If a new feature also
has to act before it can check, say so in its row.

Be wary of reimplementing git or NAR plumbing. Each reimplementation is
another place where ez can diverge from the real tool.

## End-to-end guarantees

Once commands are planners, laws that span commands become possible. They
are the most valuable kind of law: "`ez add` then `ez lock` on a fresh clone
reproduces the lock `ez add` wrote", or "`ez lock --check` fails exactly when
`ez lock` would change the lock". When a feature makes one of these statable,
add the row.

## Gate

- `ez prove` is the proof gate.
- `nix flake check` is CI's `check` job. It includes mkProofs, mkLint with
  the pinned bolt, and `fresh` (mkFresh): a fresh clone rebuilt from the
  lock, which is the real end-to-end test of EZ-DOC-3.
- Without nix, CI's `readme` job follows the README's install: bend at the
  pinned release, `sh bootstrap.sh`,
  `BEND_LIB=$PWD/.ez/lib bend ez/main.bend -o bin/ez.bin`, then
  `bin/ez.bin prove`. Run this too when a change touches bootstrap, the
  build, or the lock.
- bolt: ez pins v0.9.0 (`[tools.bolt]` in ez.toml), where binderless laws
  are `quantify` (L004), not `closed`, and there is no `trace` yet. It stays
  on that pin until the last `# toward` trail is gone.

Never run `ez publish` or `bend --publish`. An upload is public and can't be
undone.

## Migration leftovers

`# toward EZ-X-N` trails are closed laws kept during consolidation. Don't
add new ones. If your change lands a quantified law for a row that has a
trail, delete the trail in the same change.
