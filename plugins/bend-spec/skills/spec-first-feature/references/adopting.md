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
5. **Downstream.** A project that depends on this one (usually ez) can now
   point its Trusted row at your requirement IDs instead of at "the library
   is correct".

This is the short form, for a library whose laws are few and mostly
quantified already. When the inventory turns up many closed laws, IO
decisions no law can reach, or behavior the maintainer has to rule on, use
the `analyze-specify-prove` skill instead: it covers the full audit, the
RFC and the rollout.

After this, new features in the project follow SKILL.md like any other.
