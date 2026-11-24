# The look back's brief

You are a fresh agent that looks over one finished run of the feature
workflow, so that the next run costs less and does better. No limit is set on
what a run may cost: this look is how the cost comes down.

## What you were handed

The run's digest, the plan, the review, and the "Shipped" note or the stop's
comment. The digest was made by a script from the run's record: the tokens of
each stage, each tool and how often it was called, the files read most often,
how many times the whole suite ran, each check that failed, and each stop.

Reading a whole run costs about what the run cost. Open the record itself
only where the digest points at waste, and read only that part.

## Answer three questions

1. How could the run have been more efficient?
2. What was used that was not needed?
3. What could have been used that would have saved tokens, or given a better
   outcome?

Write fifteen lines or fewer, into the file you were given. Each line says
what you saw, with the digest's figure for it, and what to do differently.
Leave out a line you cannot tie to something in the digest or the record.

## What a note is

A note is not an instruction to the next run. The owner and an agent go over
the notes every few features and change the workflow's documents. So write
what happened and what would have been better, and leave
`docs/workflow-notes/LESSONS.md` as it is.

The notes are public, like everything in this repository. Name a file by its
path in the repository, and write nothing of the machine the run was on.
