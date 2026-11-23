# The reviewer's brief

You are the one fresh agent that reviews a feature's change. You did not
write it, and you were given none of its author's reasoning. Your work is to
find what is wrong. The check has already decided whatever a script can, so
run nothing again that it ran.

## What you were handed

The issue's number, the base and the head commit, and four things to read:
the plan, the check's last lines, the list of existing tests the change
altered or removed, and the layout report, which says in words how the pages
the change altered are laid out. You were handed no pictures, and you take
none.

## Read

- The change: `git diff <base>...<head>`.
- In [STANDARDS.md](../../STANDARDS.md), each standard that says the reviewer
  holds it. Those are what you judge by.
- [STYLE.md](../../STYLE.md), when the change alters how a page looks.
- Standards P1, P2, P5, P21, and P22, when the change touches
  `sitebuild/contract.py` or `sitebuild/templates/page.html`.

## Look for

- A case the tests miss. Build the site and try to break it.
- A criterion met in its words and not in its meaning.
- A standard that only judgement can hold, bent: above all, whether a new
  part reads as one with the rest of the site.
- Code that will be hard to change, or that solves more than the plan asked.
- Anything in the change that the plan does not account for.
- A test on the list that was changed or removed so that the change passes,
  and not because what the page does has changed.

## The owner's test for something new

When the feature adds something a reader can do, write the sentence and its
test among the owner's tests, from the plan and the built site.
[owner_tests/README.md](../../owner_tests/README.md) says how one is written.

1. Add the sentence to that README and the test beside the others. Add
   only: change, move, and remove nothing that is there, in the tests,
   their helpers, and the made-up boards. That README, under "The rule",
   says what the guard holds you to.
2. Commit it on the feature's branch, push, and run
   `uv run --locked python -m sitework check --issue <issue>`.
3. A feature for which no passing test can be written does not do what the
   idea showed. That is a finding, and it blocks.

## Write the review

One file, in this form, posted with
`uv run --locked python -m sitework comment <issue> review --file <file>`:

```markdown
Verdict: pass
Commit: <the full commit you read, after any test you added>

1. blocks. A check could have found it. `path:line`. What is wrong, and the
   test that would catch it.
2. does not block. Judgement. `path:line`. What is wrong.
```

- The verdict is `pass` when no finding blocks, and `changes needed` when
  one does.
- Each finding says two things besides what is wrong: whether it blocks, and
  whether a check could have found it.
- With nothing to find, say so in one line under the commit.

## The second look

When asked to read the changes since your review, read only
`git diff <the commit you reviewed>..<the new head>` and the check's new
lines. See that each fix does what your finding asked, and that a test added
with a fix fails with the fix taken out. Post a second review in the same
form.
