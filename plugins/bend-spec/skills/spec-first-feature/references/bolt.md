# bolt specifics

Read bolt's AGENTS.md first. It holds the gate, the layout, and the Bend
gotchas. This file covers what is different about bolt features, and mostly
that means lint rules.

## A new lint rule

A rule is a requirement twice over. Its header comment is where the SPEC.md
row's wording comes from, and its findings land in other people's CI.
Downstream projects pin bolt, and the 0.4.0 to 0.8.1 jump produced over
1,300 errors in ez. So the bar is higher than for internal code.

1. **Write the header comment first.** The comment block at the top of
   `bolt/rules/<group>/<slug>.bend` is the spec. Say exactly which tokens or
   tree shapes the rule reports, and every exemption. It should be precise
   enough that the SPEC.md row can quote it (see `put.bend` and
   BOLT-RULE-C004). Rewording the header later changes the requirement, so
   it goes through review.
2. **Add the SPEC.md row** under "Rules (BOLT-RULE)": `BOLT-RULE-<code>`,
   Proved, pending, wording "`<slug>` reports exactly … and nothing else."
3. **Assign the code.** Append an `Entry{slug, code, group}` to
   `bolt/codes.bend` with the next number in the group's letter
   (C correctness, U suspicious, S style, L laws, P pedantic). Codes are
   append-only. Never renumber, and never reuse a retired code (L004 stays
   reserved). BOLT-OUT-1 needs slug↔code to stay a bijection.
4. **Pick the default level.** Opinionated rules are opt-in first, on only
   when a bolt.bend names them (BOLT-CFG-6), like `quantify` and `trace`
   were. A rule defaults above warn only after the false-positive check
   below.
5. **Laws.** Every rule needs two kinds of law. Put them in
   `bolt/rules/LAWS.bend`, tagged with the rule's ID:
   - *frame*: no finding on input without the pattern. This is the law that
     protects users from noise.
   - *completeness*: a finding on every instance. The usual shape is a count
     equality against a small independent counter, as in `put_counts`,
     `nat_counts` and `param_counts`.
   Quantify over the token list or tree, not over a fixed source string.
   If the rule's pattern is code, BOLT-RULE-INERT (comment and string
   contents don't change findings) has to keep holding. Check your rule is
   in or out of its exemption list on purpose.
6. **False-positive check on real code.** Before the rule's default goes
   above warn, run it over ez, eztoml, ezhttp, ezjson, snap, shake and bolt
   itself, and read every finding. Report the numbers to the user. The spec
   inventory found confirmed false positives or negatives in most existing
   correctness and suspicious rules. That means fixing an existing rule's
   precision is often worth more than a new rule, so say so if you find
   that's the case.
7. **Semantic change to a released rule** (new findings, different
   exemptions): reword the row and the header in the same change, flag it as
   a behavior change, and make it visible in the conventional-commit type so
   release-please versions it. Don't slip it in as a fix.

Rules this ecosystem wants, because they turn the audit's lessons into
checks (each still goes through the steps above):

- a law whose proof is only `{==}` over binders its statement never
  inspects;
- an IO function that branches on a value it read, where a pure planner
  would fit;
- string-matching another program's output where a structured check exists.

## Other bolt features (CLI, LSP, grading, scope)

These follow the World model in `docs/rfc/bolt-spec.md`. The lint run's
planner takes the listed directories and read files as values, decides
everything, and returns lines plus an exit status. The LSP is a step
function from messages to replies and asks. Put new decisions there, not in
`bolt/walk/*.c|js`, `bolt/lsp/transport/*`, or the lint interpreter, which
are Trusted (BOLT-TRUST-3, -4, and the interpreter rows as they land).

`trace` and project rules only run on whole-tree lints, and the LSP runs
per-file rules only. So a new project rule gets no editor diagnostics, and
its row should say CLI only if that matters to users.

## Never

No `bend --publish` and no `ez publish`, not even to test. To exercise the
publish path without publishing, use `BEND_HUB=http://127.0.0.1:1`.
