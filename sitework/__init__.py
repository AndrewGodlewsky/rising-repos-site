"""The scripts of the site's feature workflow, which takes an approved idea from its issue to a feature live on
risingrepos.com. docs/workflow/README.md says which stage runs which, and docs/workflow-plan.md why each is so.

No agent is in any of them. A script decides whatever a script can, so that an agent's judgement is spent only
where nothing else serves. Each is run as `uv run --locked python -m sitework <command>`.
"""
