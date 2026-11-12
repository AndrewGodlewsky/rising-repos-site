# rising-repos-site

The pages of [risingrepos.com](https://risingrepos.com), which lists the GitHub
repositories gaining stars faster than their own pace predicts. The RisingRepos
project works out which repositories those are and commits the data here. This
repository holds the pages: their templates, the generator that builds them,
and the workflow that uploads them to Cloudflare Pages.

## The rebuild and the preview

The site is being rebuilt, on this repository's `main`. Until it goes live, two
addresses serve two different sites:

| Address | Serves | Source |
| --- | --- | --- |
| <https://risingrepos.com> | The earlier site, from its Cloudflare deployment of 2026-10-16. No push to this repository changes it | The tag `legacy-site` |
| <https://preview.risingrepos.pages.dev> | The rebuilt site, uploaded on every push to `main` | `main` |

- Each push to `main` is uploaded to the Cloudflare Pages branch `preview`. The
  project's production branch is `main`, so the upload is a preview deployment.
- Every page built for the preview carries
  `<meta name="robots" content="noindex">`.
- Going live is one reviewed change to `.github/workflows/deploy.yml`:
  `PAGES_BRANCH: preview` becomes `PAGES_BRANCH: main`. The same line drops the
  `noindex` tag.

## The workflow

`.github/workflows/deploy.yml` has two jobs. The daily data push can change any
file in this repository except a workflow, so nothing it can change runs in the
job that holds the Cloudflare credential.

| Job | Runs on | What it does | What it can reach |
| --- | --- | --- | --- |
| `build` | Every pull request, and every push to `main` | Checks out the repository, installs what `uv.lock` pins, runs the tests, builds the pages into `dist`, and uploads them as the artifact `site` | Read access to the repository. No secret |
| `deploy` | A push to `main`, once `build` has passed | Downloads the artifact, refuses it if it holds a `_worker.js`, and uploads it with wrangler | The `deploy` environment's `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, which GitHub gives only to `main`. It never checks out the repository, so it runs nothing from its files |

The deploy job runs wrangler with
`npm exec --ignore-scripts --before=<date> --package=wrangler@<version>`. The
version is pinned in the workflow, npm resolves every package that wrangler
pulls in as the registry stood on that date, and no package's install script
runs. Node is the runner image's own. Every action in the workflow is pinned to
a full commit SHA. `tests/test_workflow.py` checks each of these.

A pull request builds and does not deploy.

## Building locally

You need [uv](https://docs.astral.sh/uv/).

```sh
uv sync --locked                                     # the pinned dependencies, into .venv
uv run --locked python -m unittest discover -s tests
uv run --locked python -m sitebuild dist --noindex   # the pages, as the preview gets them
python -m http.server 8000 --directory dist          # then open http://localhost:8000/
```

The generator refuses a folder that already holds files, so remove `dist`
before building again.

## Layout

```text
sitebuild/          the generator: python -m sitebuild <folder> [--noindex]
  templates/        Jinja2 templates, with autoescaping on for every one
tests/              the tests
.github/workflows/  deploy.yml: the build job and the deploy job
pyproject.toml      the dependencies, and the date uv resolves them as of
uv.lock             every package, pinned with its hashes
.python-version     3.14, for local builds. CI uses the exact version in deploy.yml
```

## Changing a pinned version

Each download is checked before it is used, under the RisingRepos project's
rule: no known vulnerability on [osv.dev](https://osv.dev), and published at
least 14 days earlier.

- **Python packages.** Move `exclude-newer` in `pyproject.toml` forward, run
  `uv lock`, and check `uv.lock` with RisingRepos's
  `scripts/run_limits/check_downloads.py` before running `uv sync`.
- **wrangler.** In an empty folder, run
  `npm install --package-lock-only --ignore-scripts --before=<date> wrangler@<version>`,
  which writes a `package-lock.json` and installs nothing. Check that file the
  same way, then change the version and `--before` together in `deploy.yml`.
- **An action, uv, or Python.** Take a release at least 14 days old, look it
  up on osv.dev, and pin an action to the commit its release tag points at.
