# Bringing a sibling project under the convention

For eztoml, ezhttp, ezjson, snap, shake, or a new Bend library that has
LAWS.bend/PROOF.bend but no SPEC.md yet. Do this as its own change before
the feature, not mixed into one.

1. **Copy the format.** Take the Format and Requirements structure from
   bolt's SPEC.md, which is the canonical format that ez also adopted:
   - requirement tables headed exactly `| ID | Requirement | Level | Status | Law |`;
   - a trust table headed exactly `| ID | Assumption | Why it is trusted |`;
   - a short uppercase prefix for the project (`TOML-`, `HTTP-`, `SNAP-`).
2. **Inventory, don't invent.** List what the existing quantified laws
   actually prove, and write those rows as Proved/proved with tags. List
   what the README promises that no law proves, and write those rows as
   pending. Closed laws are not evidence: note them in the PR and plan
   their deletion. Libraries that implement a standard (TOML 1.0, RFC 9110,
   RFC 3986) should name the standard's section in the row.
3. **Trust boundary.** At least "the Bend checker is sound" (point at
   EZ-TRUST-1), plus each pinned dependency whose proofs this project relies
   on. Name the dependency and its pinned hash as the reason.
4. **Turn on the rules.** In the root bolt.bend, add `def trace() -> String:
   "error"` and `def closed() -> String: "error"`. Get `bolt` clean over the
   whole tree.
5. **Layout and pins.** Current ez expects `main.bend` at the root as the
   whole interface and every other file under `src/`: consumers import only
   `main.bend`, and everything under `src/` may change in any release
   (shake and ezjson are laid out this way). Mark each undotted IO def or
   re-export in `main.bend` `# noqa: L001 <reason>` (e.g. `IO wrapper,
   trusted (HTTP-TRUST-5)` or `re-export of Qs.get, laws in LAWS.bend`) so
   `coverage` does not ask for a law no one can state, then set `coverage`
   to error. Dotted defs (`http.get`, `text.fill`) are helpers that bolt
   never grades for coverage, so a noqa on one is itself an S005 finding.
   Don't keep an `ENTRY.bend` of wrapper laws: a file importing foreign code
   can only print `SOME PROOFS FAIL`, so its check proves nothing.
   Pin the linter in the lock (`[tools.bolt]` in ez.toml) and relock with
   the pinned ez, so CI's bolt is the one you ran. A command-line program
   also needs a Trusted row for what the compiled Bend runtime does to argv
   before `main` (it takes the first `--`, `--help`, `--threads` and
   `--gpu`; shake's SHAKE-TRUST-2), and its README must say so.
6. **Downstream.** A project that depends on this one (usually ez) can now
   point its Trusted row at your requirement IDs instead of at "the library
   is correct".

This is the short form, for a library whose laws are few and mostly
quantified already. When the inventory turns up many closed laws, IO
decisions no law can reach, or behavior the maintainer has to rule on, use
the `analyze-specify-prove` skill instead: it covers the full audit, the
RFC and the rollout.

After this, new features in the project follow SKILL.md like any other.
