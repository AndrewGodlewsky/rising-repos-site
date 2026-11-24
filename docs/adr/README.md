# Decision records

Each file here records one decision about the site: what was decided, and why.
A record is a soft guard. It does not stop a change, as a failing test does.
It tells whoever plans a change what is already settled, so that a feature
does not reopen a decision by accident.

## Before a change that goes against a record

Stop, and ask the owner. A decision is reopened by the owner, in a new
record, and never by building against the old one.

## When to write one

When all three of these hold:

1. **It is hard to undo.** Changing it later would cost real work.
2. **It would surprise a newcomer.** Someone reading the code would wonder why
   it was done this way, or would assume the opposite.
3. **It gave something up.** There was another way, and this one was chosen
   for a reason.

A rule that holds for every change belongs in [STANDARDS.md](../../STANDARDS.md),
and a fact about how a part works belongs in [README.md](../../README.md).

## The form

- **A title** that states the decision, and one paragraph under it: what the
  situation was, what was decided, and why.
- **`## Status`**: when it was accepted and where it was decided, by the
  number of an issue or of a record. It says in its own words what was
  decided there, and quotes nobody. A decision that an agent reached by
  itself says so. A decision that is accepted but not yet carried out says
  "Not yet in force", and what holds until it is.
- **`## Considered options`** and **`## Consequences`**, only where they would
  not be guessed.
- **`## Confirmed by`**: the tests that would fail if the decision were
  undone, each written `tests/<file>.py::<Class>::<test>`. A decision that no
  test can hold says "No check holds this."
- **`## Reopen when`**, only where a condition was recorded with the
  decision.

Numbers run in order and are never used twice. A record that a later one
replaces stays, and its status names the record that replaced it.

`tests/test_context.py` holds the numbering, and holds each test a record
names to the tests.
