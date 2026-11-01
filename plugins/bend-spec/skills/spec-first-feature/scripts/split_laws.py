#!/usr/bin/env python3
"""Split one LAWS.bend/PROOF.bend pair and the SPEC.md rows that name its
laws into one file per guarantee: laws/<Name>.bend and proofs/<Name>.bend,
with LAWS.bend and PROOF.bend left holding only their imports.

  split_laws.py <pair-dir> <names.json> [--spec SPEC.md]
                [--group-names g.json] [--dump out.json] [--write]

names.json maps each Proved row's ID to the guarantee's file name
({"TOML-GET-1": "GetFindsFirstPair"}); a row mapped to "" is dropped.
Without --write it prints the plan and writes nothing.

  --spec SPEC.md       the SPEC.md to read (default <pair-dir>/SPEC.md). It
                       may sit above the pair: a row belongs to this pair
                       when its Law cell names this LAWS.bend; rows with no
                       law, and the trust rows, only when the pair is in
                       SPEC.md's own directory.
  --dump out.json      write the shared groups (key, kind, file, users,
                       size, items) as JSON, to choose their names from.
  --group-names g.json name the shared groups: {"<key>": {"name": "...",
                       "about": "<one-line header>"}}, the keys as --dump
                       prints them.
  --write              write the files under <pair-dir>, and list the
                       dropped helpers in <pair-dir>/.split_dropped.txt.

Placement:
  - a law cited by exactly one Proved row lives in that row's
    laws/<Name>.bend, under the row's text as prose; a pending row's prose
    says so, with its "Left to prove" entry;
  - a law cited by several rows, or by none, gets its own file, named after
    the law (bare_word_reads_on -> laws/BareWordReadsOn.bend); each row
    using it says "also rests on:" (the file lists no rows: that would be a
    reverse reference);
  - a row whose laws are split across pairs says "also stated in:" the
    other pairs' law files of the same name;
  - a row with no law gets a laws/<Name>.bend holding only its prose, not
    imported from LAWS.bend;
  - each law file's proofs go in proofs/<same name>.bend. A proof other
    proofs use as a lemma is placed like any proof helper;
  - a proof helper (or a law def) that one file uses goes in that file;
  - helpers several files use are grouped by the exact set of files that
    use them. A group smaller than MERGE_BELOW chars is folded into one
    with more users, or one it depends on, when that makes no import cycle.
    A group goes in proofs/lemmas/<Name>.bend (law defs: laws/defs/), named
    by --group-names, else after its members' commonest dotted prefix
    (`gd.lk` -> Gd, undotted -> Common), a number added on a clash;
  - a law def only proofs use goes in laws/defs/ as well;
  - a helper nothing reaches is dropped (listed in the report).
Moved comments lose their ID tag lines, and an ID with a name becomes its
law file's path. Lines over 120 wide are folded. Trust rows and Trusted
requirement rows are listed, not placed: they are prose that belongs next
to the code they are about, or nowhere.
"""
import json, os, re, sys
from collections import defaultdict

ID = re.compile(r'^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$')
MERGE_BELOW = 6000                       # a shared group smaller than this (chars) is folded into a wider one
TOK = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')
HEAD = re.compile(r'^(law|def|type)\s+([A-Za-z_][A-Za-z0-9_.]*)')
IMPORT = re.compile(r'^import\s+(\S+)(?:\s+as\s+(\S+))?\s*$')


# --- reading -----------------------------------------------------------------

def parse_spec(path):
    """requirement rows, trust rows, and what is left to prove, each read
    from the table its header names"""
    rows, trust, left = [], [], {}
    kind = None
    for line in open(path).read().splitlines():
        if not line.startswith('|'):
            kind = None if line.strip() else kind
            continue
        cells = [c.strip().replace('\\|', '|') for c in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
        if cells and cells[0] == 'ID':
            kind = ('req' if 'Requirement' in cells else 'trust' if 'Assumption' in cells else 'left')
            continue
        if not cells or not ID.match(cells[0]):
            continue
        if kind == 'req' and len(cells) == 5:
            laws = []
            for e in cells[4].split(';'):
                ws = e.split()
                if len(ws) == 2:
                    laws.append((ws[0], ws[1]))
            rows.append(dict(id=cells[0], req=cells[1], level=cells[2], status=cells[3], laws=laws))
        elif kind == 'trust':
            trust.append(dict(id=cells[0], what=cells[1], why=cells[2] if len(cells) > 2 else ''))
        elif kind == 'left':
            left[cells[0]] = ' '.join(cells[1:])
    return rows, trust, left


class Item:
    def __init__(self, kind, name, lines, pre):
        self.kind, self.name, self.lines, self.pre = kind, name, lines, pre

    @property
    def ctors(self):
        if self.kind != 'type':
            return []
        return [m.group(1) for m in (re.match(r'^  ([A-Z][A-Za-z0-9_]*)\{', l) for l in self.lines[1:]) if m]

    def text(self):
        return '\n'.join(self.pre + self.lines)


def parse_bend(path):
    """imports [(target, alias, line)], items [Item] in order."""
    imports, items = [], []
    cur, pre, seen_import = None, [], False
    for line in open(path).read().splitlines():
        m = HEAD.match(line)
        if m:
            cur = Item(m.group(1), m.group(2), [line], pre)
            items.append(cur)
            pre = []
            continue
        if cur is not None and (line.startswith(' ') or line.startswith(')') or line == ''):
            cur.lines.append(line)
            continue
        cur = None
        im = IMPORT.match(line)
        if im:
            imports.append((im.group(1), im.group(2), line))
            seen_import = True
            pre = []
            continue
        if line.startswith('#') and seen_import:
            pre.append(line)
        elif line == '' and pre:
            pre.append(line)
    for it in items:
        while it.lines and it.lines[-1] == '':
            it.lines.pop()
        while it.pre and it.pre[0] == '':
            it.pre.pop(0)
    return imports, items


# --- naming --------------------------------------------------------------------

def camel(name):
    return ''.join(p[:1].upper() + p[1:] for p in re.split(r'[_.]', name) if p)


def topic_of(name):
    return name.split('.')[0] if '.' in name else 'common'


def alias_of(topic, taken):
    a = 'Lm' + camel(topic)
    while a in taken:
        a += 'X'
    return a


# --- the split -------------------------------------------------------------------

def tokens(text):
    return set(TOK.findall(text))


def strip_tags(pre):
    return [l for l in pre if not ID.match(l.lstrip('#').strip())]


def wrap(text, width=76):
    out, cur = [], ''
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            out.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w) if cur else w
    if cur:
        out.append(cur)
    return ['# ' + l for l in out]


BINDER = [
    re.compile(r'[(,]\s*[+\-&]?([a-z_][A-Za-z0-9_]*)\s*[:,)]'),      # a parameter
    re.compile(r'\bfor\s+[+\-&]?([a-z_][A-Za-z0-9_]*)\s*:'),          # a law binder
    re.compile(r'[&+\-]?([a-z_][A-Za-z0-9_]*)\s*=>'),                   # a lambda
    re.compile(r'^\s*[+\-&]?([a-z_][A-Za-z0-9_]*)\s*=[^=>]', re.M),    # a let
    re.compile(r'[{,]\s*[+\-&]?([a-z_][A-Za-z0-9_]*)\s*(?=[,}])'),     # a pattern field
]


def binders(it):
    text = '\n'.join(it.lines)
    return {m.group(1) for b in BINDER for m in b.finditer(text)}


def scan(line, depth):
    """each char's bracket depth on a line that opens at depth, strings and
    chars and comments skipped (None), and the depth it closes at"""
    out, quote, esc = [], None, False
    for ch in line:
        if quote:
            out.append(None)
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == quote:
                quote = None
            continue
        if ch == '#':
            out.extend([None] * (len(line) - len(out)))
            break
        if ch in '"\'':
            quote = ch
            out.append(None)
            continue
        if ch in '([{':
            depth += 1
        out.append(depth)
        if ch in ')]}':
            depth -= 1
    return out, depth


def fold(line, depth, width=120):
    """a code line over the width that opens at bracket depth, broken after
    the last comma inside a bracket, the rest four deeper; a line with no such
    comma is left as it is"""
    if len(line) <= width or line.lstrip().startswith('#'):
        return [line]
    ds, _ = scan(line, depth)
    cut = None
    for i, ch in enumerate(line[:width - 1]):
        if ch == ',' and ds[i] and ds[i] > 0 and line[i + 1:i + 2] == ' ':
            cut = i
    if cut is not None:
        _, d2 = scan(line[:cut + 1], depth)
        indent = len(line) - len(line.lstrip()) + 4
        return [line[:cut + 1]] + fold(' ' * indent + line[cut + 2:], d2, width)
    # else after the last ` <> ` that fits, the operator left trailing, as
    # Bend continues a line
    for i in range(min(width - 3, len(line) - 4), 0, -1):
        if line[i:i + 4] == ' <> ' and ds[i + 1] is not None:
            _, d2 = scan(line[:i + 3], depth)
            indent = len(line) - len(line.lstrip()) + 2
            return [line[:i + 3]] + fold(' ' * indent + line[i + 4:], d2, width)
    return [line]


def header(line, width=120):
    """a one-line def header over the width, one parameter per line"""
    ds, _ = scan(line, 0)
    try:
        op = line.index('(')
    except ValueError:
        return [line]
    close, parts, start, angle = None, [], op + 1, 0
    for i in range(op + 1, len(line)):
        if ds[i] is None:
            continue
        if line[i] == '<' and line[i - 1].isalnum():
            angle += 1
        elif line[i] == '>' and angle and line[i - 1] != '-':
            angle -= 1
        if line[i] == ')' and ds[i] == 1:
            close = i
            break
        if line[i] == ',' and ds[i] == 1 and not angle:
            parts.append(line[start:i].strip())
            start = i + 1
    if close is None:
        return [line]
    parts.append(line[start:close].strip())
    return [line[:op + 1]] + ['  %s%s' % (q, ',' if k < len(parts) - 1 else '') for k, q in enumerate(parts)] \
        + [line[close:]]


def fold_body(body, width=120):
    """long lines folded: a one-line def header to one parameter per line, a
    parameter line of a wrapped header marked (wrap forbids splitting it),
    any other line at a comma or a `<>`"""
    out, depth, in_header = [], 0, False
    for line in body.split('\n'):
        if line and not line.startswith(' ') and not line.startswith(')'):
            depth = 0
        ds, end = scan(line, depth)
        starts = line.startswith('def ')
        ends = end == 0 and line.split('#')[0].rstrip().endswith(':')
        if len(line) > width and starts and ends:
            out.extend(header(line, width))
        elif len(line) > width and in_header and not starts and not line.startswith(')'):
            out.append(line + '  # noqa: S002')
        else:
            out.extend(fold(line, depth, width))
        in_header = (starts or in_header) and not ends
        depth = end
    return '\n'.join(out)


def rewrap(line, width=120):
    """a comment line over the width, broken at the last space that fits"""
    stripped = line.lstrip()
    if len(line) <= width or not stripped.startswith('# '):
        return [line]
    lead = line[:len(line) - len(stripped)] + '# '
    cut = line.rfind(' ', len(lead), width)
    if cut <= len(lead):
        return [line]
    return [line[:cut]] + rewrap(lead + line[cut + 1:], width)


def rel(src_dir, target, out_dir):
    """an import target written in src_dir, rewritten for a file in out_dir"""
    if not target.startswith('.'):
        return target
    absol = os.path.normpath(os.path.join(src_dir, target))
    r = os.path.relpath(absol, out_dir)
    return r if r.startswith('.') else './' + r


def main():
    pkg = sys.argv[1]
    names = json.load(open(sys.argv[2]))
    write = '--write' in sys.argv
    def arg(flag):
        return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None
    group_names = json.load(open(arg('--group-names'))) if arg('--group-names') else {}
    group_meta = {}
    # the rows of a SPEC.md that may sit above this directory: a row is this
    # directory's when it names a law of this LAWS.bend; one with no law, and
    # the trust rows, are the SPEC.md's own directory's
    spec_path = arg('--spec') or os.path.join(pkg, 'SPEC.md')
    spec_dir = os.path.dirname(os.path.abspath(spec_path))
    at_root = os.path.abspath(pkg) == spec_dir
    mine = os.path.normpath(os.path.relpath(os.path.join(os.path.abspath(pkg), 'LAWS.bend'), spec_dir))
    rows, trust, left = parse_spec(spec_path)
    # a row named "" in the names map is dropped: its guarantee is gone
    rows = [r for r in rows if names.get(r['id'], None) != '']
    host = {r['id']: (os.path.dirname(os.path.normpath(r['laws'][0][0])) if r['laws'] else '') for r in rows}
    kept = []
    for r in rows:
        here = [(q, l) for q, l in r['laws'] if os.path.normpath(q) == mine]
        there = sorted({os.path.dirname(os.path.normpath(q)) for q, l in r['laws'] if os.path.normpath(q) != mine})
        if here or (at_root and not r['laws']):
            kept.append(dict(r, laws=here, elsewhere=there))
    rows = kept
    if not at_root:
        trust = []
    laws_imports, laws_items = parse_bend(os.path.join(pkg, 'LAWS.bend'))
    proof_imports, proof_items = parse_bend(os.path.join(pkg, 'PROOF.bend'))
    laws_alias = next(a for t, a, _ in proof_imports if t.rstrip('/').endswith('LAWS.bend'))

    law_items = {it.name: it for it in laws_items if it.kind == 'law'}
    spec_items = [it for it in laws_items if it.kind != 'law']
    spec_names = {}
    for it in spec_items:
        spec_names[it.name] = it
        for c in it.ctors:
            spec_names[c] = it

    # which rows cite each law
    cited = defaultdict(list)
    for r in rows:
        if r['level'] != 'Proved':
            continue
        for _, ln in r['laws']:
            if ln in law_items and r['id'] not in cited[ln]:
                cited[ln].append(r['id'])

    # law -> law file name
    home = {}
    for ln in law_items:
        cs = cited.get(ln, [])
        home[ln] = names[cs[0]] if len(cs) == 1 else camel(ln)
    files = defaultdict(list)           # law file name -> [law names]
    for ln in law_items:
        files[home[ln]].append(ln)
    prose = {}                          # law file name -> header lines
    for r in rows:
        if r['level'] != 'Proved':
            continue
        n = names[r['id']]
        own = [ln for _, ln in r['laws'] if home.get(ln) == n]
        rest = sorted({home[ln] for _, ln in r['laws'] if ln in home and home[ln] != n})
        lines = wrap(r['req'])
        if r['status'] == 'pending':
            lines += ['#', '# pending: the laws here prove part of this, not all of it.']
            if r['id'] in left:
                lines += ['#'] + wrap('left to prove: ' + left[r['id']])
        if rest:
            lines += ['#'] + wrap('also rests on: ' + ', '.join('laws/%s.bend' % x for x in rest))
        if r.get('elsewhere'):
            lines += ['#'] + wrap('also stated in: ' + ', '.join(
                os.path.relpath(os.path.join(spec_dir, d, 'laws', n + '.bend'), os.path.abspath(pkg))
                for d in r['elsewhere']))
        prose[n] = lines
        files.setdefault(n, [])
    for f, lns in files.items():
        if f not in prose:
            # no reverse list: each guarantee that rests on it says so ("also rests on")
            prose[f] = []

    # --- law helpers: which law files use each (transitively through helpers)
    item_tok = {id(it): tokens(it.text()) for it in laws_items + proof_items}
    def spec_deps(it):
        return {spec_names[t] for t in item_tok[id(it)] if t in spec_names and spec_names[t] is not it}
    spec_users = defaultdict(set)
    for f, lns in files.items():
        stack = [d for ln in lns for d in spec_deps(law_items[ln])]
        seen = set()
        while stack:
            d = stack.pop()
            if id(d) in seen:
                continue
            seen.add(id(d))
            spec_users[id(d)].add(f)
            stack.extend(spec_deps(d))

    # --- proof units: law fills and helpers
    fills = defaultdict(list)           # law file -> [items]
    helpers = {}                        # name -> [items] (law + def of one name)
    prefix = laws_alias + '.'
    for it in proof_items:
        if it.name.startswith(prefix) and it.name[len(prefix):] in law_items:
            fills[home[it.name[len(prefix):]]].append(it)
        else:
            helpers.setdefault(it.name, []).append(it)
    # a law's proof is a unit like any helper, keyed '@<law>': a proof other
    # proofs use as a lemma is placed by its users, its own file among them
    owner, fill_key = {}, {}
    for f, its in fills.items():
        for it in its:
            ln = it.name[len(prefix):]
            k = '@' + ln
            helpers.setdefault(k, []).append(it)
            owner[k], fill_key[ln] = f, k
    h_key = {}                          # a token naming a helper: its name, or a constructor of its type
    for h, its in helpers.items():
        if h.startswith('@'):
            continue
        h_key[h] = h
        for i in its:
            for c in i.ctors:
                h_key[c] = h
    def laws_refs(its):
        ts = set().union(*(item_tok[id(i)] for i in its))
        return {t[len(prefix):] for t in ts if t.startswith(prefix)}
    def deps_of(k):
        its = helpers[k]
        ts = set().union(*(item_tok[id(i)] for i in its))
        ds = {h_key[t] for t in ts if t in h_key}
        ds |= {fill_key[r] for r in laws_refs(its) if r in fill_key}
        ds.discard(k)
        return ds
    h_users = defaultdict(set)
    for k, f in owner.items():
        stack, seen = [k], set()
        while stack:
            h = stack.pop()
            if h in seen:
                continue
            seen.add(h)
            h_users[h].add(f)
            stack.extend(deps_of(h))
    # a law helper only proofs use: it still needs a home
    for h, its in helpers.items():
        for r in laws_refs(its):
            if r in spec_names:
                spec_users[id(spec_names[r])]  # touch: keeps it
    proof_spec_refs = set()                 # law defs a live proof unit names
    for h, its in helpers.items():
        if not h_users.get(h):
            continue
        for r in laws_refs(its):
            if r in spec_names:
                proof_spec_refs.add(id(spec_names[r]))

    # --- shared things, grouped by the files that use them. A thing only
    # uses things whose users are a superset of its own, so a group only
    # imports groups with strictly more users: the groups never form a cycle
    def place_groups(kind, keys, users_of, deps_of, size_of, name_of, doc_of):
        """the shared things in groups: first by the exact set of files that
        use them; then each small group folded into a wider one it can join
        without an import cycle; then named, by the names map when it names
        the group, else after its commonest dotted prefix"""
        groups = defaultdict(set)
        for k in keys:
            us = users_of(k)
            if len(us) > 1:
                groups[frozenset(us)].add(k)
        gid = {k: g for g, ks in groups.items() for k in ks}
        members = {g: set(ks) for g, ks in groups.items()}
        users = {g: set(g) for g in groups}
        def gdeps(g):
            return {gid[d] for k in members[g] for d in deps_of(k) if d in gid and gid[d] != g}
        def acyclic():
            state = {}
            def visit(v):
                state[v] = 1
                for w in gdeps(v):
                    if state.get(w) == 1 or (w not in state and not visit(w)):
                        return False
                state[v] = 2
                return True
            return all(state.get(v) == 2 or visit(v) for v in list(members))
        def size(g):
            return sum(size_of(k) for k in members[g])
        changed = True
        while changed:
            changed = False
            for g in sorted(members, key=lambda g: (size(g), sorted(g))):
                if size(g) >= MERGE_BELOW:
                    break
                targets = [t for t in members if t != g and (users[t] > users[g] or t in gdeps(g))]
                for t in sorted(targets, key=lambda t: (len(users[t]), size(t), sorted(t))):
                    for k in members[g]:
                        gid[k] = t
                    members[t] |= members[g]
                    if acyclic():
                        users[t] |= users[g]
                        del members[g], users[g]
                        changed = True
                        break
                    members[t] -= members[g]
                    for k in members[g]:
                        gid[k] = g
                if changed:
                    break
        named, used = {}, set()
        for g in sorted(members, key=lambda g: (len(users[g]), sorted(users[g]))):
            ks = members[g]
            real = sorted(u for u in users[g] if not u.startswith('<'))
            key = kind + ':' + ','.join(real) + '|' + min(name_of(k) for k in ks)
            if key in group_names:
                base = group_names[key]['name']
            else:
                pre = defaultdict(int)
                for k in ks:
                    pre[topic_of(name_of(k))] += 1
                base = camel(max(pre, key=lambda t: (pre[t], t)))
            n, i = base, 1
            while n in used:
                i += 1
                n = base + str(i)
            used.add(n)
            for k in ks:
                named[k] = n
            group_meta[(kind, n)] = dict(key=key, users=real, about=group_names.get(key, {}).get('about', ''),
                items=[(name_of(k), doc_of(k)) for k in sorted(ks, key=name_of)], size=size(g))
        return named

    # every law def the proofs reach, through other law defs
    proof_reach, stack = set(), [spec_names_by_id for spec_names_by_id in proof_spec_refs]
    by_id = {id(it): it for it in spec_items}
    while stack:
        k = stack.pop()
        if k in proof_reach:
            continue
        proof_reach.add(k)
        stack.extend(id(d) for d in spec_deps(by_id[k]))
    spec_by_id = {id(it): it for it in spec_items}
    def first_doc(its):
        for it in its:
            for l in it.pre:
                if l.startswith('#') and not ID.match(l.lstrip('#').strip()):
                    return l.lstrip('#').strip().removeprefix('LAW: ')
        return ''
    spec_topic = place_groups(
        'defs', list(spec_by_id),
        lambda k: spec_users[k] or ({'<proofs>', '<proofs2>'} if k in proof_reach else set()),
        lambda k: {id(d) for d in spec_deps(spec_by_id[k])},
        lambda k: len(spec_by_id[k].text()),
        lambda k: spec_by_id[k].name,
        lambda k: first_doc([spec_by_id[k]]))
    h_topic = place_groups('lemmas', list(helpers), lambda h: h_users[h], deps_of,
                           lambda h: sum(len(i.text()) for i in helpers[h]),
                           lambda h: h if not h.startswith('@') else h[1:], lambda h: first_doc(helpers[h]))

    # where each thing lives: (dir, file name)
    where = {}                          # key -> path relative to pkg, without .bend
    for ln in law_items:
        where[('law', ln)] = 'laws/' + home[ln]
    dropped_spec, dropped_h = [], []
    for k, it in spec_by_id.items():
        if k in spec_topic:
            where[('spec', k)] = 'laws/defs/' + spec_topic[k]
        elif spec_users[k]:
            where[('spec', k)] = 'laws/' + next(iter(spec_users[k]))
        else:
            dropped_spec.append(it.name)
    for h in helpers:
        if h in h_topic:
            where[('h', h)] = 'proofs/lemmas/' + h_topic[h]
        elif h_users[h]:
            where[('h', h)] = 'proofs/' + next(iter(h_users[h]))
        else:
            dropped_h.append(h)

    # --- assembling the files
    out = defaultdict(list)             # path -> [(item, source)]
    for f in files:
        out['laws/' + f]
        for ln in files[f]:
            out['laws/' + f].append(law_items[ln])
    for k, it in spec_by_id.items():
        if ('spec', k) in where:
            out[where[('spec', k)]].append(it)
    for f in fills:
        out['proofs/' + f]
    for h, its in helpers.items():
        if ('h', h) in where:
            out[where[('h', h)]].extend(its)
    # keep source order within each file
    order = {id(it): i for i, it in enumerate(laws_items + proof_items)}
    for p in out:
        out[p].sort(key=lambda it: order[id(it)])

    # the alias each generated file is imported under
    taken = {a for _, a, _ in laws_imports + proof_imports if a}
    alias = {}
    for p in out:
        base = p.split('/')[-1]
        if p.startswith('laws/') and not p.startswith('laws/defs/'):
            a = base
        elif p.startswith('laws/defs/'):
            a = 'Df' + camel(base)
        else:
            a = 'Lm' + camel(base)
        while a in taken or a in alias.values():
            a += 'X'
        alias[p] = a

    def law_file_of_ref(r):
        if r in law_items:
            return where[('law', r)]
        if r in spec_names:
            return where.get(('spec', id(spec_names[r])))
        return None

    def rewrite(it, me, from_laws):
        """the item's text, references to moved things rewritten; and the
        generated files it needs"""
        needs = set()
        bound = binders(it)
        def sub(m):
            t = m.group(0)
            # an undotted lowercase name may be a local: rewrite it only as a
            # call, and never when the item binds that name itself
            if '.' not in t and t[:1].islower() and (m.string[m.end():m.end() + 1] != '(' or t in bound):
                return t
            if t.startswith(prefix) and not from_laws:
                r = t[len(prefix):]
                p = law_file_of_ref(r)
                if p:
                    needs.add(p)
                    q = where.get(('h', fill_key.get(r)))
                    if q and q != me:
                        needs.add(q)
                    return '\x00' + p + '\x01.' + r
                return t
            if from_laws and t in spec_names:
                p = where.get(('spec', id(spec_names[t])))
                if p and p != me:
                    needs.add(p)
                    return '\x00' + p + '\x01.' + t
                return t
            if not from_laws and t in h_key:
                p = where.get(('h', h_key[t]))
                if p and p != me:
                    needs.add(p)
                    return '\x00' + p + '\x01.' + t
            return t
        body = '\n'.join(it.lines)
        if from_laws:
            pre = strip_tags(it.pre)
        else:
            pre = it.pre
        # a fill's own name: Laws.x -> <its file's alias>.x
        new = TOK.sub(sub, body)
        return '\n'.join(pre + [new]), needs

    src_imports = {True: laws_imports, False: proof_imports}
    written = {}
    for p, its in sorted(out.items()):
        from_laws = p.startswith('laws/')
        texts, needs = [], set()
        for it in its:
            t, n = rewrite(it, p, from_laws)
            texts.append(t)
            needs |= n
        if p.startswith('proofs/') and not p.startswith('proofs/lemmas/'):
            f = p.split('/', 1)[1]
            needs.add('laws/' + f)
            for ln in files.get(f, []):
                q = where.get(('h', fill_key.get(ln)))
                if q:
                    needs.add(q)
        needs.discard(p)
        out_dir = os.path.dirname(os.path.join(pkg, p))
        body = '\n\n'.join(texts)
        used = tokens(body)
        hdr = []
        if p.startswith('laws/') and not p.startswith('laws/defs/'):
            hdr = prose.get(p.split('/', 1)[1], [])
        elif p.startswith('laws/defs/') or p.startswith('proofs/lemmas/'):
            meta = group_meta[('defs' if p.startswith('laws/defs/') else 'lemmas', p.split('/')[-1])]
            what = 'definitions the laws share' if p.startswith('laws/defs/') else 'lemmas the proofs share'
            hdr = wrap(meta['about'] or what)
        else:
            hdr = ['# proofs of laws/%s.bend' % p.split('/', 1)[1]]
        imps = ['import Base']
        for t, a, line in src_imports[from_laws]:
            if t == 'Base' or t.rstrip('/').endswith('LAWS.bend'):
                continue
            if a and any(u.startswith(a + '.') or u == a for u in used):
                imps.append('import %s as %s' % (rel(pkg, t, out_dir), a))
        # each file names what it imports itself, short: its own law file
        # Laws, other law files L1.., shared definitions D1.., lemmas M1..,
        # proof files P1..
        local, count = {}, defaultdict(int)
        own = 'laws/' + p.split('/', 1)[1] if p.startswith('proofs/') and not p.startswith('proofs/lemmas/') else None
        taken_here = {a for _, a, _ in src_imports[from_laws] if a}
        for n in sorted(needs):
            if n == own:
                a = 'Laws'
            else:
                k = ('D' if n.startswith('laws/defs/') else 'L' if n.startswith('laws/')
                     else 'M' if n.startswith('proofs/lemmas/') else 'P')
                while True:
                    count[k] += 1
                    a = '%s%d' % (k, count[k])
                    if a not in taken_here:
                        break
            local[n] = a
            imps.append('import %s as %s' % (rel(pkg, './' + n + '.bend', out_dir), a))
        body = re.sub('\x00([^\x01]*)\x01', lambda m: local[m.group(1)], body)
        body = fold_body(body)
        written[p + '.bend'] = '\n'.join(hdr + imps) + '\n\n' + body.rstrip() + '\n'

    # a requirement ID cited in a moved comment names its law file now
    def law_path(i):
        return os.path.relpath(os.path.join(spec_dir, host.get(i, ''), 'laws', names[i] + '.bend'),
                               os.path.abspath(pkg))
    by_len = sorted(names, key=len, reverse=True)
    idre = re.compile(r'\b(' + '|'.join(re.escape(i) for i in by_len) + r')\b') if by_len else None
    if idre:
        for k in list(written):
            written[k] = '\n'.join(l2 for l in idre.sub(lambda m: law_path(m.group(1)),
                                                           written[k]).split('\n') for l2 in rewrap(l))

    # aggregators
    imported = [f for f in files if files[f]]
    laws_agg = ['# The laws: each file under laws/ is one guarantee, its prose on top.',
                '# A file here with no law is one still to state.', 'import Base']
    laws_agg += ['import ./laws/%s.bend as %s' % (f, alias['laws/' + f]) for f in sorted(imported)]
    proof_agg = ['# The proofs: proofs/<name>.bend proves laws/<name>.bend. The gate:',
                 '# `bend PROOF.bend` prints exactly `ALL PROOFS CHECK` as its first line.', 'import Base',
                 'import ./LAWS.bend as Laws']
    proof_agg += ['import ./proofs/%s.bend as P%s' % (f, f) for f in sorted(fills)]
    written['LAWS.bend'] = '\n'.join(laws_agg) + '\n'
    written['PROOF.bend'] = '\n'.join(proof_agg) + '\n'

    # report
    print('rows: %d proved/pending, %d trust rows' % (sum(r['level'] == 'Proved' for r in rows), len(trust)))
    print('law files: %d (%d own-file shared/untagged laws)' % (len(files), sum(1 for f in files if f not in names.values())))
    print('proof files: %d, lemma files: %d, law-def files: %d' % (
        len(fills), sum(p.startswith('proofs/lemmas/') for p in out), sum(p.startswith('laws/defs/') for p in out)))
    big = sorted(((len(v), k) for k, v in written.items()), reverse=True)[:8]
    print('largest files (chars):', ', '.join('%s %d' % (k, n) for n, k in big))
    print('dropped (unreachable): %d law defs, %d proof helpers' % (len(dropped_spec), len(dropped_h)))
    for t in trust:
        print('trust row to place by hand: %s: %s' % (t['id'], t['what']))
    left_ids = sorted({m for t in written.values() for m in re.findall(r'\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b', t)
                       if ID.match(m) and re.search(r'-\d+$', m)})
    if left_ids:
        print('IDs still cited in the new files (no law file to name): ' + ', '.join(left_ids))
    for r in rows:
        if r['level'] == 'Trusted':
            print('trusted requirement row: %s' % r['id'])
    if arg('--dump'):
        json.dump({m['key']: dict(kind=k, file=n, users=m['users'], size=m['size'], items=m['items'][:60],
                                  more=max(0, len(m['items']) - 60))
                   for (k, n), m in group_meta.items()}, open(arg('--dump'), 'w'), indent=1)
    if write:
        for p, text in written.items():
            fp = os.path.join(pkg, p)
            os.makedirs(os.path.dirname(fp) or '.', exist_ok=True)
            open(fp, 'w').write(text)
        with open(os.path.join(pkg, '.split_dropped.txt'), 'w') as fh:
            fh.write('\n'.join(['# law defs'] + dropped_spec + ['# proof helpers'] + dropped_h) + '\n')


if __name__ == '__main__':
    main()
