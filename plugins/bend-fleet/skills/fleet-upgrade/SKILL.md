---
name: fleet-upgrade
description: Upgrade Bend packages that depend on each other through ez (ez, bolt, shake, snap, ezjson, eztoml, ezhttp, ezimg, ezaudio, or any ez-managed Bend repos) to their latest releases, and publish them to the Bend hub, by hash and under their hub names. Two modes, one package (bump its deps, release it, publish it, fix its README, tell its dependents) or the whole fleet (every repo, leaves first, then flake ez pins and [tools.bolt] everywhere, READMEs verified as a plain Bend user). Use it whenever someone asks to bump, upgrade, re-pin, release, or publish Bend packages, update ez pins or flake inputs across repos, get "latest versions of everything", fix README hashes or hub imports, publish under a hub name (name@version), move the fleet to a new bend release, or asks why a hub import 404s or `ez publish` says the package walks drifted, even if they never say "fleet".
---

# Fleet upgrade

A fleet is a set of Bend repos that pin each other. The goal of a run:

1. every package imports the **latest release** of each dependency, by the
   hash that release has on the hub;
2. every release is **published to the hub**, by hash, and under its hub
   name as `<name>@X.Y.Z.0` where the project has one (step 3.6);
3. every hub package carries its **LICENSE** and a **one-line description**;
4. every README leads with the named import (`import <name>@<ver>/main.bend`)
   the hub serves, and every snippet checks for a **plain Bend user** (only
   `bend`, no ez);
5. dev tooling (flake `ez` input, `[tools.bolt]`) points at the latest ez and
   bolt.

Content and tooling are separate on purpose. A package's hub hash is the
walk from its entry: the imported `.bend` and effect files, plus a LICENSE
from each directory that holds a walked file. `flake.lock`, `ez.toml` tools, READMEs, and files the entry doesn't
reach are not part of it. So "latest" is judged by content: a leaf whose
default branch only moved its `flake.lock` is still at its latest release.
This also breaks the cycle you'd otherwise hit, where ez pins shake by rev
while shake's flake pins ez. Package edges go leaves-first, and tooling is
updated in one final pass.

## Tools in this skill

- `scripts/fleet_graph.py DIR` maps every clone in DIR. It shows each dep's
  tag and hash, whether the hub serves that hash, which deps are stale
  against the latest release, tools and flake pins, unreleased commits, any
  `publish-as` set, and the **release order**. Run it first and again at the
  end.
- `scripts/publish_hash.sh REPO [TAG] [NAME]` shallow-clones the tag and
  publishes it with `$BEND` (the bend the fleet targets), as `NAME@X.Y.Z.0`
  when a hub name is given. It refuses, before any upload, a `[package]` that
  sets `publish-as`/`version`, an entry under `manifest/`, and an entry with
  no LICENSE beside it. It prints the entry's first line (the description)
  and `repo tag 0x… hub=200 named=…`. `EZ=` is only used to fetch locked deps.
- `scripts/readme_hub_check.sh README.md [HASH]` checks each `import 0x…`
  against the hub, then runs every snippet that imports one with
  `bend --check-only`, in an empty HOME with only `bend` on PATH.
  Imports may be by hash or by `<name>@<ver>` (resolved at the hub's
  `/name/<name>@<ver>`). A snippet passes on `ALL PROOFS CHECK`, or on a
  `SOME PROOFS FAIL` whose only error is that defs rely on unsafe or foreign
  code, which since bend 2.0.32 is the verdict on any program that reaches
  an effect.

## 0. Prepare

- Refresh every clone to its default branch (`git fetch --prune --tags`,
  `checkout`, `reset --hard origin/<branch>`). Old local branches and stray
  files are not the state you are upgrading. Ask before discarding someone's
  uncommitted work; move stray files aside rather than deleting them.
- Build the **current ez** (`nix build github:Emerging-Patterns/ez`) and use
  it with the Bend version ez's README names (`bend version`). Every hash in
  this run must come from that pair. An older ez or bend walks packages
  differently (Bend 2.0.27 added LICENSE to the walk), and then the hash ez
  computes disagrees with the one bend uploads.
- Pin bend deliberately. Update only the inputs you mean to: `nix flake
  update ez`, not `nix flake update`, which also moves `bend`. A bend release
  can land in the middle of a run, as 2.0.28 did, with new name rules, a Base
  `Set`, and a new JS effect registration. Moving to a new bend is its own
  pass across the whole fleet, with its own releases. When one ships, test
  what a new user gets. Install it with the official `install.sh` into an
  empty HOME, and run the README checks with that `bend` first on PATH. The
  `vX.Y.Z` tag of bend's flake can still package the previous release
  archive, so it is not a reliable way to get the new bend.
- A new bend can break the tools before the packages. On 2.0.28 neither ez
  1.2.0 nor bolt 1.8.0 built, and every package's CI builds both, while ez and
  bolt import the very packages waiting on that CI. Break the loop in each
  package flake: the `ez` input stops following `bend` and pins
  `inputs.bend.url` to the rev ez's own `flake.lock` records (without a rev,
  nix resolves bend's latest and nothing changes), and `packages.bolt` drops
  `inherit bend`. ez, `ez prove` and `mkLint`'s bolt then run on the old
  bend, and the package's own builds on the new one. Say in the PR that the
  proofs were also run on the new bend by hand, since CI no longer does it.
  The CI then goes green without admin merges, and the tools move to the new
  bend when their own releases do.
- **Read every release note between the fleet's bend and the target**, and
  expect breaks the notes don't call breaking. From 2.0.28 to 2.0.34:
  `IO.args()` starts with the program name (arguments at index 1) and a
  compiled binary passes `--help` through; `TCP.listen`/`UDP.bind` take a
  host; `bend` prints `ALL PROOFS CHECK` / `SOME PROOFS FAIL` (exit 1) and a
  proof whose imports reach `@unsafe` **or user foreign code** (C/JS
  effects, hub imports included) fails; Base lost helpers such as
  `String.eq.fin` and `Nat.mod.fin`, and some Array/U32 helpers changed
  shape. Survey first: fetch each repo's deps and run its entry and every
  PROOF.bend on the new bend (`references/porting.md`). A proof that fails
  only because it imports an effect is fixed by moving the effect into a
  sibling module no law file imports, not by exempting it.
- **When ez's own gate can't read the new bend**, the interim package flake
  runs the proofs itself: bend at the new rev, the `ez` input pinned to ez's
  own bend rev instead of following, and `checks.proofs` a `runCommand`
  that runs bend on every PROOF.bend with
  `BEND_LIB = ez.bendLib ./ez.lock.toml` and requires the first line
  `ALL PROOFS CHECK` (`references/flake.md`). ez.mkProofs comes back in the
  tooling pass, once ez releases on the new bend.
- Check branch protection is uniform. Each package repo should carry the same
  ruleset: PR required, `check / check` required, no force-push or deletion,
  squash only, auto-merge on, delete branch on merge. Fix drift with
  `gh api repos/<org>/<repo>/rulesets`. See `references/github.md`.
- **Hub names.** Keep `publish-as`/`version` out of `ez.toml`: release-please
  would have to bump `version`, and the name is a publishing decision, not
  package content. Name each release when publishing instead (step 3.6).
  bend accepts any `[a-z][a-z0-9-]{0,63}`, and the hub decides: 12 to 64
  characters register free on first publish, 3 to 11 are auctioned (Bender
  credits, bid at `hub.bend-lang.com/n/<name>`), shorter ones are refused.
  The Emerging-Patterns fleet owns `bolt`, `snap`, `shake` and `ezx` (ez's
  library; `ez` is too short); the rest publish as `emerging-<repo>`.
  Before publishing, ask the hub, read-only, with the `bend login` key
  (`~/.bend/bender.json`) as a bearer token:
  `GET https://hub.bend-lang.com/publish-check?name=N&version=X.Y.Z.0` must
  answer `"name":"yours"` or `"free"` and `"version_ok":true`. A version only
  goes up, so name the newest release, not old ones after it.
- **Layout, LICENSE and description** (checked before any publish, which is
  permanent). The hub shows the first line of the first walked file by path
  (LICENSE aside) as the description, and bend adds a LICENSE only from a
  directory that holds a walked file. ez init's layout gets both right:
  `main.bend` at the package root, opening with `# <name>: <one sentence>`,
  the LICENSE beside it, and every other module under `src/` (so nothing but
  LICENSE sorts before `main.bend`). A flat layout (`b64.bend` before
  `main.bend`) shows the wrong module's header; an entry in a subdirectory
  (`ezaudio/main.bend`, `ledger/manifest.bend`) walks no LICENSE and is
  published as MIT-0, the hub terms' default, for good. Move such a package
  to ez init's layout (`feat!`: module paths change) before its next publish.
  The hub's `GET /packages.json` lists `desc` and `license.id` per package.

## 1. What "latest" means

The newest **GitHub release tag**, not the default branch head. If a repo has
feat/fix commits since its last tag, release it first. Merge its open
release-please PR (step 3), then use the new tag. Other sessions may be
merging while you run. Take each release as it stands when you merge it, and
note what landed after.

## 2. Order

Release in `fleet_graph.py` order: a package only after every package its
`[deps]` name is released and published. Tools and flake inputs are not edges.
bolt, for example, needs shake, ezjson and snap, not ez, so it releases
before ez and ez's `[tools.bolt]` can then point at the new bolt.

## 3. Release one package

For each package in order:

1. **Bump deps** on a branch:
   `BEND_LIB=$PWD/.ez/lib $EZ add <git-url> <tag> <entry>` per dependency.
   Check that the printed `import 0x…` hash is the one you published for that
   tag. Then rewrite **every** `import 0x<old>/<path>` in tracked `.bend`
   files (LAWS, PROOF, bench and tests too, not only the entry's walk) to the
   new hash **and the new path**. Layouts move between releases, e.g.
   `value.bend` became `src/value.bend`. Then run `$EZ lock`. `ez lock`
   refuses an import of a hash that ez.toml doesn't name and the hub doesn't
   serve, which is how you find the stragglers.
2. **Breaking changes**: read the dependency's CHANGELOG. Port the dependent to
   the dependency's **public interface** only (its `main.bend`). A dependent
   must not import or prove a dependency's internals (`src/…`). It takes what
   the dependency proves as trusted: cite the dependency's SPEC row IDs in the
   dependent's SPEC.md trust section, and state the dependent's laws over its
   own code. If a dependent needs a property the dependency doesn't prove, the
   fix is a new proved row upstream, not a private proof downstream. Large
   ports suit one subagent per repo (see `references/porting.md`).
   Read the changelog for **semantic** changes too, not just the ones that
   stop compilation. snap 1.0.0 began returning stdout and stderr
   interleaved in the order they were written. Nothing failed to check, but
   every caller that parsed combined output by position had to be audited.
   If the dependent's own users will see a change, say so in a
   `BREAKING CHANGE:` footer so it lands in the release notes.
   A row the dependency still lists as pending is weaker than a proved one.
   Adopting that release means the dependent's laws rest on an unproved row.
   That's the maintainer's call. Record the row as trusted-but-pending in the
   trust section, so the weakness stays visible.
3. **Gate** with the current ez and bend: `bend <entry> --check-only`, every
   `PROOF.bend` prints `ALL PROOFS CHECK` (`$EZ prove`), `$EZ test`, and `nix flake check` if
   you can. LAWS files listing TODOs are normal (the proof discharges them).
4. **Commit** with a conventional type release-please will release: `fix(deps):`
   or `feat(deps):`, or `!` for a breaking change. Repos here use
   `versioning: always-bump-minor`, so breaking changes bump the minor, never
   the major. Push, open a PR, and `gh pr merge --squash --auto`.
5. **Release**: release-please opens `chore(<branch>): release X.Y.Z` as
   `github-actions`. CI does **not** run on PRs a bot token opens, so the
   required check never reports. Close and reopen the PR as yourself
   (`gh pr close N && gh pr reopen N`), enable auto-merge, and wait for the tag
   and GitHub release.
   If release-please rewrites the PR after you reopen it (another merge
   landed), the check again never reports: reopen it once more.
   **No release PR at all** after a `fix:` merge means release-please could
   not parse the squash commit: its log says `commit could not be parsed`.
   A body line such as `io_eff(CID(Name), run, need)` reads as a footer. Add
   `BEGIN_COMMIT_OVERRIDE` / `fix: …` / `END_COMMIT_OVERRIDE` to the merged
   PR's body and re-run the release-please workflow run.
6. **Publish** the tag. Normally nothing to do: each repo's
   `release-please.yml` has a `publish` job (shared `publish.yml`) that runs
   when release-please cuts a release and publishes the tag as
   `<hub-name>@X.Y.Z.0` with the `BEND_HUB_KEY` repo secret. It builds ez from
   the repo's flake, runs `ez prove`, refuses a missing LICENSE, a
   `manifest/` entry or a name the hub won't take, then uploads and checks the
   name resolves. Check the run; if it failed, fix the cause and retry with the
   repo's `publish.yml` (workflow_dispatch: `tag`, `dry-run`). Run it with
   `dry-run` first when anything about the flow changed. See
   `references/github.md`.
   The job reads the workflow at the release commit: a pin or caller fix must
   land **before** the release PR merges, or that release publishes with the
   old one (ez 1.4.0 did; its retry went through `publish.yml`).
   A tag cut before the repo's tooling moved to the target bend can't be
   published by CI (its flake builds the old ez); publish such a tag locally
   with `BEND=<bend> scripts/publish_hash.sh <repo> <tag> <hub-name>`.
   Publishing is public and permanent, but content-addressed, so re-publishing
   the same tag returns the same hash. A hub name's version only goes up, so
   when a tag has a defect (old description, missing LICENSE) skip it and
   publish the next release rather than naming a bad one.
   **`manifest` is reserved at a package's root.** The hub serves each
   package's own manifest at `<hash>/manifest`, and it refuses a package
   with a top-level `manifest/` directory. Rename the directory.
   **Only a real release goes to the real hub.** Every other `--publish`
   (a repro, an experiment, a script under test) runs with `BEND_HUB` set to
   a local stand-in, and you check it is set before running it: bend uploads
   to `https://hub.bend-lang.com` whenever `BEND_HUB` is unset, and a test
   upload there is public and permanent (an agent's 2026-09-25 `manifest/`
   repro is still on the hub as `0xb3a098ff…`). The stand-in is ez's
   `src/check/oracle.bend`, which accepts an upload, computes the package
   hash the way bend does, and serves the files back:

   ```bash
   mkdir -p "$TMP/hub"
   bend <ez>/src/check/oracle.bend "$TMP/hub" 8765 &   # GET / answers ok once it is up
   until curl -fs http://127.0.0.1:8765/ >/dev/null; do sleep 1; done
   BEND_HUB=http://127.0.0.1:8765 bend main.bend --publish
   ```

   It takes uploads by hash only. For name questions use the real hub's
   read-only `GET /publish-check` (step 0), never a trial named publish.
   ez's own tests already run this way (`tests/publish.bend`,
   `tests/publishing.bend`). A refused upload (a check that fails before any
   bytes are sent) is also safe to reproduce against the real hub.
7. A hash that did not change is fine when the entry's walk didn't change,
   e.g. ezhttp's `json.bend` is only reached from LAWS, so bumping ezjson left
   ezhttp's hub package identical. Say so rather than assume a mistake.

A third-party dependency (e.g. Giulio2002/bend-sha256) is not yours to
publish. Pin the entry whose walk its author published, so the hash matches
the one in their README (`package.bend` → `0xda83…`), rather than a smaller
walk nobody put on the hub. When upstream lags a bend release, fork it, open
the fix upstream, pin the fork's rev, and publish the fork by hash only with
the maintainer's (your user's) say-so: a package whose walk reaches it
cannot be fetched by a plain bend user until it is on the hub. With no
LICENSE it goes up as MIT-0.

## 4. Tooling pass (after ez and bolt are released)

In every repo, one PR:

- `flake.nix` inputs are `nixpkgs`, `bend` and `ez` only, with
  `ez.inputs.{nixpkgs,bend}.follows`. **No `bolt` input.** bolt comes from the
  lock's `[tools.bolt]` through ez's nix lib: `ez.mkLint { src = self; … }`
  for the lint check, `ez.toolPackage { name = "bolt"; src = self; inherit bend; }`
  or `ez.devPackages self` for the package or shell. Removing the bolt input
  also removes the duplicate `ez_2` lock node.
- `[tools.bolt]` at bolt's new tag. ez has no `add --tool`. Write the table
  with `git`, `tag`, `root = "."` and `entry = "main.bend"`, then run
  `$EZ lock --upgrade --package bolt`, which fills in `rev` and `narHash`.
  bolt itself has no pin, because it lints itself with the bolt it builds.
- Drop `extraFlags` from `mkProofs`. Current ez's `ez test` takes no flags
  (`ez prove` is the proof gate), and the old `--unit-only` was silently
  ignored.
- `nix flake update ez bend`, then `nix flake check`, then PR with auto-merge.
  Use `chore:` or `build:`, since this doesn't change package content and
  needs no release. `references/flake.md` has the template.
- **A new bolt finds new lint.** Rules added since the old pin can fail a
  repo whose `bolt.bend` sets groups to `error`. Don't hold the upgrade
  hostage, and don't hide the debt. Set only the newly firing rules
  (`def closed() -> String: "warn"`, a per-slug level, narrower than the
  group) to warn, with a comment. Open one issue per repo with counts by rule
  and file, and link it from the commit. The maintainer decides when the
  levels go back up.

## 5. READMEs (a plain Bend user)

For each package, in the tooling PR or a `docs:` PR (docs don't release, and
README isn't part of the hash):

- **Install** leads with plain Bend and the hub name:
  `import <name>@X.Y.Z.0/main.bend as X`, which bend resolves at the hub and
  fetches on first run. Name the version, and give the hash it resolves to
  once, for pinning by content. ez (`ez add <org>/<repo>`) comes second.
- State the bend the package needs (2.0.32+ for anything reading argv or
  the new verdict) and the one it is built and checked on.
- A **tool** whose entry is its program (bolt; ez as `ezx` since 1.4.0) is
  built from the hub with nothing but bend: a file holding
  `import <name>@<ver>/main.bend as T` and `def main() -> IO(Unit): T.main()`,
  then `bend t.bend -o <tool>`. Lead with that, then the clone/nix build.
- Every import names the current release with paths valid at that tag. A
  snippet that names a type imports the module that defines it
  (`…/src/value.bend` for ezjson's `Json`).
- Run `scripts/readme_hub_check.sh README.md <hash>` until it exits 0. Note
  a fetch from the hub can time out: retry before debugging.

## 6. Finish

Re-run `fleet_graph.py`. Every dep is at the latest tag with `hub=ok`, no
`publish-as` anywhere, and flake pins are current. Report one table: repo,
release, hash, hub, README check, flake ez rev. Also list what you could not
finish and anything upstream you found (missing proved rows, packages whose
entry doesn't reach a module the README advertises).

## One package

Do step 0 for that repo, then step 3 for it alone. If its own deps are stale,
release them first, recursively, in graph order. Then steps 5 and 4 for it.
Finally list its **dependents** (`fleet_graph.py` shows who pins it) and
either bump them too or report them as stale. A release nobody pins is only
half an upgrade.
