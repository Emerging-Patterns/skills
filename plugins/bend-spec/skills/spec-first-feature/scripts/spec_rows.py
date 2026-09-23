#!/usr/bin/env python3
"""Read the requirement and trust tables of a SPEC.md (bolt's format).

  spec_rows.py SPEC.md                  rows by group prefix, then pending ones
  spec_rows.py SPEC.md --next EZ-RES    the next free ID with that prefix
                                        (a bolt rule: --next BOLT-RULE-C; the code
                                        itself comes from bolt/codes.bend)
  spec_rows.py SPEC.md --pending        only the pending rows

It reads only tables whose header is exactly the requirement or trust
header, as bolt's `trace` rule does. It is a planning aid; `trace` is the check.
"""
import re
import sys

REQ = "| ID | Requirement | Level | Status | Law |"
TRUST = "| ID | Assumption | Why it is trusted |"
ID = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")


def cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def read(path):
    reqs, trusts, mode = [], [], None
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        s = line.strip()
        if s == REQ:
            mode = "req"
            continue
        if s == TRUST:
            mode = "trust"
            continue
        if not s.startswith("|"):
            mode = None
            continue
        if mode is None or set(s) <= set("|:- "):
            continue
        c = cells(s)
        row = {"line": n, "id": c[0] if c else ""}
        if mode == "req":
            row.update(level=c[2] if len(c) > 2 else "", status=c[3] if len(c) > 3 else "",
                       law=c[4] if len(c) > 4 else "", ok=len(c) == 5 and bool(ID.match(row["id"])))
            reqs.append(row)
        else:
            row.update(ok=len(c) == 3 and bool(ID.match(row["id"])))
            trusts.append(row)
    return reqs, trusts


def prefix(i):
    return i.rsplit("-", 1)[0]


def next_id(ids, pre):
    # EZ-RES -> EZ-RES-9; BOLT-RULE-C -> BOLT-RULE-C011 (a code tail: letter + fixed width)
    dash = [m for m in (re.match(re.escape(pre) + r"-(\d+)$", i) for i in ids) if m]
    if dash:
        return f"{pre}-{max(int(m.group(1)) for m in dash) + 1}"
    code = [m for m in (re.match(re.escape(pre) + r"(\d+)$", i) for i in ids) if m]
    if code:
        width = len(code[0].group(1))
        return f"{pre}{str(max(int(m.group(1)) for m in code) + 1).zfill(width)}"
    return pre + "-1"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    reqs, trusts = read(argv[1])
    ids = [r["id"] for r in reqs] + [t["id"] for t in trusts]
    if "--next" in argv:
        print(next_id(ids, argv[argv.index("--next") + 1]))
        return 0
    bad = [r for r in reqs + trusts if not r["ok"]]
    for r in bad:
        print(f"malformed row, line {r['line']}: {r['id']}")
    pending = [r for r in reqs if r["status"] == "pending"]
    if "--pending" not in argv:
        groups = {}
        for r in reqs:
            groups.setdefault(prefix(r["id"]), []).append(r)
        for g, rs in groups.items():
            done = sum(r["status"] == "proved" for r in rs)
            tr = sum(r["level"] == "Trusted" for r in rs)
            print(f"{g:14} {len(rs):3} rows  {done:3} proved  {tr:3} trusted  last {rs[-1]['id']}")
        print(f"{len(trusts)} trust rows")
    print(f"{len(pending)} pending:")
    for r in pending:
        print(f"  {r['id']}")
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except BrokenPipeError:
        sys.exit(0)
