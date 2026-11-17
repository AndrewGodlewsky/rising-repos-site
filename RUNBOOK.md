# Going live, and going back

How risingrepos.com was moved from the earlier site to the one this
repository's `main` builds, and how it is moved back. The runbook was written
for [RisingRepos#57](https://github.com/AndrewGodlewsky/RisingRepos/issues/57).
The switch was made under
[RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58),
which followed it step by step. That issue holds the day and time of the
switch, the result of every check before and after it, and each reading taken
from Cloudflare's dashboard; this file holds none of them.

Each fact below says how it was found and on which day. A fact can change
between the day it was read and the day it is relied on, so whoever goes back
reads each one again first.

## Who does what

The RisingRepos project can leave an agent working alone for a while, in what
it calls an unattended run. A step can have a different owner inside such a run
than outside one, so each step below names both.

| Part | During an unattended run | Outside one |
| --- | --- | --- |
| The checks before the switch, and after it | The agent | The user, or an agent the user asks |
| The switch | The agent. The user handed it this decision for the length of a run ([RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58)) | The user: they say when the site is ready, and they approve the pull requests |
| A step in Cloudflare's dashboard, or one that turns this repository's deploy workflow off or on | The user | The user |
| Going back | The user decides it and makes its dashboard steps. An agent never begins it on its own | The same |

Agents keep out of Cloudflare's dashboard because the project's rules give
every step there to the user, as the table says; nothing technical has been
shown to stop one. The one Cloudflare token an agent holds was created to read
the Pages project and nothing more, and no write has been tried with it. The
token that uploads is a secret of this repository's `deploy` environment, which
only the deploy job reads.

## Where things stand

These facts were read before the switch, on 2026-11-12 and again on
2026-11-16, at the UTC times given, and describe the arrangement that going
back returns to. "The API" means Cloudflare's API, read with GET requests and
the token that can only read. What the same facts were on the day of the
switch, and what they became after it, is on
[RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58).

| Fact | What was found | How it was found |
| --- | --- | --- |
| The Pages project | `risingrepos`, created on 2026-08-07. It takes direct uploads and has no connection to git | The API, the project, 2026-11-12 at 22:21, and again on 2026-11-16 at 06:44 |
| Its production branch | `main`. An upload under any other branch name, `preview` included, makes a preview deployment | The API, the project, at the same two times |
| The deployment that served risingrepos.com before the switch | The production deployment uploaded on 2026-10-16 at 18:38:52, from commit `4b5d97e`, which the tag `legacy-site` points at. It was the project's canonical deployment, its stage was `deploy: success`, and it was the only one holding the aliases risingrepos.com and www.risingrepos.com | The API, the project and its production deployments, 2026-11-12 at 22:21 and 22:22, and 2026-11-16 at 06:44. The tag, with `git rev-parse legacy-site^{commit}` in this repository |
| Earlier production deployments | 43, of 44 production deployments in all, on both days. The nine just before the live one, from 2026-09-24 to 2026-10-09, were each uploaded from `main` and each has the stage `deploy: success` | The API, the production deployments, 2026-11-12 at 22:21, and the count again on 2026-11-16 at 06:44 |
| Preview deployments | 30 on 2026-11-16, one more after each push to `main`. The newest, uploaded on 2026-11-15 at 23:31:34, held the alias `preview.risingrepos.pages.dev` | The API, the preview deployments, 2026-11-16 at 06:44 |
| The addresses the project answers on | `risingrepos.pages.dev`, and two custom domains, `risingrepos.com` and `www.risingrepos.com`, both `active` | The API, the project's domains, 2026-11-12 at 22:22. The same three names on 2026-11-16 at 06:44 |
| How `www` is served | Like the bare domain, from the same deployment: `https://www.risingrepos.com/` answers 200 with the same page, and is not redirected. `http://` on either name answers 301, to the same name over `https://` | `curl -sI` on the four addresses, 2026-11-12 at 22:21 and 2026-11-16 at 06:58 |
| What risingrepos.com states | `rr:board-date` 2026-10-16 and `rr:build-ts` 2026-10-16T18:38:34+00:00, and no `rr:published-at` | `curl -s`, three times on 2026-11-12 at 22:21, and once on 2026-11-16 at 06:58 |
| An address the earlier site holds no page for | 200, with the earlier site's front page | `curl` on `/archive/` and `/no-such-page/` of risingrepos.com, 2026-11-12 at 22:25 and 2026-11-16 at 06:58 |
| The same addresses on the preview | 404, with this site's not-found page | The same, 2026-11-12 at 22:25, and `/no-such-page/` on 2026-11-16 at 06:58 |
| The preview's `noindex` mark | Two parts. Cloudflare adds the header `x-robots-tag: noindex` to an answer from a preview address, and the build puts `<meta name="robots" content="noindex">` in each page of an upload that is not production | `curl -sI` and `curl -s` on the preview, 2026-11-12 at 22:21 and 2026-11-16 at 06:58 |
| Always Online | **Unknown.** The switch belongs to the zone `risingrepos.com`, which is out of the read-only token's sight | The API: `GET /zones?name=risingrepos.com` came back with an empty list, 2026-11-12 at 22:22. Only the dashboard shows it, so check 2 before the switch asks for it |
| The rollback action in the dashboard | **Unknown.** The API answers about deployments, and nothing about the dashboard's menus | Not read: only the dashboard shows it. Check 3 before the switch asks for it |

**A reading of the live page that can be compared.** Cloudflare adds a script to
each answer, and one line of it is different every time, so two fetches of the
whole page never have the same hash. Leaving that line out gives a hash that
holds from one request to the next:

```sh
curl --silent https://risingrepos.com/ | grep --invert-match '__CF$cv$params' | sha256sum
```

On 2026-11-12 at 22:21 UTC, three fetches of risingrepos.com and one of
www.risingrepos.com each gave
`ef2c4506a5466ed57935273e0d5b830f37b75d2d139ce0cfcaca97d17ce16c95`, which is
also what [RisingRepos#38](https://github.com/AndrewGodlewsky/RisingRepos/issues/38)
read that morning. Fetched the same way on 2026-11-16 at 06:58 UTC, three
times from risingrepos.com and once from www.risingrepos.com, the earlier site
gave the same hash each time. That is the hash a rollback is checked against.

## What Cloudflare's documentation says

Nothing in this section has been tried on this project. It was read on
2026-11-12.

- [Rollbacks](https://developers.cloudflare.com/pages/configuration/rollbacks/):
  a rollback makes an earlier production deployment the live one, at once.
  Any production deployment that built successfully can be chosen. A preview
  deployment cannot. In the dashboard the action is in the project's
  **Deployments**, under **All deployments**, in the three-dot menu of the
  deployment to go back to: **Rollback to this deployment**, and then a
  confirmation. Nothing on the page speaks of Direct Upload projects, the
  kind this project is.
- [The API's rollback call](https://developers.cloudflare.com/api/resources/pages/subresources/projects/subresources/deployments/methods/rollback/):
  a `POST` to the deployment's `rollback` address, which needs the permission
  `Pages Write`. The token that can only read lacks it, so the call has never
  been made.
- [Preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/#preview-indexing-by-search-engines)
  and [Serving Pages](https://developers.cloudflare.com/pages/configuration/serving-pages/#headers):
  Pages adds `X-Robots-Tag: noindex` to every answer from a preview address,
  and to no other.
- [Asset retention](https://developers.cloudflare.com/pages/configuration/serving-pages/#asset-retention):
  a data center may keep handing out a file it cached for as long as seven
  days after a newer deployment. The preview showed this: a page that the
  newest deployment had dropped was still served by the data centers that had
  cached it, and only at that one address
  ([RisingRepos#71](https://github.com/AndrewGodlewsky/RisingRepos/issues/71)).
- [Always Online](https://developers.cloudflare.com/cache/how-to/always-online/):
  a switch on the zone's **Caching**, **Configuration** page. While it is on and
  Cloudflare cannot reach the site, Cloudflare can answer with a copy kept by
  the Internet Archive.

**Not in the documentation, and so the agent's reading.** After a rollback, the
next upload under the production branch becomes the live deployment again: in
the API's answer of 2026-11-12, the newest production deployment is the
canonical one. So going back stops the uploads to production before it rolls
back.

## Why the rollback has not been rehearsed

Rolling back swaps which production deployment answers at risingrepos.com, and
a preview can never be the one swapped in. A practice run would therefore
alter the live site while it ran. The only other way to practise is a second
Pages project, which is a change to the Cloudflare account and the user's to
make. The agent's token can only read, so it could do neither.

So whether the way back is open can only be seen once the switch has left an
earlier production deployment behind it. Seeing it is the first step after
the switch: step 1 under "After the switch".

## The lines the switch changes

The switch edited these lines and nothing else that decides an address, and
every row now stands on its "After go-live" side. Going back moves each of
them to its other side. `tests/test_runbook.py` holds the table to the files:
each file holds one side of its row, once, every row is on the same side, and
every line of a workflow or of the eval's code that names either address, or
sets the Pages branch, is a row here.

| File | Before go-live | After go-live |
| --- | --- | --- |
| `.github/workflows/deploy.yml` | `PAGES_BRANCH: preview` | `PAGES_BRANCH: main` |
| `.github/workflows/stale-check.yml` | `default: https://preview.risingrepos.pages.dev/` | `default: https://risingrepos.com/` |
| `.github/workflows/stale-check.yml` | `DEFAULT_ADDRESS: https://preview.risingrepos.pages.dev/` | `DEFAULT_ADDRESS: https://risingrepos.com/` |
| `.github/workflows/site-eval.yml` | `default: https://preview.risingrepos.pages.dev/` | `default: https://risingrepos.com/` |
| `evals/site/measure.py` | `DEPLOYED_SITE = "https://preview.risingrepos.pages.dev"` | `DEPLOYED_SITE = "https://risingrepos.com"` |
| `evals/site/accepted.json` | `"base": "https://preview.risingrepos.pages.dev",` | `"base": "https://risingrepos.com",` |

What each one does:

- **`PAGES_BRANCH`** names the Pages branch of every upload. Set to `main`, an
  upload is a production deployment, and the build leaves the `noindex` tag
  out of the pages. The header goes with it, because risingrepos.com is not a
  preview address. So this one line removes both parts of the mark. Set to
  `preview`, it puts both back on whatever is uploaded next.
- **The stale check's two lines** are the address a run started by hand reads
  by default, and the address the daily scheduled run reads. Left on the
  preview, which stopped changing once uploads went to production, the check
  would post a false alarm every day.
- **The site eval's two lines** are the address a run by hand measures by
  default, and the address it measures after each deploy. Left on the preview,
  the measurement after each deploy would keep looking for a board day that
  never appears there, and fail.
- **`accepted.json`'s `base`** is held to the address in `measure.py` by
  `tests/test_site_eval.py`, so the two move together. Its numbers were
  measured on the preview, and the limits in `evals/site/limits.json` were set
  there ([RisingRepos#74](https://github.com/AndrewGodlewsky/RisingRepos/issues/74)).
  The first runs on the live address are judged against them, and
  [RisingRepos#113](https://github.com/AndrewGodlewsky/RisingRepos/issues/113)
  replaces the numbers from a run there, in a pull request of its own.

The tests that hold these lines moved with them, in the same pull request, and
move back with them: `tests/test_workflow.py`, `tests/test_stale_check.py`,
`tests/test_site_eval_workflow.py`, and `tests/test_site_eval.py`. So did the
words around them: the comments over `PAGES_BRANCH` and `DEFAULT_ADDRESS`,
which are rewritten with the lines under them; `measure.py`'s docstrings and
the words of the eval's summary; `evals/site/README.md`; and this repository's
`README.md`, under "The live site and the preview" and "The stale check".

**In the RisingRepos repository**, in a pull request of its own, which merges
after this repository's:

- A publish to the site reads the site's page back after it pushes, and the
  address it reads is the setting `RISINGREPOS_SITE_ADDRESS`. Its default, in
  `src/risingrepos/config.py`, was the preview before go-live and is
  `https://risingrepos.com/` after it. The scheduled task that publishes each
  day does not set the variable (see check 6), so the default is what it
  reads: the switch reaches it once the copy of RisingRepos that the task runs
  holds the change, and the task is not registered again. The default is held
  by `tests/test_config.py` and `tests/test_cli.py`, and given in `README.md`
  and `.env.example`, which change with it.
- Where the data goes does not change: a publish still pushes to this
  repository's `main`.
- Its documents that described the preview as the place the rebuilt site is
  shown say that the rebuilt site is live, in the same pull request.

## What was built after this runbook was written

When this runbook was first written, on 2026-11-12, four parts of RisingRepos
did not exist: the daily job
([RisingRepos#51](https://github.com/AndrewGodlewsky/RisingRepos/issues/51),
[#52](https://github.com/AndrewGodlewsky/RisingRepos/issues/52), and
[#53](https://github.com/AndrewGodlewsky/RisingRepos/issues/53)), the database's
backup ([RisingRepos#6](https://github.com/AndrewGodlewsky/RisingRepos/issues/6)),
the daily job's alarms
([RisingRepos#54](https://github.com/AndrewGodlewsky/RisingRepos/issues/54)),
and the site's own notice of an old board
([RisingRepos#56](https://github.com/AndrewGodlewsky/RisingRepos/issues/56)).
All four were built before the switch. Check 6 compared each of them with this
runbook on 2026-11-16, and
[RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58)
lists every place it looked at. What each turned out to need:

- **The daily job** publishes with the read-back above, and needs the address
  change and nothing else. Its scheduled task hands the job only the settings
  it was registered with, and `RISINGREPOS_SITE_ADDRESS` is not one of them,
  so the job reads back whatever address the default in its own copy of
  RisingRepos names.
- **The backup** copies the database and names no address of the site.
- **The alarms** name no address of the site either. One of them bears on the
  timing of the switch: a read-back that fails fails the day's publish, and
  the daily job then raises `failed at publish` (check 7).
- **The notice** is part of this repository's pages, reads only what its own
  page states, and names no address, so it moved with the pages.

None of the four adds a row to "The lines the switch changes".

## Before the switch

Each check is made on the day of the switch, and its result is recorded on
[RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58).
A check that fails stops the switch until the fault is put right or the user
decides.

1. **Read the Pages project again.**
   Who: the agent, in a run; outside one, an agent the user asks.
   Through the API, read the production branch, the canonical deployment, and
   the production deployments. It passes when the production branch is `main`,
   and the deployment that holds the aliases risingrepos.com and
   www.risingrepos.com is a successful production deployment. Record that
   deployment's date and commit: it is the one a rollback goes back to. If the
   production branch is not `main`, stop: an upload under `main` would then be
   a preview, and the arrangement that ADR 0009 in RisingRepos describes has to
   be looked at again first.
2. **Read Always Online.**
   Who: the user, in a run or out of one, because it is in the dashboard.
   Open the dashboard at the zone `risingrepos.com` › **Caching** ›
   **Configuration**, and look at **Always Online**. It passes when the switch
   is off. When it is on, the user turns it off or says that it stays
   on, and the answer is recorded.
3. **Look for the rollback action on an earlier production deployment.**
   Who: the user, in a run or out of one.
   In the dashboard, go to **Workers & Pages** › `risingrepos` ›
   **Deployments** › **All deployments**. Pick an older production
   deployment, for instance the upload of 2026-10-09, and open its three-dot
   menu. It passes when the menu has **Rollback to this deployment**. Leave
   that item alone: once confirmed, it changes risingrepos.com.
   When the action is not there, the way back is unknown, and the switch waits
   for the user.
4. **Read how risingrepos.com answers.**
   Who: the agent, in a run; outside one, the user or an agent they ask.
   Record `curl -sI` on `https://risingrepos.com/`, `https://www.risingrepos.com/`,
   and both `http://` addresses, the page's `rr:board-date`, and the hash
   above. A rollback is checked against these readings.
5. **Confirm that the preview shows what goes live.**
   Who: the agent, in a run; outside one, the user or an agent they ask.
   The preview's `rr:board-date` and `rr:published-at` are those of the newest
   board day in `site-data/boards/index.json` on `main`, the last run of
   **Build and deploy** on `main` passed, and the site eval's last run after a
   deploy passed, or its numbers were accepted.
6. **Compare this runbook with what has been built since.**
   Who: the agent, in a run; outside one, an agent the user asks.
   For the daily job, its install, the backup, and the alarms (see "What was
   built after this runbook was written"), find every place that names an
   address of the site, and add each to "The lines the switch changes". Run
   this repository's tests on `main`: `tests/test_runbook.py` shows the table
   still matches the files.
7. **Choose a time when no publish runs.**
   Who: whoever makes the switch.
   No publish is running, and none is due before both pull requests below are
   merged. A publish whose read-back address is on the other side of the switch
   from the site fails its read-back, though its data still reaches the site,
   and the daily job then raises `failed at publish`. The daily job's times are in RisingRepos's `architecture.md`, in its
   list of what runs on the machine. So both merges, and the update of the copy
   of RisingRepos that the scheduled task runs, fall between one evening's
   starts and the next.

**If check 2 or check 3 goes unanswered.** Only the user can take these two
readings, since both live in the dashboard. In a run, the agent sends its
request for them once this runbook is on `main`, and sends it again when the
switch is due; it first went out on 2026-11-12. If either reading fails, the
switch stops, like any other failed check. If all the other checks have passed
and one of the readings, or both, has not come back, the agent makes the call
alone, on the evidence open to it: check 1 has confirmed, through the API, that
the deployment to return to finished as a production deployment with no error,
and the rollback page of Cloudflare's documentation, cited above, lets any
production deployment that built cleanly be picked. On
[RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58) it
writes down which of checks 2 and 3 went unread, and the reason it switched or
held off.

## The switch

1. **Open the two pull requests.**
   Who: the agent, in a run; outside one, the user, or an agent they ask.
   In this repository: every line of the table moved to "After go-live", with
   the tests and the words that go with them. In RisingRepos: the read-back's
   address. Each is reviewed. This repository's workflows hold its secrets, so
   the review of this one includes its security.
2. **Clear them.**
   Who: in a run, the reviewers' assessment, as the project's rules for a run
   clear any merge; outside one, the user's approval.
3. **Merge this repository's pull request first.**
   Who: whoever makes the switch.
   The RisingRepos change depends on the site being live, so it waits. The
   push to `main` starts **Build and deploy**, which now uploads to
   production. Its deploy job passes. Note the time it finished.
4. **Check that the site is live, then merge the RisingRepos pull request.**
   Who: whoever makes the switch.
   Make check 2 under "After the switch" first. When it passes, merge. Then
   bring the copy of RisingRepos that the scheduled task runs up to date, as
   that pull request's description says, before the task's next start: from
   then on each publish reads back risingrepos.com.

## After the switch

Each check below is made once the switch's deploy has finished, and its
result is recorded on
[RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58).

1. **Confirm the way back is open: the deployment from before the switch can
   be chosen to roll back to.** This is the first action after the switch.
   Who: the agent reads the API, in a run or when the user asks; the user
   reads the dashboard, in both cases.
   Through the API: the deployment recorded in check 1 before the switch is
   still a successful production deployment and no longer the canonical one,
   and the upload made by the switch's merge is canonical and holds the
   aliases risingrepos.com and www.risingrepos.com. In the dashboard, as in
   check 3 before the switch, but on the deployment recorded in check 1: the
   menu has **Rollback to this deployment**, which stays unselected. In a run,
   the agent sends the user a message asking for that reading, records the
   answer on
   [RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58),
   and goes on with the checks below while it waits.
2. **risingrepos.com serves this site, without the `noindex` mark.**
   Who: the agent, in a run; outside one, the user or an agent they ask.
   `curl -sI https://risingrepos.com/` answers 200 and has no `x-robots-tag`
   line. The page holds no `<meta name="robots">`, and its `rr:board-date` and
   `rr:published-at` are those of the newest board day on `main`. The same
   holds for `https://www.risingrepos.com/`. `/no-such-page/` answers 404 with
   the not-found page.
3. **The stale check reads risingrepos.com.**
   Who: the agent, in a run; outside one, the user or an agent they ask.
   Start it by hand with no inputs, as "The stale check" in `README.md` shows.
   Its log says the board is fresh and names `https://risingrepos.com/` as the
   address it read. A run with `max_age_hours` set to `0` forces an alarm,
   which shows that the message reaches Discord with the new address. The next
   scheduled run, at 04:41 UTC, reads the same address, and its log shows it.
4. **The site eval measured the live address.**
   Who: the agent, in a run; outside one, the user or an agent they ask.
   The run that followed the switch's deploy measured
   `https://risingrepos.com/`. Each number is inside its limit, and where one
   is not, the user has looked at it and accepted it. Replacing
   `accepted.json` from that run is a pull request of its own.
5. **The next publish reads back risingrepos.com.**
   Who: the agent, in a run; outside one, the user or an agent they ask.
   The next publish's read-back confirms its board day on risingrepos.com, and
   the run of **Build and deploy** for its commit uploads under `main`.
6. **Pages of the earlier site.**
   Who: the agent, in a run; outside one, the user or an agent they ask.
   A page of the earlier site that this site lacks may still be served, at
   that one address, for as long as seven days, by the data centers that
   cached it. On the preview, the same address with a query string added,
   such as `?v=1`, answered from the newest deployment
   ([RisingRepos#71](https://github.com/AndrewGodlewsky/RisingRepos/issues/71));
   nobody has measured that on production. A week after the switch, check one
   such address again without the query string: it answers 404.

## When something looks wrong after the switch

The agent, in a run or out of one, does these three things first, in this
order:

1. **Stop.** Make no further change towards the switch in either repository,
   and start no publish.
2. **Record** on
   [RisingRepos#58](https://github.com/AndrewGodlewsky/RisingRepos/issues/58)
   what it saw: the address, the time, what the page answered (its status, its
   `rr:board-date`, and the hash above), and the run of **Build and deploy**
   that made the upload.
3. **Send the user a message** that says what is wrong, that going back is
   theirs to decide, and that the steps are under "Going back" in this file.

It then carries on with work the fault does not touch. A fault in the pages
themselves can be fixed by an ordinary reviewed change, which deploys to
production like any other. Going back is not the agent's to start.

## Going back

Going back is the user's to decide, in a run or out of one, and three of its
steps are the user's own: one is made in Cloudflare's dashboard, and two turn
this repository's deploy workflow off and on again.

1. **Stop the uploads to production.**
   Who: the user, in a run or out of one.
   In this repository on GitHub, open **Actions**, then the workflow **Build
   and deploy**, then its menu, **···**, and choose **Disable workflow**. If a
   run of it is in progress, wait for it to end. The daily data push starts
   this workflow, and a production upload made after the rollback would become
   the live deployment again.
2. **Roll back in the dashboard.**
   Who: the user, in a run or out of one.
   Go to **Workers & Pages** › `risingrepos` › **Deployments** › **All
   deployments**. Find the production deployment recorded in check 1
   before the switch: on 2026-11-12 that is the one uploaded on 2026-10-16 at
   18:38 UTC from commit `4b5d97e`. Open its three-dot menu, choose
   **Rollback to this deployment**, and confirm.
3. **Check it.**
   Who: the agent, or the user.
   risingrepos.com and www.risingrepos.com state the `rr:board-date` of check 4
   before the switch, 2026-10-16 today, and give the same hash. The stale
   check then alarms every day, and every publish's read-back fails though its
   data still reaches this repository. Both start out reading risingrepos.com,
   where the earlier site states no publish time, and each moves to the
   preview at its own point. The stale check moves when this repository's pull
   request of step 4 is merged, and goes on alarming there until step 5
   uploads to the preview again, since its last upload came before the switch.
   The read-back moves in step 5, when the copy of RisingRepos that the
   scheduled task runs is updated after that upload, so the first preview it
   reads is already current.
4. **Put the lines of the switch back.**
   Who: an agent, once the user has asked for the way back, in a run or out of
   one.
   A pull request in this repository moves every line of the table back to
   "Before go-live", and one in RisingRepos puts the read-back's address back.
   Because they undo a change that went live, the user approves each one.
   **Build and deploy** is still disabled, and a disabled workflow starts for
   nothing, pull requests included, so no `build` check runs on the one here.
   Whoever opens it runs the tests on its branch by hand and posts what they
   print on it. The RisingRepos pull request waits for step 5.
5. **Start the uploads again.**
   Who: the user, in a run or out of one.
   Once the pull request in this repository is merged, enable **Build and
   deploy** again. The next push to `main` uploads to the preview. Once that
   upload has finished, merge the RisingRepos pull request of step 4, then
   bring the copy of RisingRepos that the scheduled task runs up to date, as
   that pull request's description says, before the task's next start. The
   merge alone does not move the read-back: the task sets no address, so the
   default in its own copy decides it. From that update on, the read-back
   finds the preview current.

For as long as seven days after the rollback, a page of this site that the
earlier one lacks, such as a board day after 2026-10-16, may still be served
at that one address by the data centers that cached it.
