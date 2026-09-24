# Techniques, with the code that worked

All from bolt's lint run (bend 2.0.27, native, 4 cores). The file paths are
bolt's, and the commits are on bolt#201.

## A per-stage bench program

The bench lives on the research branch (`autoresearch/bench/rules.bend`) and
imports the project's modules by relative path. Each stage's strict lets
sit in their own def, so the timestamp after a line covers that stage only:

```bend
def stage1(+path: String, +text: String, +toks: List<&2, Lex.Tok>) -> IO(Unit):
  +tree = Tree.of_tokens(toks)                       # runs before the do-block
  do IO<Unit>:
    say("lex", U32.from_nat(List.length(&2, Lex.Tok, toks)))
    say("tree", nodes(tree))
    stage2(path, text, toks, tree)

def say(+name: String, +n: U32) -> IO(Unit):
  IO.print_err(name ++ " " ++ U32.show(n))
```

Print a count derived from each result (tokens, binders, findings), so every
stage has to finish before its line. A second bench reads many files and
times the project-wide rules separately. `Args.argv()` (bolt's widening of
`IO.args()`) gives `List<&2, String>`; `IO.args()` alone is `List<&1, ..>`.

## Sound index plus fallback (unused, 135 s → 0.4 s)

A binary trie on the low 16 bits of a use target's line. The path is a
`List<Bool>` computed from the key, so the proofs match on each bit as a
pattern variable instead of a computed value:

```bend
def path(dd: Nat, +key: U32) -> List<&2, Bool>:
  match dd:
    case 0n:
      Nil{}
    case 1n+p:
      U32.is_even(key) <> path(p, U32.shr(key))

def seen(hh: Hits, +uses: List<&2, Bind.Use>, +line: U32, +col: U32) -> Bool:
  Lazy.or_else(find(path(depth(), line), hh, line, col), _u => used(uses, line, col))
```

The lemmas, in order:
- `find(qq, HNone, ..) == False`;
- insert soundness, for any two paths:
  `or(find(q, put(p, h, c1)), or(eq(c1, c2), find(q, h))) == or(eq(c1, c2), find(q, h))`;
- index soundness over the uses, by induction with a 4-Bool step lemma;
- `or_else(f, _ => u) == s` given `u == s` and `or(f, s) == s`.

In the rule, gate the lookup: `Lazy.and_then(reportable, _u =>
Bool.not(seen(..)))`. Without the gate, every item and pattern binder, none
of which is ever a local use, misses and falls back to the scan.

## Cursor with fallback (binder notes, 35 s → 15.6 s)

```bend
+ahead = U32.is_ge(line, at)
+here = Lazy.either(List<&2, String>, ahead, _u => List.drop(&2, String, cur, U32.to_nat(U32.sub(line, at))), _v => cur)
+text = Lazy.either(String, ahead, _u => head(here), _v => back(lines, line))
```

Use `Lazy.either`, not `Bool.pick`: `U32.sub(line, at)` underflows when the
binder is behind the cursor, and an eager pick would unfold that huge Nat.
Put the fallback `List.get` in a non-recursive helper. bolt's `index` rule
flags it when it sits in the loop body, and that finding is right: it stays
quadratic in the out-of-order case.

## Early-exit twin of a pinned walk (coverage, 10.2 s → 2.75 s)

`fresh` was
`Bool.pick(and(and(has(read, d), not(has(seen, d))), not(has(more, d))), d <> more, more)`,
with a strict `List.contains` scanning every file per edge. The twin asks the
short lists first and stops at the first hit:

```bend
Lazy.and_then(Bool.not(seek(more, d)), _u => Lazy.and_then(Bool.not(seek(seen, d)), _v => seek(read, d)))
```

It's proven by rewriting `seek` → `has` three times, then an eight-case
lemma for the reorder. The old walk was renamed to `walk.spec`, and every
`Imports.reach(` in PROOF.bend became `Imports.walk.spec(` by regex. The
renames made some lines longer than 120 columns: rewrap them before running
the guard.

## Lazy branch in a per-char step (lexer, 2.44 s → 0.89 s)

```bend
Lazy.either(St, continues(mode, cls),
  _u => St{after(mode, cls), kind, line2, col2, sl, sc, cc <> buf, toks},
  _v => St{begin.mode(cls), begin.kind(cls), line2, col2, line, col, [cc], flush(kind, sl, sc, buf, toks)})
```

Also fixed: the two PROOF-local lemmas that stated
`seen(Bool.pick(Lex.St, b, x, y))` now state `Lazy.either`. The proofs didn't
change.

## A cheaper equality, proven (items, 15.6 s → 12.6 s)

```bend
def same(aa: String, bb: String) -> Bool:
  match aa bb:
    case SNil{} SNil{}:
      True{}
    case SCon{h1, t1} SCon{h2, t2}:
      Lazy.and_then(Char.is_eq(h1, h2), _u => same(t1, t2))
    ...
```

The proof: `same(a, b) == String.eq(a, b)`, by matching
`SCon{Chr{+x}, +t1} SCon{Chr{+y}, +t2}` (a nested pattern; a second `match`
on `h1` is refused as "consumed"), then a helper lemma over an arbitrary
`c: Cmp` standing for `U32.cmp(x, y)`, plus one lemma that destructures
`String.cmp`'s pair (`String.eq.fin(String.cmp.rec(hx, hy, rr)) ==
String.eq.fin(rr)`). `U32.is_eq(a, b)` is definitionally
`Cmp.is_eq(U32.cmp(a, b))`. `U32.cmp` compiles natively, so don't try to beat
it. A strict `Bool.and` in `same` was 3x slower: it compares whole strings.

## Proof-writing mechanics that cost a round each

- `%e : P`: `P` is the goal with `_` marking `b` of `e : {a == b}`; the
  current goal is `P[b]` and the new one is `P[a]`. To replace `x` with `y`
  in the goal, pass `Equal.sym(.., y, x, e)` where `e : {x == y}`.
- A lemma used by another must be defined above it, and the "an unfilled
  law is a dead claim" error means it wasn't. A local absurd lemma is
  `%e : ty(_)` with `ty(True) = Unit`, `ty(False) = Empty`.
- Nested matches in a proof must follow binder order: match `b1` (bound by
  `pp`'s pattern) before you match the next parameter `qq`, not after.
- A list or string argument used in two recursive places needs `+`.
- `awk 'length > 120'` counts bytes, not characters: use the linter's own
  width finding.

## Measured and discarded

Record these too. They save the next person the build.
- An early-exit environment search (`Bind.find`): no gain, because
  environments are short.
- Fast equality inside the coverage walk: no gain, since keys differ at the
  first char.
- Dropping unreferenced items: 1133 → 1049 items, not worth it.
