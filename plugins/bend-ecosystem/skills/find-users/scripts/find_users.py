#!/usr/bin/env python3
"""Find GitHub repos outside an org that use, or mention, the org's Bend packages.

GitHub's code index misses many young repos, so code search alone undercounts.
This runs three passes and merges them:

  1. code search for every `<org>/<pkg>`, every hub hash, and marker phrases;
  2. collect every Bend repo search can find (code seeds + repo search);
  3. read each candidate's file tree (ez.toml, ez.lock.toml, bolt.bend, .ez/)
     and README (org links, package names, ez commands).

Needs `gh` (authenticated). Code search allows 10 requests a minute, so the run
sleeps between queries; expect a few minutes.

  find_users.py --org Emerging-Patterns --clones ~/projects/bend > report.md
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

HASH_RE = re.compile(r"0x[0-9a-f]{32}")
# files whose presence means a repo is managed by ez or linted by bolt
TREE_RE = re.compile(r"(^|/)(ez\.toml|ez\.lock\.toml|bolt\.bend|\.ez/)")
# searches that seed the list of Bend 2 repos
SEED_CODE = [
    '"import Base" extension:bend',
    '"-> IO(Unit)" extension:bend',
    '"bend-lang.com/install.sh"',
    '"hub.bend-lang.com"',
    '"--publish" bend',
]
SEED_REPOS = [
    ["bend", "--language=bend"],
    ["bend2 OR bend-lang OR hvm4"],
    ["bend", "--created=>2026-01-01"],
]
# `bend` keeps these off Osdag's bolt checks and card games' Lightning Bolt
MARKERS = ['"bolt lsp" bend', '"bolt check" bend', '"ez tool run"', '"ez add" bend', '"ez lock" bend']


def gh(args, quiet=True):
    """Run gh with stdin closed (gh in a read loop otherwise eats the input)."""
    r = subprocess.run(["gh", *args], stdin=subprocess.DEVNULL,
                       capture_output=True, text=True)
    if r.returncode != 0 and not quiet:
        print(f"gh {' '.join(args)}: {r.stderr.strip()}", file=sys.stderr)
    return r


def code_search(q, limit=100):
    """One code search, waiting out the 10/minute limit. Returns (repo, path) pairs."""
    for _ in range(3):
        r = gh(["search", "code", q, "--limit", str(limit), "--json", "repository,path"])
        if r.returncode == 0:
            time.sleep(7)
            return [(x["repository"]["nameWithOwner"], x["path"]) for x in json.loads(r.stdout)]
        if "rate limit" in r.stderr.lower():
            lim = json.loads(gh(["api", "rate_limit"]).stdout)["resources"]["code_search"]
            wait = max(5, lim["reset"] - int(time.time()) + 2)
            print(f"  rate limited, sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        print(f"  query failed: {q}: {r.stderr.strip()[:200]}", file=sys.stderr)
        return []
    return []


def local_hashes(clones):
    """Hub hashes named in the clones' ez.toml, ez.lock.toml and READMEs."""
    found = set()
    for d in Path(clones).expanduser().iterdir():
        for f in ("ez.toml", "ez.lock.toml", "README.md"):
            p = d / f
            if p.is_file():
                found |= set(HASH_RE.findall(p.read_text(errors="ignore")))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default="Emerging-Patterns")
    ap.add_argument("--packages", nargs="*", help="default: every repo in the org")
    ap.add_argument("--clones", help="dir of local clones to harvest hub hashes from")
    ap.add_argument("--hashes", nargs="*", default=[], help="extra hub hashes (old releases)")
    ap.add_argument("--skip-sweep", action="store_true", help="code search only")
    a = ap.parse_args()

    org = a.org
    pkgs = a.packages or json.loads(gh(["repo", "list", org, "--limit", "200",
                                        "--json", "name"]).stdout)
    pkgs = [p if isinstance(p, str) else p["name"] for p in pkgs]
    hashes = set(a.hashes) | (local_hashes(a.clones) if a.clones else set())
    pkg_re = re.compile(
        rf"{re.escape(org)}/({'|'.join(map(re.escape, pkgs))})\b"
        r"|\bez (add|run|lock|init|tool)\b|\bbolt (lsp|check)\b", re.I)

    evidence = defaultdict(set)  # repo -> {"kind: detail"}
    pkg_hits = defaultdict(set)  # repo -> packages named

    def outside(repo):
        return not repo.lower().startswith(org.lower() + "/")

    print(f"code search: {len(pkgs)} packages, {len(hashes)} hashes", file=sys.stderr)
    for p in pkgs:
        # unquoted: GitHub fails to match the quoted form across the slash
        for repo, path in code_search(f"{org}/{p}"):
            if outside(repo):
                evidence[repo].add(f"code: {path} names {org}/{p}")
                pkg_hits[repo].add(p)
    for h in sorted(hashes):
        for repo, path in code_search(h):
            if outside(repo):
                evidence[repo].add(f"code: {path} names hash {h}")
    for m in MARKERS:
        for repo, path in code_search(m):
            if outside(repo):
                evidence[repo].add(f"marker {m}: {path}")

    if not a.skip_sweep:
        cands = set(evidence)
        for q in SEED_CODE:
            cands |= {r for r, _ in code_search(q)}
        for args in SEED_REPOS:
            r = gh(["search", "repos", *args, "--limit", "100", "--json", "fullName"])
            if r.returncode == 0:
                cands |= {x["fullName"] for x in json.loads(r.stdout)}
        cands = sorted(c for c in cands if outside(c))
        print(f"sweep: {len(cands)} candidate repos", file=sys.stderr)
        for repo in cands:
            r = gh(["api", f"repos/{repo}/git/trees/HEAD?recursive=1", "--jq", ".tree[].path"])
            for path in r.stdout.splitlines():
                if TREE_RE.search(path):
                    evidence[repo].add(f"file: {path}")
            r = gh(["api", f"repos/{repo}/readme", "--jq", ".content"])
            if r.returncode == 0:
                text = base64.b64decode(r.stdout).decode(errors="ignore")
                for line in text.splitlines():
                    m = pkg_re.search(line)
                    if m:
                        evidence[repo].add(f"readme: {line.strip()[:160]}")
                        if m.group(1):
                            pkg_hits[repo].add(m.group(1))
                    for h in HASH_RE.findall(line):
                        if h in hashes:
                            evidence[repo].add(f"readme hash {h}")

    def weak(repo):
        return all(e.startswith("marker ") for e in evidence[repo])

    print(f"# Users of {org} packages outside the org\n")
    print("`listing?` = names 4+ packages, probably an awesome-list or index.\n")
    for repo in sorted(evidence, key=lambda r: (-len(evidence[r]), r)):
        if weak(repo):
            continue
        tag = " (listing?)" if len(pkg_hits[repo]) >= 4 else ""
        print(f"## [{repo}](https://github.com/{repo}){tag}\n")
        for e in sorted(evidence[repo])[:15]:
            print(f"- {e}")
        print()
    weak_repos = sorted(r for r in evidence if weak(r))
    if weak_repos:
        print("## Marker phrase only (usually unrelated, check by hand)\n")
        for repo in weak_repos:
            print(f"- [{repo}](https://github.com/{repo}): {sorted(evidence[repo])[0]}")

if __name__ == "__main__":
    main()
