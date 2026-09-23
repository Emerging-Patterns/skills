# Debugging along the way

The audits of ez and bolt found their real bugs by running the real
binary, not by reading tests or laws. This file has the recipes that did
it, and the catalog of what was found, so you know what kind of bug to
look for.

## Contents

- The fresh-clone recipe
- Master's binary against the branch's
- Checking a claim, not just an outcome
- Root-causing a disagreement with another tool
- The catalog
- Turning a manual check into CI

## The fresh-clone recipe

A working checkout hides bugs: untracked files, a filled cache, a `bin/`
directory someone made by hand, environment variables set in your shell.
Start from exactly what a clone has:

```sh
scratch=$(mktemp -d)                      # or a path in your scratchpad
git -C "$repo" archive HEAD | tar -x -C "$scratch"
cd "$scratch"
git init -q && git add -A                 # a repo, with only tracked files
# fill dependencies the documented way (for ez: sh bootstrap.sh), or copy a
# known-good BEND_LIB to check offline
# build exactly as the README says
rm ez.lock.toml && bin/ez.bin lock        # regenerate the committed artifact
cmp "$repo/ez.lock.toml" ez.lock.toml     # the headline guarantee, directly
```

Adapt the last two lines to the project's headline guarantee. Run it for
every PR that touches the build, the bootstrap, dependencies or the
guaranteed artifact, and say in the PR that the fresh clone was
byte-identical. Variations that found bugs in ez: an empty BEND_LIB (every
tree cloned), a filled one (nothing fetched), the hub blocked, and the
clone moved to another path.

## Master's binary against the branch's

For every behavior change, build master's binary and the branch's, run the
same cases with each in scratch directories, and record both results in
the PR, usually as a table of case and result. This catches a change that
does more than it says, and it is the evidence a reviewer uses to confirm
the change is the one the RFC decided. Give each binary its own scratch
directories and build output path, so one run cannot read the other's
state.

## Checking a claim, not just an outcome

A command exiting 0 is not evidence for what it claims. Check the claim
itself:

- "ez lock reads nothing from the network": run it under
  `strace -f -e trace=connect` and see no `connect` calls;
- "bootstrap changes nothing when every package is present": run it, then
  `diff -r` the library against the copy you started with, and require
  empty stderr;
- "a refused command writes nothing": list the directory, including
  mtimes, before and after;
- "the proof checks something": replace it with `{==}` and watch the gate
  fail.

## Root-causing a disagreement with another tool

When the project and a tool it must agree with disagree (a hash, a path,
a format), do not decide which is right from comments or docs.

1. Reproduce the disagreement on the smallest input (one file with one
   non-ASCII character).
2. Read the other tool's source at the version you pin. bend ships its JS
   inside the binary; `strings $(command -v bend) | grep -n 'createHash'`
   and similar searches find the code that computes a hash or parses a
   flag.
3. Confirm with the tool itself, against a local stand-in, never the real
   service: ez's `tests/publish.bend` runs `bend --publish` against a local
   oracle hub (`check/serve.bend`) and compares its hash with ez's. A
   public upload cannot be undone (see orchestration.md).
4. Record the evidence in the RFC's REVIEW item and in the PR.

Also use the tool's source to check a design is possible before designing
it. `bend --publish` accepts no option that stops between hashing and
uploading, so "compare before upload" could not be built; the RFC says
so, and the requirement promises only what can be kept.

## The catalog

What the audits found, how, and what it became. Use it as a checklist of
where bugs hide.

| Found | How | Became |
| :---- | :---- | :---- |
| ez's sha256 folded each char to its low byte, so non-ASCII files got a 0x name bend never publishes, and one dependency's ledger name was never valid on the hub | a publish of a non-ASCII file; bend's source read out of its binary | fix (#58), EZ-HASH-6 reworded to "UTF-8 bytes", a publish test with 2, 3 and 4 byte chars |
| `ez lock` on a fresh clone wrote empty `files` tables and exited 0 | fresh clone, relock, `git diff` | decided input changes (#55), then EZ-DOC-3 proved (#68) |
| the lock read `.ez/origins.toml`, untracked files, `BEND_HUB`, `bend version` | tracing every read to its source line | the World's fields; each extra read a decided change |
| the README build failed on a clean clone because `bin/` did not exist | following the README literally | `mkdir -p bin` in the README, then a CI job that follows it |
| `ez add` named two dependencies whose entry is `main.bend` both `main` | adding two real packages | EZ-LED-7, naming like cargo with `--rename` |
| `ez add ../x` fetched from inside a work directory | a relative path from a subdirectory | EZ-LED-8, resolved against the project root |
| `ez init` overwrote an existing ledger; `ez remove` with no ledger created one | running each command twice and in an empty directory | EZ-LED-6, refusals that write nothing |
| every command, `ez help` included, created `.ez` and `bin` | `ls` after `ez help` in an empty directory | untagged fix, noted in the inventory |
| `ez doctor` failed a project with no dependencies | running it on `ez init`'s output | untagged fix |
| an upgrade decision function was always called with its agreement bit fixed to true, so its drift arm was dead | reading the call sites while tracing | the planner calls it with the real bit (EZ-RES-8) |
| walks stopped silently when fuel ran out | reading the walks while tracing | the planner refuses instead |
| a committed ledger would have held an absolute path | reviewing an agent's diff | sent back before push |
| bolt's `bolt check` said `clean`, exit 0, with no bend on PATH | running it with no bend available | decided change: a spawn failure is an error |
| bolt's `shadow` rule guarded against a failure bend 2.0.25 no longer has | trying the pattern in the pinned bend | the rule retired, its code reserved |
| bolt's rules each had a false positive or negative against their header | a scratch project per rule | per-rule fixes, each proving the rule's row |
| bolt's `main` had no branch protection, so the gate bound nothing | the GitHub API | a Trusted row that holds once a maintainer adds the ruleset |

## Turning a manual check into CI

A bug that only a manual check caught will come back unless CI runs that
check. ez added two after the hash and README bugs (#61):

- `fresh`, an offline nix check (`mkFresh` in `nix/lib.nix`): copy the
  tracked files into a new git repo, copy the lock's BEND_LIB in, run
  `bootstrap.sh` and require that it fetches and changes nothing, build the
  README's way, delete the lock, relock, and `cmp`. It is the direct check
  of EZ-DOC-3, covering the trusted interpreter too.
- `readme`, a job with no nix: install the pinned bend release by URL and
  checksum (not an install script that picks the newest version), run the
  README's steps verbatim, then the proof gate.

After a new check's first CI run, open the job log and confirm each step
ran. A check that is skipped or short-circuits looks green.
