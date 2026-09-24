#!/usr/bin/env python3
"""Does a new proof catch a planted bug on its own?

  isolate_mutant.py PROOF.bend PREFIX [PREFIX ...]

Run it in a scratch copy of the repo with the mutant already planted (never
in your working tree: it rewrites .bend files). It runs `bend PROOF.bend`,
reads the def the first failure names, and, unless that def's name starts
with one of the PREFIXes (the new proof's defs, e.g. `gv.` or
`Laws.values_given`), replaces that def's body with `?TODO` and runs again.
It stops when a failure lands in a PREFIX def (the new proof catches the
mutant) or when nothing fails but the TODOs (it does not).

A failure location is printed as `name` (a def of PROOF.bend), `LAWS.name`
(a law's proof, `def Laws.name` in PROOF.bend) or `../dir/file.name` (a def
of an imported module); the script maps each back to its file.
"""
import os
import re
import subprocess
import sys


def run(proof):
    r = subprocess.run(["bend", proof], capture_output=True, text=True)
    return r.stdout + r.stderr


def locate(loc, proof):
    base = os.path.dirname(proof) or "."
    m = re.match(r"((?:\.\./|\./)*[\w/]+)\.(\S+)$", loc)
    if m and "/" in m.group(1):
        path = os.path.normpath(os.path.join(base, m.group(1) + ".bend"))
        return path, m.group(2)
    if loc.startswith("LAWS."):
        return proof, "Laws." + loc[len("LAWS."):]
    return proof, loc


def stub(path, name):
    s = open(path, encoding="utf-8").read()
    i = s.find("\ndef " + name + "(")
    if i < 0:
        return False
    k = i + 1
    depth, seen, q = 0, False, k
    while q < len(s):  # the header ends at the first `:` + newline outside brackets
        ch = s[q]
        if ch in "({":
            depth, seen = depth + 1, True
        elif ch in ")}":
            depth -= 1
        elif ch == ":" and seen and depth == 0 and s[q + 1] == "\n":
            break
        q += 1
    body = q + 2
    r = body
    while r < len(s) and (s[r] in " \n"):  # the body is every indented or blank line after
        nl = s.find("\n", r)
        r = len(s) if nl < 0 else nl + 1
    open(path, "w", encoding="utf-8").write(s[:body] + "  ?TODO\n\n" + s[r:])
    return True


def main():
    proof, prefixes = sys.argv[1], sys.argv[2:]
    for _ in range(200):
        out = run(proof)
        m = re.search(r"Location: (\S+)", out)
        if not m:
            first = out.strip().splitlines()[0] if out.strip() else ""
            print("NOT CAUGHT by the new proof:", first)
            return 1
        loc = m.group(1)
        path, name = locate(loc, proof)
        if any(name.startswith(p) or loc.startswith(p) for p in prefixes):
            print("CAUGHT by", loc)
            return 0
        if not stub(path, name):
            print("cannot find the def for", loc, "in", path)
            return 2
        print("stubbed", loc)
    return 2


if __name__ == "__main__":
    sys.exit(main())
