---
name: fleet-upgrade
description: Upgrade Bend packages that depend on each other through ez (ez, bolt, shake, snap, ezjson, eztoml, ezhttp, ezimg, ezaudio, or any ez-managed Bend repos) to their latest releases, and publish them to the Bend hub by hash. Two modes, one package (bump its deps, release it, publish it, fix its README, tell its dependents) or the whole fleet (every repo, leaves first, then flake ez pins and [tools.bolt] everywhere, READMEs verified as a plain Bend user). Use it whenever someone asks to bump, upgrade, re-pin, release, or publish Bend packages, update ez pins or flake inputs across repos, get "latest versions of everything", fix README hashes or hub imports, or asks why a hub import 404s or `ez publish` says the package walks drifted, even if they never say "fleet".
---

# Fleet upgrade

A fleet is a set of Bend repos that pin each other. The goal of a run:

1. every package imports the **latest release** of each dependency, by the
   hash that release has on the hub;
2. every release is **published to the hub by hash** (no named publishing);
3. every README's `import 0x…` lines name hashes the hub serves, and every
   snippet checks for a **plain Bend user** (only `bend`, no ez);
4. dev tooling (flake `ez` input, `[tools.bolt]`) points at the latest ez and
   bolt.

Content and tooling are separate on purpose. A package's hub hash is the
walk from its entry (the imported `.bend` files, plus LICENSE under Bend
2.0.27). `flake.lock`, `ez.toml` tools, READMEs, and files the entry doesn't
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
- `scripts/publish_hash.sh REPO [TAG]` shallow-clones the tag and refuses if
  `[package]` sets `publish-as` or `version`. Otherwise it runs `ez publish`
  (hash only) and prints `repo tag 0x… hub=200`. Set `EZ=` to a current ez
  binary.
- `scripts/readme_hub_check.sh README.md [HASH]` checks each `import 0x…`
  against the hub, then runs every snippet that imports one with
  `bend --check-only`, in an empty HOME with only `bend` on PATH.

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
- Check branch protection is uniform. Each package repo should carry the same
  ruleset: PR required, `check / check` required, no force-push or deletion,
  squash only, auto-merge on, delete branch on merge. Fix drift with
  `gh api repos/<org>/<repo>/rulesets`. See `references/github.md`.
- Confirm no `ez.toml` sets `publish-as` or `version` under `[package]`. Those
  two fields switch `ez publish` to named publishing (`bend … --publish
  name@version`), which the hub gates. Without them ez runs a bare
  `bend <entry> --publish`, which is hash only.
  Names are still gated after bend 2.0.28: the hub registers 12 to 64
  characters, auctions 3 to 11 (Bender credits), and refuses shorter ones.
  Every fleet name is short, and `ez` can never be one. Ask the hub before
  planning a named publish: `GET $BEND_HUB/publish-check?name=N&version=V`
  with the `bend login` key as a bearer token is read-only.

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
   `PROOF.bend` says `All terms check`, `$EZ test`, and `nix flake check` if
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
6. **Publish** the tag: `EZ=<current ez> scripts/publish_hash.sh <repo> <tag>`.
   Record `repo tag hash`. ez's nix package wraps `ez` with the bend it was
   built with first on PATH, so `ez publish` runs that bend, not yours. The
   walk and the hash are the same, and ez refuses a disagreement, but check
   the published package with the new bend afterwards (step 5).
   Publishing is public and permanent, but
   content-addressed, so re-publishing the same tag is harmless and returns the
   same hash. The repos' own `publish` workflow (`workflow_dispatch`, input
   `tag`) is fine **only once that repo's flake pins a current ez and bend**.
   Until then it builds with the stale pins and fails with
   `ez computed 0x… and bend published 0x…`, and bend has already uploaded an
   orphan under the old walk.
   **`manifest` is reserved at a package's root.** The hub serves each
   package's own manifest at `<hash>/manifest`, and it refuses a package
   with a top-level `manifest/` directory (`EISDIR … /srv/hub/stage/…/manifest`).
   Rename the directory; ez's `manifest/` became `ledger/` in 1.2.0.
   Reproduce hub questions with the real package, or with a refused upload.
   Each successful test upload is permanent and public.
7. A hash that did not change is fine when the entry's walk didn't change,
   e.g. ezhttp's `json.bend` is only reached from LAWS, so bumping ezjson left
   ezhttp's hub package identical. Say so rather than assume a mistake.

A third-party dependency (e.g. Giulio2002/bend-sha256) is not yours to
publish. Pin the entry whose walk its author published, so the hash matches
the one in their README (`package.bend` → `0xda83…`), rather than a smaller
walk nobody put on the hub.

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

For each package, on a `docs:` PR (docs don't release, and README isn't part
of the hash):

- **Install** leads with plain Bend: no install step, just
  `import 0x<hash>/main.bend as X`, which bend fetches from the hub on first
  run. Name the version the hash is. ez (`ez add <org>/<repo>`) comes second.
- The hub package is the walk from `[package] entry`. For ez that is the
  ledger library, not the `ez` binary, so ez's README shows importing the
  library, and the tool is still built from a clone. bolt's entry is its
  program, so bolt can be built from the hub:
- A **tool** whose entry is its program can be built from the hub with nothing but bend: a
  file holding `import 0x<hash>/main.bend as T` and `def main() -> IO(Unit):
  T.main()`, then `bend t.bend -o t.bin`. Lead with that, then the clone
  build.
- Every `import 0x…` is the current release's hash with paths valid at that tag.
  A snippet that names a type imports the module that defines it
  (`0x…/src/value.bend` for ezjson's `Json`).
- Run `scripts/readme_hub_check.sh README.md <hash>` until it exits 0. Bend
  2.0.27 gotchas that break snippets: `match` can't scrutinize a computed
  value (give it its own def), and a type must be named through its defining
  module.

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
