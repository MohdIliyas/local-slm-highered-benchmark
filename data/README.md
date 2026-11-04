# Data statement

## What's here

| File | Contents |
|---|---|
| `tasks/syllabi.json` | 24 syllabus excerpts. Each item has a gold label for course code, instructor, grading weights, and whether an accommodation statement is present (16 have one, 8 don't). |
| `tasks/policies.json` | 16 university policies, each with the list of constraints a summary must keep and a three-bullet reference summary. |
| `tasks/tickets.json` | 64 helpdesk tickets, 8 for each of 8 categories. 16 of them (`use_for_drafting: true`) are also used for reply drafting. |
| `syllabi/schema.json` | JSON Schema the extraction output must satisfy. |

The files under `emails/`, `policies/` and `syllabi/` other than `schema.json` are leftovers from the pilot. The benchmark does not use them.

## Provenance

All items are **synthetic**. They were written for this study, with AI assistance, and reviewed by the authors. They imitate the vocabulary, length, and format variety of real university material, but they don't come from any real student, course, or institution. Instructor names are invented, and course codes are generic. Because no real records are involved, the data can be public.

## Design choices that matter for scoring

**No ticket contains its own category name.** The earlier corpus did contain them ("Support request #1 regarding lms access"), which made classification trivial.

**Syllabi vary on purpose.** They use percentages, the word "percent", point totals that have to be converted, dot-leader tables, and distractor names such as a lab coordinator. The scorer accepts grading weights either itemized ("Exam 1 15%, Exam 2 15%") or merged ("Exams 30%").

**Policy constraints are matched as whole phrases** after number words are normalized, so "five business days" matches `5 business days` but "15 business days" does not. A constraint may list alternative forms, for example `["grade of W", "a W"]`.

## Before final scoring

The `reference_summary` entries in `policies.json` are drafts (`reference_status`). An author must approve or rewrite each one before ROUGE and BERTScore are reported. If you change them, set `reference_status` to `"approved"` and rerun `scripts/score.py`.

## Changes made after inspecting model outputs

**POL-07 (Incomplete grades).** The constraint "automatically converts to an F" now also accepts "automatically convert to an F" and "automatically become(s) an F". On the first full run, correct summaries that wrote "will automatically convert to an F" were scored as having dropped the constraint. Only the verb form was added; no constraint was removed or loosened in meaning. This is disclosed in the paper's method section.
