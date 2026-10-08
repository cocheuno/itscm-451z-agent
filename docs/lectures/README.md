# Lectures

One file per session, written as a complete walkthrough: why the session exists and where it sits in the
three course threads (capability ladder, version management, analytics), the words the student needs, the
checks to run before starting, every step with the command, its expected output and what to do when it
fails, the deliverable, and check questions. The handouts in `docs/exercises/` are the checklist and rubric
for the same session; the lecture is the explanation.

Start with [Getting started](00-getting-started.md): the terminal, Python, git from zero, and the routine
for each module. The student's work stays on their laptop, one branch per module, written up in
`docs/journal/`; the instructor's changes arrive with `git pull`.

| Date | Module | Lecture | Handout |
|---|---|---|---|
| before Module 2 | 0 | [Getting started](00-getting-started.md) | — |
| 2026-09-15 | 2 | [Make the program see the data (Rung 0)](02-rung0-closeout.md) | [handout](../exercises/2026-09-15-rung0-closeout.md) |
| 2026-09-17 | 3 | [SLAs, the first real classifier, and ground truth](03-sla-rung1-eval-prs.md) | [handout](../exercises/2026-09-17-first-classifier.md) |
| 2026-09-22 | 4 | [A second model, an LLM as a classifier, and the bake-off](04a-gbm-and-llm-classifiers.md) | (steps are in the lecture) |
| 2026-09-24 | 4 | [The build review, the memo, and Rung 1 done (A1 due)](04b-bakeoff-memo-v0.1.md) | (steps are in the lecture) |
| 2026-09-29 | 5 | [Service requests, tool schemas, and read-only tools](05a-service-requests-and-read-tools.md) | (steps are in the lecture) |
| 2026-10-01 | 5 | [The Model Context Protocol](05b-mcp.md) | (steps are in the lecture) |

Instructor-facing: [implementation notes](implementation-notes.md), what is scaffolded, what the student writes, how to verify, and what is still open, per module.
