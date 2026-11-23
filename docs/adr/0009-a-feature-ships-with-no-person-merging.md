# A feature goes from an approved idea to the live site with no person merging

Once the owner has approved an idea, the workflow plans it, builds it, checks
it, reviews it, merges it, and confirms it on the live site, by itself. Nobody
merges by hand, and no stage waits for the owner as a matter of course. It
stops only for a named reason, and then it waits for the owner's direction.
The safety is in the checks, in one adversarial review, and in a merge that
refuses unless its conditions hold, and not in a person reading each change.
The purpose of the workflow is that the owner is not a part of it.

## Status

Accepted on 22 November 2026, by the owner.

**Not yet in force.** None of the checks, the review, or the merge it relies
on is built (`docs/workflow-plan.md`). Until they are, an agent merges or
pushes to `main` only when the owner asks.

## Considered options

- **A person approves each merge.** Guidance written for agents that run
  unattended recommends it
  (`docs/research/2026-11-22-agent-context-foundation.md`, section 6). Turned
  down: it puts the owner back into every feature.
- **A person merges at first, and the workflow takes over later.** Turned
  down for the same reason.
- **No person on the merge** (chosen).

## Consequences

- One feature is in flight at a time. Every merge is a deploy
  ([0006](0006-every-push-to-main-is-a-production-deploy.md)), and the checks
  that follow a deploy can blame only one change when only one went in.
- A rule that a tool can hold gets a check, and is not left to a reviewer.
  What a reviewer finds that a check could have found becomes a check.
- The reasons to stop are few, and written down. A long list would bring the
  owner back into every feature.

## Confirmed by

No check holds this yet. The merge's own conditions will, once they are
built.
