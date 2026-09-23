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
