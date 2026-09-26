# GitHub: protection, release-please, publishing

## The ruleset every package repo carries

One repository ruleset named `main: require ci`, targeting `~DEFAULT_BRANCH`:

```json
{"name":"main: require ci","target":"branch","enforcement":"active",
 "conditions":{"ref_name":{"exclude":[],"include":["~DEFAULT_BRANCH"]}},
 "rules":[{"type":"deletion"},{"type":"non_fast_forward"},
  {"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false,"allowed_merge_methods":["squash"]}},
  {"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,"do_not_enforce_on_create":false,"required_status_checks":[{"context":"check / check","integration_id":15368}]}}],
 "bypass_actors":[{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"pull_request"}]}
```

Apply it: `POST repos/<org>/<repo>/rulesets --input ruleset.json`, or `PUT
…/rulesets/<id>` when one by that name exists. Set the merge settings too:

```bash
gh api -X PATCH repos/<org>/<repo> -F allow_squash_merge=true -F allow_merge_commit=false \
  -F allow_rebase_merge=false -F allow_auto_merge=true -F delete_branch_on_merge=true
```

`check / check` is the job name of each repo's `ci.yml`, which calls the
shared `Emerging-Patterns/actions` `nix-flake-check.yml`. A repo with no CI
(e.g. `skills`) gets no required check.

## release-please and the required check

release-please (shared workflow, `versioning: always-bump-minor`) opens its
release PR with `github.token`. GitHub does not start workflows for events a
workflow's token causes, so `check / check` never reports and the PR sits
`BLOCKED`. Until the shared workflow is given a PAT or App token (its
`secrets.token` input), start CI by closing and reopening the PR as a person:

```bash
gh pr close N -R org/repo && gh pr reopen N -R org/repo
gh pr merge N -R org/repo --squash --auto
```

The merge creates the tag and GitHub release a few seconds later.

## Publish workflow

Each repo's `publish.yml` is `workflow_dispatch` with input `tag`. It calls the
shared workflow, which checks out `refs/tags/<tag>` and runs
`nix develop -c ez publish`, so it uses the **repo's flake-pinned** ez and bend.
Trust it only after the tooling pass. Before that, publish locally with
`scripts/publish_hash.sh`. `ez publish` prints the hash on a line of its own,
then the import line. The workflow's log has them after the `hub description:`
line.
