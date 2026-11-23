# The repository is public, and holds nothing private

This repository is public and RisingRepos is private. So everything written
here is published the moment it is pushed, and pushed history is never
rewritten. The owner chose on 22 November 2026 to keep it public for now:
`GOING-PRIVATE.md` records what making it private would cost, and where it
would break.

## Status

Accepted on 22 November 2026, by the owner.

## Consequences

- What is written here names a RisingRepos issue by its number, and says in
  its own words what was decided there. It quotes neither the issue nor the
  owner.
- No file, commit, pull request, review, or comment holds a path on anyone's
  machine or a personal e-mail address. A commit is made with a GitHub noreply
  address.
- Each commit is read before it is pushed, and each pull request's body, each
  review, and each comment before it is posted.
- The deploy job and the site eval each read the head of `main` with no
  credential, which works only while the repository is public.

## Confirmed by

`tests/test_tokens.py::TheRepository::test_no_file_git_would_commit_holds_a_string_shaped_like_a_credential`
holds the one part a check holds today: no file git would commit holds a
string shaped like a GitHub token or a Discord webhook address. The reviewer
holds the rest.

## Reopen when

The owner means to make the repository private in time. `GOING-PRIVATE.md`
gives the steps, in order.
