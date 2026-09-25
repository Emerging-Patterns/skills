#!/usr/bin/env python3
"""Map a fleet of ez-managed Bend repos: what each one pins, what is stale,
and the order to upgrade them in.

    fleet_graph.py [DIR]            # DIR holds one clone per repo (default .)
    fleet_graph.py [DIR] --json     # the same, as JSON

Reads each clone's default branch as checked out (refresh first: git fetch,
checkout the default branch, reset to origin). For every repo it reports:

  deps   - [deps.*] in ez.toml: key, git url, tag, hash, and whether that hash
           is on the hub (GET <hub>/<hash>/manifest == 200)
  tools  - [tools.*] pins (bolt as a lint tool, for example)
  flake  - flake.lock inputs that point at other fleet repos, with their rev
  latest - the repo's newest GitHub release tag (gh), and how many commits
           the default branch is ahead of it

Then it prints a topological order over [deps] edges (package content), which
is the order releases must go in. [tools] and flake inputs are dev tooling:
they do not change a package's hub hash, so they are updated in a final pass
and are not edges here (they form cycles with the package edges: ez pins shake
by rev while shake's flake pins ez).
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

HUB = "https://hub.bend-lang.com"


def load_ledger(path):
    """ez.toml as nested dicts. ez writes flat tables of `key = "string"`, so
    this is enough when tomllib (Python 3.11+) is missing."""
    try:
        import tomllib
        return tomllib.load(open(path, "rb"))
    except ModuleNotFoundError:
        pass
    doc, cur = {}, None
    for line in open(path):
        line = line.split("#", 1)[0].strip() if not line.strip().startswith('"') else line.strip()
        if not line:
            continue
        m = re.fullmatch(r"\[([^\]]+)\]", line)
        if m:
            cur = doc
            for part in m.group(1).split("."):
                cur = cur.setdefault(part.strip('"'), {})
            continue
        m = re.fullmatch(r'"?([^"=\s]+)"?\s*=\s*"(.*)"', line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2)
    return doc


def sh(*args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def on_hub(h):
    if not h:
        return None
    try:
        with urllib.request.urlopen(f"{HUB}/{h}/manifest", timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def slug(url):
    m = re.search(r"github\.com[/:]([^/]+/[^/.]+)", url or "")
    return m.group(1) if m else None


def repo_info(path):
    name = os.path.basename(os.path.abspath(path))
    info = {"name": name, "slug": slug(sh("git", "remote", "get-url", "origin", cwd=path)),
            "deps": [], "tools": [], "flake": []}
    led = os.path.join(path, "ez.toml")
    if os.path.exists(led):
        doc = load_ledger(led)
        for k, d in (doc.get("deps") or {}).items():
            info["deps"].append({"key": k, "git": d.get("git"), "slug": slug(d.get("git")),
                                 "tag": d.get("tag"), "rev": d.get("rev"), "hash": d.get("hash"),
                                 "hub": d.get("hub"), "entry": d.get("entry")})
        for k, t in (doc.get("tools") or {}).items():
            info["tools"].append({"key": k, "slug": slug(t.get("git")), "tag": t.get("tag"), "rev": t.get("rev")})
        info["publish_as"] = (doc.get("package") or {}).get("publish-as")
    lock = os.path.join(path, "flake.lock")
    if os.path.exists(lock):
        nodes = json.load(open(lock))["nodes"]
        for k, n in nodes.items():
            lk = n.get("locked") or {}
            if lk.get("type") == "github":
                info["flake"].append({"input": k, "slug": f'{lk["owner"]}/{lk["repo"]}', "rev": lk.get("rev", "")[:10]})
    if info["slug"]:
        tag = sh("gh", "api", f"repos/{info['slug']}/releases/latest", "--jq", ".tag_name")
        info["latest"] = tag
        branch = sh("gh", "api", f"repos/{info['slug']}", "--jq", ".default_branch")
        if tag and branch:
            info["ahead"] = sh("gh", "api", f"repos/{info['slug']}/compare/{tag}...{branch}", "--jq", ".ahead_by")
    return info


def topo(repos):
    names = {r["slug"]: r["name"] for r in repos if r["slug"]}
    edges = {r["name"]: sorted({names[d["slug"]] for d in r["deps"] if d["slug"] in names}) for r in repos}
    order, seen, stack = [], set(), set()

    def visit(n):
        if n in seen:
            return
        if n in stack:
            raise SystemExit(f"cycle in [deps] through {n}")
        stack.add(n)
        for m in edges[n]:
            visit(m)
        stack.discard(n)
        seen.add(n)
        order.append(n)

    for n in sorted(edges):
        visit(n)
    return order, edges


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else "."
    repos = [repo_info(os.path.join(root, d)) for d in sorted(os.listdir(root))
             if os.path.isdir(os.path.join(root, d, ".git")) and
             (os.path.exists(os.path.join(root, d, "ez.toml")) or os.path.exists(os.path.join(root, d, "flake.nix")))]
    by_slug = {r["slug"]: r for r in repos}
    for r in repos:
        for d in r["deps"]:
            d["on_hub"] = on_hub(d["hash"])
            up = by_slug.get(d["slug"])
            d["latest"] = up.get("latest") if up else None
    order, edges = topo(repos)
    if "--json" in sys.argv:
        print(json.dumps({"repos": repos, "order": order, "edges": edges}, indent=2))
        return
    for r in repos:
        flag = "  PUBLISH-AS SET" if r.get("publish_as") else ""
        print(f"== {r['name']}  latest={r.get('latest') or '-'}  unreleased={r.get('ahead') or '?'}{flag}")
        for d in r["deps"]:
            stale = "" if not d["latest"] or d["tag"] == d["latest"] else f"  -> {d['latest']}"
            print(f"   dep  {d['key']:<10} {d['tag'] or d['rev'][:10] if d['rev'] else d['hub']:<10} {d['hash']}  hub={'ok' if d['on_hub'] else 'MISSING'}{stale}")
        for t in r["tools"]:
            print(f"   tool {t['key']:<10} {t['tag'] or (t['rev'] or '')[:10]}")
        for f in r["flake"]:
            if f["slug"] in by_slug:
                print(f"   flake {f['input']:<9} {f['slug']}@{f['rev']}")
    print("\nrelease order ([deps] edges, leaves first):")
    for n in order:
        print(f"  {n}" + (f"  <- {', '.join(edges[n])}" if edges[n] else ""))


if __name__ == "__main__":
    main()
