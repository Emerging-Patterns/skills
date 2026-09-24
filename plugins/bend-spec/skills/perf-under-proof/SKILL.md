---
name: perf-under-proof
description: Make a Bend project that keeps SPEC.md, LAWS.bend and PROOF.bend faster without weakening one guarantee. Profile, find the shape that costs the time, rewrite it and keep every law proven, one measured change at a time, with tracking kept off main. Use this whenever the job is speed in a proven Bend repo (ez, bolt, eztoml, ezhttp, ezjson, snap, shake), for requests like "bolt has become slow", "auto research lint performance", "why does ez take a minute on this repo", "profile the checker", "this rule is quadratic" or "make the planner faster", including when the user names an autoresearch-style loop plugin. For new behavior use spec-first-feature; for a project whose laws are not trustworthy yet use analyze-specify-prove first.
---

# Performance under proof

A proven Bend project can be made fast without trusting anything new. The
laws don't mention speed, but they pin the code closely. A tagged law's
statement is human-owned (spec-first-feature, step 1), and the proofs unfold
the very defs you want to replace. So the work is always the same:

1. find the def that costs the time;
2. write a faster def that computes the **same value for every input** the
   law quantifies over, not only for the inputs the run feeds it;
3. prove the two equal, and put the proof where the old proofs can use it;
4. measure, and keep the change only if the whole run got faster and the
   findings didn't change.

bolt's lint went from 208 s to 20 s over its own tree this way, in seven
kept changes. No LAWS.bend was edited, and the findings stayed
byte-identical. The history is on bolt's `autoresearch/bolt-lint-perf`
branch (`autoresearch/loop-260924-2130/summary.md`), and the fixes are
bolt#201. Every technique below comes from that run.

## 0. Orient

Read the repo's AGENTS.md (the gate, the Bend gotchas) and the
spec-first-feature skill's vocabulary. A perf change is a **refactor** in
spec-first-feature's table: nothing in SPEC.md changes, no tagged law
statement changes, proofs may be rewritten. If the only fast version you can
find needs a law restated, stop and put it to the user (step 6). Don't
edit LAWS.bend yourself.

## 1. Branches: tracking off main

Research leaves a trail: a results table, a profiler, verify/guard scripts,
`experiment:` commits and reverts. None of that belongs on main. Use two
branches:

- **`autoresearch/<topic>`** (or any research branch the user names): the
  loop's commits, the TSV, the summary, the bench programs, the scripts.
  Push it, and never open a PR from it.
- **the fix branch**: one conventional `perf(<area>): ...` commit per kept
  change, carried over with the tracking paths excluded:

  ```
  git diff <exp>~1 <exp> -- . ':(exclude)autoresearch' | git apply --index
  ```

  Then check the fix branch's code is byte-identical to the research tree:
  `git diff <research> <fix> -- . ':(exclude)autoresearch'` must be empty.

If someone opens a PR from the research branch anyway, a PR's head can't
change: open the clean one from the fix branch and close the other with a
pointer.

## 2. Set up the metric, the guard and a profiler

**Metric.** Wall time of the real thing, built from the commit under test,
run over a real input: `bolt --gpu off` over the repo's own tree, `ez test`
on a real project. A `verify.sh` should `git archive HEAD` into a scratch
directory (minus the tracking directory, or the linter lints your bench too),
build with bare `bend <entry> -o`, time one run, and print the number. Build
natively: the JS lane is not what users run, and it overflows on long input.

**Guard.** Every PROOF.bend prints `All terms check.`, **and** the output
equals the baseline's. For a linter, compare the findings with `path:line:col`
normalized to `path:`, so code moving down a file isn't a regression. But
compare everything else, the summary line included. The guard also catches
your own mess: a long line, an undocumented def, a def no law reaches now
(bolt L001), a `List.get` in a loop (U007). Fix those in the same iteration.

**Profiler.** The generated C is a dispatch-table runtime, so native
profilers see one big function. Write a bench program instead (see
`references/techniques.md`): read one input and print a line to stderr after
each stage and each rule. A strict `+x = f(..)` let runs before the
`do` block, so put each stage's let in its own def, and have every stage
print something derived from its result, so nothing can skip it. Timestamp
the lines outside:

```
bench.bin --gpu off big.bend 2>&1 | while read -r l; do echo "$(date +%s.%N) $l"; done
```

Profile the **largest** input alone first. Superlinear cost shows up as
time out of proportion to size (bolt: a 192 KB file took 4 s, a 1.4 MB one
180 s). Then profile the whole run as well: cross-file work (project rules,
closures, the planner) doesn't appear in per-file numbers. Compare the sum
of per-file times with the full run.

## 3. Find the shape

Nearly every cost in bolt was one of these (details and fixes in
`references/techniques.md`):

| Shape | Seen as | Fix |
| :-- | :-- | :-- |
| A loop scans a list it carries unchanged, once per element | `unused`: per binder, every use (135 s) | an index as a **sound fast path**, the scan only on a miss |
| `List.get` from the head, per element, through a helper | binder notes: `List.get(lines, line)` per binder | walk a cursor forward in source order, and fall back to `List.get` for an element out of order |
| An eager `Bool.pick` whose not-taken branch does real work | lexer `step`: flush on every char | `Lazy.either` / `Lazy.stop`, and restate the proof's pick lemmas |
| A first-match search that binds its recursion above the pick | `deps_of`, strict `List.contains` | `Lazy.stop` / `Lazy.or_else` early exit |
| The same work done twice | `Src.of` lexed every file twice | compute once, share |
| Duplicates in a list every lookup scans | `law x` + `def x` as two items | drop adjacent duplicates where it's built |
| A costly equality in a hot scan | `String.eq` via `String.cmp` builds pairs per char | a char-by-char `same` with early exit, proven `== String.eq` |

Look for the first four in the project's own linter output too. bolt's
`strict`, `pick`, `eager`, `index` and `concat` catch some forms and miss the
ones behind a helper (bolt#196–#199).

## 4. The loop: one change, measured

For each iteration:

1. Pick the biggest remaining stage from the latest profile.
2. Check, in the bench, that the idea helps **before** proving anything:
   a throwaway build with the change (even an unproven or wrong-valued one,
   such as `has(..)` replaced by `False{}`) tells you how much of the stage
   the change can remove. Several ideas die here in five minutes, and that is
   the point.
3. Make the change properly: fast def, equality lemma, proofs updated.
4. Commit `experiment: <what>` on the research branch, run verify then guard.
5. Keep it if the metric dropped and the guard passed; otherwise revert. Log
   a row either way, measured-only discards included, with numbers:
   `iteration timestamp commit metric delta guard status description`.

A gain inside noise (well under a second on a 20 s run) isn't worth new
proof code. Simplicity wins ties.

## 5. Keeping the proofs

The law quantifies over **all** inputs, so a speedup that relies on how the
real input is shaped (sorted, source-ordered, unique) must still be exactly
right on any other input. Four ways to get there, from cheapest:

- **Early exit is free.** `Lazy.or_else(a, _u => x) == Bool.or(a, y)` given
  `x == y`, and likewise for `and_then`, `stop` against `pick`, and `either`
  against `pick`. Each is a two-case lemma (match on the Bool). Reordering
  the tests of a `Bool.and` chain is an eight-case lemma.
- **Sound fast path plus fallback.** Build any index where a *hit* is
  certainly right and a miss falls back to the original scan:
  `Lazy.or_else(find(index, q), _u => scan(list, q))`. You then need only
  soundness (found ⇒ scan finds it), never completeness, so no order laws
  on `U32` or `String` are needed. Prove it as or-absorption:
  `Bool.or(find(ix, q), scan(xs, q)) == scan(xs, q)`. It only pays when
  misses are rare, so gate the lookup lazily to the elements that are
  actually asked about.
- **A proven twin.** When many proofs reason about a def's structure (bolt's
  closure walk had ~30 lemmas over `fresh` and `reach`), leave the old def
  as a dotted spec helper (`walk.spec`, `fresh.spec`) that the proofs keep
  using, add the fast twin under the name the code calls, and prove
  `twin == spec` step for step (induction on the fuel, rewriting each step's
  intermediate with the helper lemmas). Only the top-level proofs that unfold
  the entry point need one rewrite each. Dotted names keep the old defs out of
  bolt's coverage rule.
- **Restate the PROOF-local lemmas.** Lemmas in PROOF.bend (not LAWS.bend)
  are yours. When `Bool.pick(St, b, x, y)` becomes `Lazy.either(St, b, _u =>
  x, _v => y)`, change the lemma statements that mention it; their proofs
  are the same `match b`.

Before changing a def, list who unfolds it:
`grep -n "Mod\.name\b" */PROOF.bend */*/PROOF.bend */LAWS.bend`. A def only
IO or lookups use, with no law naming it (bolt's `annotate`, `items`),
needs no proof, but the guard still has to show the output is unchanged.

## 6. When a law blocks the speedup

Sometimes the fast version can't be proven equal because the law fixes the
**interface**. bolt's `resolves` states name resolution over `Names{its,
als}` with `its` a `List<String>`, so every lookup that misses must scan the
list, and an index needs the law restated. Don't route around it: a new
constructor, or a second path the law doesn't cover, would leave the code
that actually runs unproven. Stop, measure what's left, and put the choice to
the user: which law, what it would say instead, and what it would buy.

## 7. Wrap up

- On the research branch: a `summary.md` (baseline → final, a table of kept
  changes with before/after per stage, what blocks more, how to reproduce)
  and a `handoff.json` if the loop tool wants one.
- On the fix branch: the full gate the repo names (AGENTS.md), including the
  stay-list integration tests. bolt's `tests/bare.bend` builds from nothing
  and lints the tree, which catches most slips.
- Shapes that generalize become rule proposals (issues on bolt): the shape,
  a real instance with its measured cost, why the current rules miss it, and
  a proposed trigger that keeps idiomatic code quiet.
- The PR says what each commit bought, that no law statement or SPEC.md row
  changed, and what the laws block.
