#!/usr/bin/env python3
"""Search the Bend hub for packages that already do something, before building it.

The hub's own search (search.json) matches package names, descriptions and
file names only, returns at most 50 packages, and never looks inside files.
Many packages also have an empty description, or no name at all. So this runs
up to three passes per term and merges them:

  1. hub search:   search.json?q=<term>
  2. full crawl:   every version in packages.json, matched on name,
                   description and file paths (catches what the 50-cap drops)
  3. --content:    the .bend files of the latest version of every named
                   package (plus every pass-1/2 hit), grepped for the term in
                   `def`/`type` lines and comments

Hub files are content-addressed (a hash never changes), so downloads are
cached under ~/.cache/bend-hub/<hash>/ and later runs are fast.

  find_packages.py base64 "percent decod"            # passes 1 and 2
  find_packages.py --content iso_week strftime        # also grep inside files
  find_packages.py --json regex > hits.json
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HUB = "https://hub.bend-lang.com"
CACHE = Path.home() / ".cache" / "bend-hub"


def get(path, raw=False):
    with urllib.request.urlopen(HUB + path, timeout=60) as r:
        body = r.read()
    return body if raw else json.loads(body)


def crawl():
    """Every package version on the hub, newest first."""
    out, after = [], 0
    while True:
        page = get(f"/packages.json?sort=new&limit=100&after={after}")
        page = page if isinstance(page, list) else page.get("packages", [])
        out += page
        if len(page) < 100:
            return out
        after += 100


def owners():
    """name -> owner, for the names names.json will show. It caps every
    listing at 100 and has no paging, so a few sort orders are merged; a name
    outside them shows its owner as "?"."""
    res = {}
    for s in ("score", "new", "hot"):
        try:
            for n in get(f"/names.json?limit=100&sort={s}"):
                res[n["name"]] = n.get("owner_login") or "?"
        except Exception:
            pass
    return res


def file_text(h, f):
    p = CACHE / h / f
    if not p.exists():
        try:
            data = get(f"/{h}/{urllib.parse.quote(f)}", raw=True)
        except Exception:
            return ""
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return p.read_text(errors="replace")


def key(p):
    return p.get("name") or p["hash"]


def latest(pkgs):
    """The newest version of each name (unnamed packages stand alone)."""
    best = {}
    for p in pkgs:
        k = key(p)
        if k not in best or p.get("ts", 0) > best[k].get("ts", 0):
            best[k] = p
    return best


def grep_content(p, rx):
    """`file:line: text` for def/type lines and comments that match."""
    hits = []
    for f in sorted(p.get("files") or {}):
        if not f.endswith(".bend"):
            continue
        for i, line in enumerate(file_text(p["hash"], f).splitlines(), 1):
            s = line.strip()
            if (s.startswith(("def ", "type ", "#", "@unsafe def"))
                    and rx.search(s)):
                hits.append(f"{f}:{i}: {s[:100]}")
    return hits


def search(term, pkgs, own, content, workers):
    rx = re.compile(re.escape(term), re.I)
    found = {}  # key -> {"pkg": newest matching version, "why": set()}

    def note(p, why):
        k = key(p)
        e = found.setdefault(k, {"pkg": p, "why": set(), "defs": []})
        if p.get("ts", 0) > e["pkg"].get("ts", 0):
            e["pkg"] = p
        e["why"].add(why)

    # pass 1: the hub's own search
    try:
        hub = get("/search.json?q=" + urllib.parse.quote(term))
        for p in hub.get("packages", []):
            note(p, "hub-search")
    except Exception as e:
        print(f"hub search failed for {term!r}: {e}", file=sys.stderr)

    # pass 2: every version, by name, description and file paths
    for p in pkgs:
        if rx.search(p.get("name") or ""):
            note(p, "name")
        if rx.search(p.get("desc") or ""):
            note(p, "desc")
        if any(rx.search(f) for f in (p.get("files") or {})):
            note(p, "file")

    # pass 3: inside the files of the newest version of each package
    if content:
        newest = latest(pkgs)
        scan = [p for k, p in newest.items() if p.get("name")]
        scan += [e["pkg"] for k, e in found.items() if k not in newest
                 or not newest[k].get("name")]
        with ThreadPoolExecutor(workers) as ex:
            for p, hits in zip(scan, ex.map(lambda p: grep_content(p, rx),
                                             scan)):
                if hits:
                    note(p, "content")
                    found[key(p)]["defs"] = hits

    rows = []
    for k, e in found.items():
        p = e["pkg"]
        owner = own.get(p.get("name"), "?") if p.get("name") else "-"
        deps = max((q.get("dependents") or 0) for q in pkgs if key(q) == k)
        rows.append({
            "name": p.get("name"), "version": p.get("version"),
            "hash": p["hash"], "owner": owner, "dependents": deps,
            "matched": sorted(e["why"]), "desc": p.get("desc") or "",
            "files": sorted(f for f in (p.get("files") or {})
                            if f.endswith(".bend")),
            "defs": e["defs"],
        })
    # named and depended-on first: those are the ones worth reusing
    rows.sort(key=lambda r: (r["name"] is None, -(r["dependents"] or 0),
                             r["name"] or r["hash"]))
    return rows


def report(term, rows, max_defs):
    print(f"## `{term}`: {len(rows)} package(s)\n")
    if not rows:
        print("No package names, describes, ships a file named, or (with "
              "--content) defines it.\n")
        return
    print("| package | owner | dependents | matched | hash | description |")
    print("| :-- | :-- | --: | :-- | :-- | :-- |")
    for r in rows:
        name = f"{r['name']}@{r['version']}" if r["name"] else "(unnamed)"
        desc = r["desc"].replace("|", "\\|")[:90] or ", ".join(r["files"][:4])
        print(f"| {name} | {r['owner']} | {r['dependents']} | "
              f"{', '.join(r['matched'])} | `{r['hash']}` | {desc} |")
    print()
    for r in rows:
        if r["defs"]:
            print(f"- **{r['name'] or r['hash']}**")
            for d in r["defs"][:max_defs]:
                print(f"  - `{d}`")
            if len(r["defs"]) > max_defs:
                print(f"  - … {len(r['defs']) - max_defs} more")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("terms", nargs="+", help="words to look for (case-insensitive)")
    ap.add_argument("--content", action="store_true",
                    help="also grep def/type lines and comments inside .bend files")
    ap.add_argument("--json", action="store_true", help="print JSON, not markdown")
    ap.add_argument("--max-defs", type=int, default=8)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()

    print("crawling the hub…", file=sys.stderr)
    pkgs, own = crawl(), owners()
    print(f"{len(pkgs)} versions, owners known for {len(own)} names",
          file=sys.stderr)
    results = {t: search(t, pkgs, own, a.content, a.workers) for t in a.terms}
    if a.json:
        json.dump(results, sys.stdout, indent=1)
        return
    passes = "hub search, names/descriptions/file names"
    passes += ", file contents" if a.content else " (not file contents: add --content)"
    named = len({p["name"] for p in pkgs if p.get("name")})
    print(f"# Bend hub search\n\nSearched {len(pkgs)} package versions "
          f"({named} names) by {passes}.\n")
    for t, rows in results.items():
        report(t, rows, a.max_defs)


if __name__ == "__main__":
    main()
