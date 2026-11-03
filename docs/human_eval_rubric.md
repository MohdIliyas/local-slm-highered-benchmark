# Human evaluation rubric

You will rate model outputs for two tasks: **reply drafting** (an e-mail answering a student) and **policy summarization** (three bullet points). You will not be told which model wrote anything. Do not open `results/human_eval/key/`, and do not discuss individual items with the other rater until you have both finished.

Read the source text (the student's message or the policy) first, then the output. For each item, fill in one row of your `ratings_<name>.csv`.

## Columns

**quality_1to5**: overall usefulness to the person who would send or publish it.

| Score | Meaning |
|---|---|
| 5 | Could be sent or published as is. |
| 4 | Minor polish only (wording, tone). Nothing factually wrong. |
| 3 | Usable after a real edit: something missing, unclear, or slightly off, but the structure is sound. |
| 2 | Major rewrite needed. Wrong emphasis, missing the key point, or misleading. |
| 1 | Unusable or harmful: wrong information, invented policy, or inappropriate tone. |

**needs_substantive_edit_YN**: `Y` if a staff member would have to change *content* (not just wording) before sending or publishing. This is the column that defines the Human Intervention Rate (HIR). As a rule of thumb, scores of 1–3 are usually `Y`, and 4–5 are usually `N`, but decide this column on its own.

**factual_error_YN**: `Y` if the output states something that is false or not supported by the source. This includes:

- an invented deadline, number, office name, URL, e-mail address, or phone number;
- a policy rule the source does not contain;
- a changed number. For example, the policy says 14 days and the summary says 10.

A bracketed placeholder such as `[insert office]` is **not** a factual error. It is the safe behaviour we asked for.

**notes**: optional, but please note the reason for any score of 1 or 2 and for every factual error. These notes feed the paper's error analysis.

## Calibration

Before rating, both raters independently score the first 10 items. Then compare. Discuss only the *rubric*, meaning what counts as a 3 versus a 4, and never which model you think wrote something. Then rate the rest without further discussion. The paper reports agreement on all items, including the 10 calibration items.

## Disagreements

After both of you finish, run `python scripts/score_human.py`. It reports agreement (Cohen's kappa) and lists how many items you disagree on for `needs_substantive_edit`. Dr. Smith adjudicates those items blind. He records each decision in `results/human_eval/adjudication.csv`, which has the columns `blind_id,needs_substantive_edit_YN`. Then rerun the script.
