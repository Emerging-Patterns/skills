---
name: find-users
description: Find who outside Emerging-Patterns uses its Bend packages (bolt, ez, shake, snap, ezjson, eztoml, ezhttp, ezimg, ezaudio, or any org's Bend packages) on GitHub, and tell real dependents apart from mentions and package listings. Use it whenever someone asks who uses bolt or ez, for dependents, adopters, downstream users, "search GitHub for users of X", who would break if a package changes, or whom to tell about a release, even if they don't say "users".
---

# Find users

The goal is a short, honest list: which repos outside the org actually
**depend on** a package, which only **mention** it, and which are
**listings** (awesome-lists, package indexes). Report what was searched and
what can't be seen, not just the hits.

## Why code search alone undercounts

GitHub's code index is incomplete for young and small repos, which is most of
the Bend ecosystem. Bend packages are also imported by hub hash
(`import 0x…/main.bend`), not by name, so a user may never write
`Emerging-Patterns` anywhere. So the search has three passes:

1. **Code search** for `<org>/<pkg>` (unquoted) per package, every hub hash (current
   ones from `ez.toml`/`ez.lock.toml`/READMEs, plus old ones), and marker
   phrases (`"bolt lsp"`, `"ez add"`, …).
2. **Collect every Bend repo** search can find: code seeds (`"import Base"
   extension:bend`, `"-> IO(Unit)" extension:bend`, the install URL, the hub
   URL) and repo search (`--language=bend`, recent `bend` repos).
3. **Read each candidate directly**: its file tree for `ez.toml`,
   `ez.lock.toml`, `bolt.bend` or `.ez/`, and its README for org links,
   package names and `ez`/`bolt` commands. The tree and README calls use the
   core API (5000/hour), not code search, so they reach repos the index missed.

## Run it

`scripts/find_users.py` does all three passes and prints a markdown report
(progress on stderr). It needs an authenticated `gh`.

```bash
python3 scripts/find_users.py --org Emerging-Patterns --clones ~/projects/bend \
  --hashes <old hub hashes> > report.md
```

- `--clones` harvests hub hashes from local clones' `ez.toml`,
  `ez.lock.toml` and READMEs. Without clones, pass them with `--hashes`.
- Old hashes are worth adding: awesome-lists and other people's READMEs lag
  behind releases, and 777genius/awesome-bend is a good place to find them.
- `--packages` narrows to a few packages; default is every repo in the org.
- `--skip-sweep` does pass 1 only (about 2 minutes). The full run takes
  about 5 to 10 minutes, mostly waiting out the code-search limit.

## Classify every hit by hand

The script collects evidence; deciding what it means is your job. Open the
file it cites before you put a repo in a category.

| Category | Evidence |
| :-- | :-- |
| **Depends** | Has `ez.toml`/`bolt.bend`; imports a package hash in `.bend` code; code or config that runs the tool (e.g. zed-bend's `src/lib.rs` finds the `bolt` binary for `bolt lsp`). |
| **Mentions** | Research notes, comparisons, "trial first" docs; no import or config. Say what version they looked at, since stale evaluations are worth answering. |
| **Listing** | Names 4+ packages (the script tags these `listing?`), e.g. 777genius/awesome-bend, 777genius/bend-packages. Check its hashes are current. |
| **Upstream** | A repo the org depends on, found because its hash is in our `ez.toml` (e.g. Giulio2002/bend-sha256). Not a user. |
| **Noise** | Marker phrases hit unrelated code (`ez lock` apps, "lightning bolt" in a README). Drop it. |

Also check forks and stargazers of each package
(`gh api repos/<org>/<pkg>/forks`, `…/stargazers`); they are cheap and
occasionally find a user with no public code yet.

## Report

Lead with the answer (who really depends, and how), then a table of repos
with category and one line of evidence each, then what was searched, then the
limits:

- private repos are invisible;
- someone who runs `bolt` in an editor or CI with no `bolt.bend` and no
  README mention leaves no trace;
- the candidate set is only as good as the seed searches, so a Bend repo that
  uses none of the common phrases can be missed.

Flag stale hashes in listings and READMEs as a follow-up (a PR to the
listing), since they send new users to old versions.

## Gotchas when running by hand

- Code search allows **10 requests a minute** (separate from the 5000/hour
  core limit). Sleep about 7 s between queries; on a 403 read
  `gh api rate_limit --jq .resources.code_search.reset` and wait for it.
- `gh` inside `while read r; do … done < list` eats the rest of the list
  from stdin, so the loop quietly runs once. Give it `</dev/null`.
- Search `Emerging-Patterns/bolt` **unquoted**. The quoted form fails to
  match across the slash and silently misses repos (bend-voxel's research
  doc, for one).
- Bare marker phrases are noisy: `"bolt check"` hits structural-engineering
  code and card games. Add `bend` to them, and treat marker-only hits as
  noise until you've opened the file.
- `filename:ez.toml` is fuzzy and matches `Wetez.toml`, `testez.toml`; use
  the tree scan instead.
- `language:bend` isn't a code-search qualifier GitHub parses reliably; use
  `extension:bend`.
- On some machines `grep` is aliased to `ugrep`, which rejects long
  `.{0,60}` context patterns; use `/usr/bin/grep` or Python.
