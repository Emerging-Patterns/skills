# Running the rollout with subagents

ez's rollout was about twenty PRs over several days, most written by
subagents while a lead agent verified, pushed, watched CI and merged. This
is the loop that worked, and the mistakes that shaped it. Skip it if you
are doing the work alone; the per-PR checks still apply.

## Contents

- One PR per coherent change
- Briefing an agent
- Isolation
- The lead's loop for each PR
- Reviewing agent output
- Keeping agents current
- When agents stop
- Things never to do

## One PR per coherent change

A PR is one decided behavior change, one work package, or one phase step.
Mixing them makes the PR description unable to say what changed and how it
was checked, which is the record reviewers rely on. The RFC's decided
behavior changes and the design doc's work packages are the natural PR
list; the DAG says which can run in parallel.

## Briefing an agent

Give each agent:

- the goal as the RFC or design doc states it, with the section to read,
  and the rows it should land or leave pending;
- current main as the base, not a tagged release (an agent briefed against
  a release re-derives work that already merged);
- the exact checks to run and report: the proof gate count, bolt's error
  count, the fresh-clone `cmp`, and master-versus-branch runs for each
  behavior change;
- which laws must not change (tagged statements are human-owned);
- its own build script and scratch paths (below);
- the instruction to merge origin's main into its branch before it
  reports, so the lead verifies what will actually merge;
- that it reports in the PR-description format: changes, laws, behavior
  changes, checks, what is left pending.

## Isolation

Each agent works in its own git worktree, on its own branch, with its own
build output path and scratch directories. A shared build script once
pointed one agent's checks at another agent's worktree without anyone
noticing, so its "passing" gate was checking the wrong code. Give every
agent a script with its worktree path written in, or have it derive every
path from its own working directory.

## The lead's loop for each PR

1. Wait for the agent's report, then read its diff in full.
2. Verify independently: build from a fresh clone of the agent's branch,
   run the gate and bolt, run the fresh-clone check, and rerun the
   behavior-change cases that matter. Do not merge on the agent's word.
3. Push the branch and open the PR with the description (it ends with the
   attribution lines the session asks for).
4. Watch CI. When it finishes, open each job's log and confirm every check
   actually ran its steps; this matters most on the first run of a new
   check.
5. Squash-merge on green, unless the user said they merge; then hand them
   the PR link and the CI result.
6. Clean up: remove the worktree, delete the local branch, and reset your
   own working branch to the new main.
7. Tell the user what merged, what it proved, and what starts next.

## Reviewing agent output

Read the diff for things that pass every check and are still wrong:

- values specific to the agent's machine in committed files. One agent
  recorded absolute paths in the committed ledger, which would have broken
  the headline guarantee on every other machine. It was sent back;
- a tagged law's statement edited to make a proof go through;
- a closed law, a `tests/*.bend` file, or a Trusted row added without a
  reason;
- a decision left inside IO where a pure function would fit;
- SPEC.md, the RFC and the inventory not updated together.

Send it back with the specific problem rather than fixing it yourself, so
the agent's worktree and report stay consistent.

## Keeping agents current

When a PR merges that a running agent depends on (shared lemmas, a new
bolt pin, a rename), tell that agent, and have it merge main before it
continues. An agent that builds on a stale base produces a PR that
conflicts or, worse, merges cleanly and duplicates work.

## When agents stop

Usage limits can stop every running agent at once. Their work survives in
their worktrees, committed or not. When the limit resets, resume each one
with a short status message: what merged in the meantime, what it had
finished, and what is left. Tell the user what happened and when work
resumed.

## Things never to do

- **Never publish to a package hub to test something.** An upload is
  public and permanent. Use a local oracle hub (ez's `check/serve.bend`)
  or a dead address, and know the limits of each.
- **Never put model identifiers in repository artifacts**: code, docs,
  commit messages beyond the session's attribution lines, SPEC.md, RFCs.
- Never lower a bolt level to get a PR green; that is a policy decision
  for the maintainer.
- Never push to or merge into main without the checks having run.
