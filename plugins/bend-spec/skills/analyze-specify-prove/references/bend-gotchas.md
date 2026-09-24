# Bend gotchas met while proving

Each of these cost a failed check during the ez and bolt rollouts, with
bend 2.0.25. When a proof or build fails, look here before you doubt the
law: most failures were one of these, fixed in one edit. The project's own
AGENTS.md wins where it has a list (bolt's is the longest; read it before
writing Bend in bolt). ez has no AGENTS.md, so for ez this file is the
list.

## Modules and imports

- **One file, one namespace.** A file imported under two different paths
  in one proof is refused. ez's `sha/*.bend` imported `sha.bend` as
  `./sha.bend` while another module reached it as `../sha/sha.bend`, and
  the proof file that saw both failed. Import a shared file by the same
  relative path everywhere (`../sha/sha.bend`, even from inside `sha/`).
- **A PROOF that uses another module's proved law must import that
  module's PROOF.bend**, not only its LAWS.bend. Otherwise the checker
  reports the law as unfilled. ez's `sha/PROOF.bend` uses
  `pkg/LAWS.bend sort_perm`, so it imports `pkg/PROOF.bend`.
- **Shared lemmas go in one module that is itself in the gate.** ez's
  `check/str.bend` holds string and list lemmas as quantified laws proved
  in the same file, and `check/PROOF.bend` imports it so `ez prove` checks
  it. Other proofs import it as `import ../check/str.bend as Str`.
- `x.of` and `x_of` mangle to the same C name: never both in one module.
- A def must be defined above its use, and there is no mutual recursion.

## Names

- **`law` is a keyword.** A bolt.bend cannot contain `def law()`, so bolt
  v0.9.0's `law` rule could only be set through its group; newer bolt
  renamed it `coverage`.
- **`Done` is taken by Base.** Name a planner's success outcome something
  else (ez uses `Success{}`).
- `Kind` is a keyword: no type of that name.

## Proof terms

- **`Char.is_eq` returning true does not give you equality for free.**
  Reflecting it into `a == b` needs an induction lemma over the 32-bit
  word (ez's `char_eq_true`, through `Word.cmp`), and `String.eq` true to
  equality builds on it (`string_eq_true`). Both are in `check/str.bend`.
- **Linearity.** A binder used twice needs `+` (`for +w: World`); most
  failed steps in ez's spike were a missing `+`, a definition order
  problem, or a def matching on a value it was not given as a parameter.
- **Function values are linear**, so a key function applied at every
  comparison cannot be passed to a generic sort. Reuse a sort already
  proved over a concrete type: ez sorts package blocks and NAR entries as
  `K.File{name, text}` values with `K.file.sort`, so `sort_perm` applies
  unchanged and distinct paths are distinct names.
- **`match` takes parameters and pattern variables only.** To branch on a
  computed value, pass it to a helper that receives it as a parameter; the
  same goes for a destructure (`Out{a, b} = f(x)` fails).
- User code may not call a law before its def is filled, so give an arm
  its induction hypothesis as a parameter (bolt's `Word.xor_assoc`).
- A self-call must shrink the same argument every time, and it must be the
  first live parameter.

## Proof terms: syntax and copying (shake, bend 2.0.27)

These cost shake's walker proofs most of their failed checks.

- **A dependent function type is `@x: A -> B`** (a sigma is `&x: A -> B`).
  `(x: A) -> B` and `∀` do not parse. Write a premise that quantifies as
  `@vv: String -> {P(vv) == True{} : Bool} -> {Q(vv) == True{} : Bool}`.
- **Only Data copies.** `+` works on Data values and on equalities written
  out as `{a == b : T}`, but not on functions, pairs (`A & B` is Type),
  or a value whose type is a def returning `Type` (`gv.In(w, ws)` with
  `def gv.In(...) -> Type`), even when that def's body is an equality.
  When a premise must be used twice (a split with both `and_l` and `and_r`,
  or a recursive call and a use), state it as a Boolean equality with its
  type written out: `+hh: {gv.sufs(ww, ws) == True{} : Bool}`. A
  Pi-typed premise cannot be copied at all, so shake turned "every suffix
  of `w` is a piece of the words" into a Bool (`gv.sufs`) instead of a
  function premise.
- **A copied `let` needs its type**: `+hi = {f(x) : {g(x) == True{} : Bool}}`
  and `+fr = {Grow.Frame{...} : Grow.Frame}`. Without the annotation it
  fails with "expected Data, observed Type" or "cannot infer".
- **Binders in lambdas and Nat patterns take `+` too**: `+vv => hv => ...`,
  `case SCon{+cc, +tt} 1n+(+pp):`.
- **A `let` before a `match` blocks the match** ("a match on a parameter or
  field"). Put the let inside each case, or move the derived fact into a
  helper def that each case calls.
- **`%e : P` turns a goal of the form `P[b]` into `P[a]`** for
  `e : {a == b : T}`. When it reports expected and observed swapped, rewrite
  with `Equal.sym(T, a, b, e)` instead.
- **Refute a clash through a motive.** `SNil == SCon{c, t}`: define
  `snil_ty(s) -> Type` (SNil to Unit, SCon to Empty), `%e : snil_ty(_)`,
  answer `Unit{}`. For Bools, `Walk.wk.false_true`-style
  `{False == True} -> Empty` then `Empty.absurd(Goal, ...)`.
- **Constructor injectivity by `Equal.cong` with a projection**: from
  `SCon{d, u} == SCon{c, t}` get `u == t` as
  `Equal.cong(String, String, s => tail(s), ...)`.
- **Matching a Bool parameter refines premises that mention it**, so a
  helper `f(b: Bool, ..., h: {g(b) == True{} : Bool})` with `match b:` sees
  `h` at `g(True{})` and `g(False{})`. This is how every case split on a
  computed Bool goes: pass the computed value as the parameter.
- **Decidable predicates beat existentials in law statements.** A law
  whose conclusion is `{p(x) == True{} : Bool}` for a law-side Bool `p`
  (`ends`, `piece`, `all_given`) reads plainly, copies, and composes with
  `and`/`or` lemmas; a sigma-typed conclusion does none of these.
- **Avoid needing `String.eq` true to equality** when a structural
  statement will do. shake's "what is left of a word once chars are
  dropped" is proved through `String.drop` and `ends_self` (reflexivity
  only), so no soundness lemma is needed. When one is, ez's
  `check/str.bend` has `string_eq_true`.
- **Per-type lemma copies add up.** List append associativity, reversal
  onto an accumulator and `drop` lemmas get rewritten for each element type
  (`gw.app` for bindings, `sc.app` for names). Before writing one, look for
  it in the project's lemma module and ez's `check/str.bend`, and put a new
  one there rather than beside its first use.

## Running

- **A big pure walk can overflow the interpreter's stack and still run
  compiled.** If `bend file.bend` overflows on a large input, build it
  with `-o` and run the binary before concluding the code is wrong.
- A big `Nat` literal expands in unary: write `U32.to_nat(100000)`.
- `Bool.pick`, `Bool.and`, `Bool.or`, `&&` and `||` are ordinary defs, so
  both branches are evaluated. Never put a different recursive call in
  each branch.
- `bend x.bend` runs `main` after checking; use `--check-only` to check.
- **bend exits 0 when a proof relies on unsafe or foreign code**, printing
  `All terms check, but N defs rely on unsafe or foreign code:`. The gate
  must read the first line, not the exit status.

## The proof gate

Run every PROOF.bend and require the exact first line `All terms check.`
(`ez prove` in ez). Proofs are slow on large files (bolt's closed-law
PROOFs took 84 s and 34 s); run them in parallel under a memory cap, as
`ez prove` does, rather than serially.

## Lint on proof files

Current bolt lints PROOF.bend like code. The findings that recur on new
proofs:

- S003: a def header over 120 chars, or a wrapped header that is not one
  parameter per line. Write
  `def f(\n  a: A,\n  b: B\n) -> {...}:`; when the return type alone
  is too long, give it a type alias def (`def fin.Framed(...) -> Type:`).
- S004: a parameter named with one letter. Use two or more (`vv`, `wd`).
- U001: an unused parameter. Prefix it with `_` (a law's proof def takes
  every binder, so `_name` for the ones the proof ignores).
- C003: `Bool.pick` with a recursive call in a branch evaluates both
  branches; split into a helper that matches.
