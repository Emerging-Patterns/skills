---
name: find-packages
description: Search the Bend hub (hub.bend-lang.com) and JendHub (jend.leeeet.dev, a search engine over the definitions of Base and every hub package) for a package or definition that already does something, before writing it or proposing a new library or library feature. Searches names, descriptions, file names, JendHub's ranked definition index and, with --content, the def/type lines inside every named package, and says what was searched. Use it whenever a Bend task needs functionality that might already exist (base64, regex, JSON, HTTP, time zones, CRC, a protocol), before "let's add X to ezhttp/ezsys", before creating a new ez* library, when porting a service to Bend, or when someone asks "is there a Bend package for X", even if they don't mention the hub.
---

# Find packages

Search the hub **before** building, and put what you found in the proposal:
"bend-kit-regex does this (RE2, Pike VM, 0 dependents, paymog)" or "nothing
on the hub names, describes, ships a file for, or defines `iso_week`". A
library proposal that skipped this step is incomplete.

## Why a quick look misses things

We built `ezsys` and parts of `ezhttp` while paymog's `bend-kit-*` family
(about 59 packages: http, wire, json, url, time, files, process, regex,
lemmas…) was already on the hub. The search that missed it only grepped
package **names**. Three things make the hub easy to under-search:

- `search.json?q=` matches names, descriptions and **file names** only, never
  file contents, and returns at most 50 packages.
- Many packages have an **empty description**, and many versions are
  **unnamed** (published by hash only). `bend-encoding` has no description;
  you find its base64 by its file `base64.bend`.
- The function you need is often a few defs inside a bigger package
  (`gralha-bytes` does base64 and percent-decoding among other things), so
  only a content search finds it.

[JendHub](https://jend.leeeet.dev/) closes most of that gap: it indexes every
definition (function, type, law) of Base and of the latest valid release of
each hub package, and ranks them against task words ("base64 encode"), names
(`List.map`) or types (`List<A> -> List<B>`), preferring well-used code. The
script runs it as a pass for every term. It always returns its best guesses,
even for nonsense, so a JendHub hit counts only when its signature fits; and
it skips releases that fail to load, so the hub crawl and `--content` still
matter.

## Run it

```bash
python3 scripts/find_packages.py base64 "percent decod"     # names, descs, files
python3 scripts/find_packages.py --content iso_week strftime  # also inside .bend files
python3 scripts/find_packages.py --json regex > hits.json
python3 scripts/find_packages.py --no-jendhub crc32         # hub passes only
```

- Pass **several terms per need**, and for JendHub a short task phrase too
  (`"sha256 hash of bytes"`), since it matches words against code and docs: the concept, its RFC or standard name, the
  likely file name and likely def names (`base64`, `b64`, `RFC 4648`;
  `regex`, `re2`, `pike`; `time`, `rfc3339`, `tzif`).
- `--content` downloads the `.bend` files of the newest version of every
  named package and greps `def`/`type` lines and comments. The first run
  takes a few minutes; files are content-addressed, so they are cached under
  `~/.cache/bend-hub/` and later runs are quick.
- Output is ranked named-and-depended-on first, and says how each package
  matched (`hub-search`, `name`, `desc`, `file`, `content`) and which passes
  ran (`jendhub` hits list the matching signature and its `definition`
  URL, which opens the code with its exact import lines). Owners come from `names.json`, which only ever lists 100 names, so
  some owners show as `?`.

The hub API, if you need to go further by hand:

| Endpoint | What it gives |
| :-- | :-- |
| `/search.json?q=TERM` | `{names, packages}`: name/desc/file-name matches, max 50 |
| `/packages.json?sort=new&limit=100&after=N` | every version: name, version, hash, desc, files, dependents, ts |
| `/names.json?limit=100&sort=score\|new\|hot` | named packages with owner and latest version (capped at 100, no paging) |
| `/stats.json` | counts of packages, names, authors |
| `/<0xhash>/<file>` | a file of a package version (immutable) |

JendHub, on `https://jend.leeeet.dev` (plain-text answers; full docs in
[`/llms.txt`](https://jend.leeeet.dev/llms.txt); also an MCP server at
`/mcp`). A path is `name@version/file.bend`; Base is `Base/base.bend`.

| Endpoint | What it gives |
| :-- | :-- |
| `/search.txt?query=&package=&uses=&used_by=&limit=` | ranked definitions, each with import line, head and `definition` URL |
| `/definition.txt?path=&name=` | one definition's code, its import lines, and what it uses |
| `/read.txt?path=&start_line=&end_line=` | lines of a file, any release |
| `/grep.txt?pattern=&path=` | ripgrep over one release |
| `/files.txt?path=` | files of one release |

`uses=`/`used_by=` (`package/module:name`, or a Base name) find callers and
callees, handy for checking whether a hit is actually used.

## Judge each hit

A hit is a lead, not a decision. Before recommending a package, open it:

1. **Read the entry file's exports** (the `def`s at top level of its entry,
   e.g. `regex.bend`) and check it does what the task needs, on the types
   you have (String vs `List<U32>` bytes vs a packed `Bytes`).
2. **Check how it's proven.** Does it ship laws (`LAWS.bend`/`PROOF.bend`,
   a SPEC with rows), or only examples? How much is foreign code
   (`effs/*.c`, `*.js`)? A proven-by-us library can't lean on unproven code
   without a trust row.
3. **Check it's alive and usable:** newest version and date, dependents,
   license, its Bend version, and whether it builds offline from a pinned
   hash under ez's `mkPackage` (no network in the build).
4. **Note the import cost:** its own dependencies (they come along by hash),
   and whether a second copy of something you already pin would end up in
   the lock (ez can't unify transitive deps yet, Emerging-Patterns/ez#150).

Then recommend one of: **use it** (import directly), **wrap it** (our
library re-exports or adapts it and keeps our laws), or **build it** (and say
why the hits don't fit: wrong types, not byte-safe, unproven, unmaintained).

## Report

Say which terms and passes you ran, list the plausible hits with the
evidence (package@version, hash, owner, dependents, the matching def), and
give the recommendation. "No match" is a result too: name the terms and
passes so a reader can tell it from "didn't look".
