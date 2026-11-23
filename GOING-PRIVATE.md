# Going private

What it would take to make this repository private, and where the site's
process would break on the day it is. Nothing here has been done. The
repository is public, and RisingRepos: `intent.md` records that it stays so
for now and is to be looked at again
([RisingRepos#65](https://github.com/AndrewGodlewsky/RisingRepos/issues/65)).
It was looked at again on 22 November 2026. It stays public while the account
that owns it is on GitHub Free, and it is expected to go private later. This
file is what that day's look found, so that the work is not done twice.

Each fact below says how it was found. The files were read at this
repository's commit `4665ccb` and at RisingRepos's `5514d8f`, and GitHub's
pages on 2026-11-22. Nothing was tried on a private repository. A plan's
terms, a price, and a line of a workflow can each change, so whoever makes the
change reads each one again first. "Not checked", at the end, lists what this
file does not know.

## What has to be bought

**GitHub Pro, for the account that owns the repository.** It is the one
purchase the switch cannot do without.

- A private repository keeps its environments, and their secrets, only on a
  paid plan. GitHub's page on
  [managing environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
  says that an account on GitHub Free can configure environments for public
  repositories only, that GitHub Pro can for private ones, and that a
  repository converted from public to private on Free has its environment's
  protection rules and secrets ignored.
- The Cloudflare token and account ID are secrets of the `deploy` environment
  and are held nowhere else: `gh secret list --env deploy` names both, and
  `gh secret list` names only the Discord webhook. The environment lets only
  `main` use it (`gh api repos/<repository>/environments/deploy/deployment-branch-policies`).
- [GitHub's plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)
  lists protected branches in a private repository under Pro as well. `main`
  has no protection and no ruleset today, so nothing is lost there, but none
  could be added to a private repository on Free.

**Its price was not read.** [GitHub's pricing page](https://github.com/pricing)
listed Free, Team, and Enterprise on 2026-11-22, and not Pro. The account's
billing settings give it.

### What is free today and would be metered

A public repository's standard runners cost nothing. A private one draws on
an allowance that belongs to the account, and is shared by every private
repository the account owns. RisingRepos is private and runs its own workflow
on each pull request, so it draws on the same allowance.

| | Private, on GitHub Free | Private, on GitHub Pro |
| --- | --- | --- |
| Usage of runners included each month | $12 | $18 |
| Artifact storage included | 500 MB | 1 GB |

A standard Linux runner, which every job here uses (`ubuntu-24.04`), is $0.006
a minute, and each job is rounded up to a whole minute. Storage past the
allowance is $0.25 for a GB kept a month, counted by the hour. These are from
[billing for GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
and
[the runners' prices](https://docs.github.com/en/billing/reference/actions-runner-pricing).

**The minutes fit.** From 12 to 22 November 2026, eleven days that held the
site's redesign, this repository ran 167 workflow runs of 210 jobs. With each
job rounded up they come to 358 minutes, which is $2.15. They were counted
from each run's jobs (`gh api repos/<repository>/actions/runs/<id>/jobs`), as
the time between a job's start and its end.

| What happens | Jobs | Minutes |
| --- | --- | --- |
| A push to `main` | Build (58 to 99 seconds on 21 and 22 November), deploy (16 to 27), and the site eval (150 to 166) | 2 + 1 + 3 |
| A push to a pull request | Build, and the site eval when the pull request changes the eval | 2, or 5 |
| The daily stale check | One job of about 5 seconds | 1 |

A day with one publish and nothing else is 7 minutes, so about 210 minutes,
$1.26, in a month.

**The storage does not fit, and is the first thing to change.** On 2026-11-22
the repository held 87 artifacts that had not expired, 694 MB between them
(`gh api repos/<repository>/actions/artifacts`):

| Artifact | Kept for | How many | Size |
| --- | --- | --- | --- |
| `site`, the built pages, from each build | 7 days | 27 | 201 MB. Each one since the redesign is 14.9 MB |
| `site-eval`, each eval's reports and logs | 90 days | 60 | 493 MB, 8.2 MB each on average |

That is already past Free's 500 MB. At one deploy a day the evals alone come
to about 740 MB (8.2 MB for each of 90 days) and the pages to about 105 MB
(14.9 MB for each of 7), so about 845 MB, which leaves little of Pro's 1 GB,
and every merged feature and every pull request adds to it. `retention-days: 90` in
`.github/workflows/site-eval.yml` is the line to shorten: at 30 days the same
day's rate keeps about 350 MB.

### What a plan for one person does not buy

- **Secret scanning and push protection.** Both are on for this repository
  today (`gh api repos/<repository> --jq .security_and_analysis`). GitHub's
  page [about secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning)
  lists it for public repositories, at no cost; for private repositories that
  an organisation owns, with GitHub Secret Protection on Team or Enterprise
  Cloud; and for repositories a person owns only on Enterprise Cloud with
  managed users. So on Free and on Pro alike, both stop on the day this
  repository goes private. `tests/test_tokens.py`, and the same search run
  before a commit, would then be the only checks for a credential. Keeping
  GitHub's own means moving the repository to an organisation, which changes
  its address and is a larger change than this file covers.
- **Rulesets.** The pricing page gives them to Free for public repositories
  only, and to Team and Enterprise. It does not name Pro.

## Where it breaks

Three things stop on the day of the switch. Two of them stop on any plan.

| Where | What happens | What it needs |
| --- | --- | --- |
| The deploy job's upload, "Upload to Cloudflare Pages" in `.github/workflows/deploy.yml`. **On Free only** | The job names `environment: deploy`, and GitHub ignores that environment's secrets, so wrangler has no Cloudflare credential. Nothing is uploaded, and risingrepos.com keeps the pages it had, with no new board day | GitHub Pro, bought before the switch |
| The deploy job's "Upload only the newest push". **On any plan** | It reads the head of `main` with `git ls-remote` and no credential. The job has `permissions: {}` and checks out nothing, which works only because anyone can read a public repository. In a private one the read fails, and the step's own comment says what follows: the job fails, and nothing is uploaded | A credential that can read the repository: `contents: read` on the job, and the job's token handed to that one git call |
| The site eval's `head_of_main`, in `evals/site/measure.py`. **On any plan** | The same read, with no credential. The job has `contents: read`, but its checkout sets `persist-credentials: false`, so git holds no token. The eval raises "the head of main could not be read" and fails after every deploy (`tests/test_site_eval.py` shows that a head that cannot be read fails it) | The job's token in the Measure step's environment, and `head_of_main` handing it to git |

**What the two reads give up.** The deploy job holds the Cloudflare token, and
today it holds nothing that can reach GitHub. Once the repository is private
it also holds a token that can read the repository. It still checks out
nothing and runs nothing from the repository's files. The eval's job already
reads the whole repository through its checkout, so a token that can read it
adds little there.

**What the tests hold, and so what changes with the two reads.**

- `tests/test_workflow.py` holds the deploy job to `permissions: {}`, in the
  test of where the Cloudflare credential comes from, and holds the whole text
  of the "Upload only the newest push" script.
- `tests/test_site_eval_workflow.py` fails a workflow whose text holds the
  word `secrets`, and fails a step whose script holds a `${{` expression. So
  the token reaches the eval through the step's `env`, and is written as
  `github.token`.
- README.md, "The workflow", says what each job can reach, and under "Pushes
  close together" that the read needs no credential.

A token does no harm to a read of a public repository, so one pull request can
make both reads work before the switch and after it. That has not been tried.

**A way round Pro that is not taken.** The two Cloudflare secrets could move
from the environment to the repository's own secrets. The rule that GitHub
gives them only to `main` goes with the environment, and README.md, "The
workflow", and `tests/test_workflow.py` rest on that rule.

## What does not break

Each of these was read, and none was run against a private repository.

- **The upload itself.** Wrangler uploads the built files directly. The Pages
  project has no connection to git (RUNBOOK.md, "Where things stand").
- **The build job, and the eval's checkout.** `actions/checkout` uses the
  job's own token, which `contents: read` lets read a private repository.
- **The stale check.** It has `permissions: {}`, checks out nothing, and reads
  the live page.
- **The daily publish.** RisingRepos: `src/risingrepos/publishing/site.py`
  hands its own token to every git call it makes, a clone and a fetch as well
  as a push, and reads the live page back, not the repository. That token is
  made for this repository alone, with write access to its contents
  (RisingRepos: `scripts/run_limits/tokens.sh`).
- **An unattended run's token.** It is made for the two repositories by name,
  in the same script, and its check of write access does not depend on the
  repository being public.
- **The pages.** No page links to this repository: a search of `sitebuild/`
  finds its name nowhere, and the only links to github.com are the listed
  repositories' own.

Links to a workflow run, in `evals/site/accepted.json`, in
`evals/site/README.md`, and in the stale check's message on Discord, would
then open only for an account that can see the repository.

## What is lost for good

- **Its stars and watchers.** GitHub's page on
  [setting a repository's visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
  says they are erased. On 2026-11-22 that was one star, no watcher, and no
  fork.
- **Nothing already pushed is taken back.** Any copy made while the repository
  was public stays where it is. A credential that reached its history is still
  one that leaked.

## The order

1. **The user moves the account to GitHub Pro.** First, because of what
   GitHub's page says happens to an environment's secrets on Free.
2. **One pull request here** gives the two reads a credential, changes the
   tests and README.md with them, and shortens the eval artifact's retention.
   It works while the repository is public, so it is merged, deployed, and
   watched through a deploy and an eval before the switch.
3. **Check each credential held outside the two repositories.** Whatever files
   the `site-idea` issues here signs in with a token this file has not seen.
4. **The user changes the visibility**, in the repository's settings or with
   the command below. It is the user's step: RisingRepos: `expectations.md`
   lists a repository's visibility under "What waits for the user", and its
   run limits block an agent that tries a repository's settings.

   ```sh
   gh repo edit AndrewGodlewsky/rising-repos-site --visibility private --accept-visibility-change-consequences
   ```

5. **Check, the same day:**
   - `gh secret list --env deploy --repo AndrewGodlewsky/rising-repos-site`
     still names both Cloudflare secrets.
   - A run of "Build and deploy" for a push to `main` uploads, and the site
     eval that follows it measures.
   - The next daily publish lands on `main` and reads its board day back from
     the site.
   - The next stale check reads the site.
   - `gh api repos/AndrewGodlewsky/rising-repos-site --jq .security_and_analysis`
     says what became of secret scanning.
   - After a week, the account's billing page gives the minutes and the
     storage used.
6. **Pull requests to both repositories** change what says the repository is
   public (below).

**Going back** is the same command with `--visibility public`. It restores the
free minutes and the secret scanning, and not the star. The change of step 2
can stay.

## What says the repository is public

Here, at `4665ccb`:

- AGENTS.md, under "What a push does", that a push is public at once, and
  under "The project this repository serves", what may be written here
  because of it.
- README.md, under "The workflow", that the read of `main` needs no
  credential, and under "The stale check", GitHub's rule on the schedule of a
  public repository that has gone 60 days without activity.
  [GitHub's page](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)
  words that rule for a public repository and does not say what holds for a
  private one.
- The comment on "Upload only the newest push" in
  `.github/workflows/deploy.yml`, the docstring of `head_of_main` in
  `evals/site/measure.py`, and the docstring of `tests/test_tokens.py`.

In RisingRepos, at `5514d8f`:

- `intent.md` and `architecture.md`, which state it.
- `docs/agents/git-workflow.md`, "Work in the site repository": what may be
  written here, and that each commit is read before it is pushed.
- `docs/agents/secrets.md`, `expectations.md`,
  `docs/adr/0009-the-rebuilt-site-is-developed-on-the-site-repositorys-main-and-shown-on-a-preview.md`,
  and `src/risingrepos/publishing/contract/README.md`, each in passing.
- `scripts/run_limits/README.md` and `scripts/run_limits/tokens.sh`, where
  they say why a token's write access is checked by a write.

The rules on what may be written here were made because the repository is
public. Whether they are loosened once it is private is the user's to decide
then: they are part of the agents' instructions in RisingRepos, and a change
to those needs the user's approval.

## Not checked

- GitHub Pro's price.
- Whether the deploy job is refused outright or runs with empty secrets once
  the environment's secrets are ignored. In neither case does wrangler get a
  credential.
- That `git ls-remote` reads a private repository's `main` with a job's token.
  It is how the token is meant to be used, and it was not run.
- Whether a public repository's artifact storage is counted against anything
  today. The pages read say only that its runners are free.
- Whether GitHub stops the workflows or sends a bill when an allowance runs
  out. That depends on the account's payment method and its budget.
- Pro's storage. The billing page's table gives 1 GB of artifact storage, and
  the plans page 2 GB of GitHub Packages storage, which the billing page says
  share one allowance.
- Whether rulesets, or push protection of any kind, reach a private repository
  on Pro.
- The usage of the account's other private repositories, which share the
  allowance. The billing API was not read: it needs a scope that the login
  used here does not have.
- The token of whatever files the `site-idea` issues.
