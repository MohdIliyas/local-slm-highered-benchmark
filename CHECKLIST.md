# Path to submission

Work through this in order. Each step lists who does it.

## 1. Run the experiments
- [ ] **Mohammed:** on the i7, run `python tests/test_pipeline.py`, then the `smoke`, `main`, and `temperature` presets, then `score.py`. See the README.
- [ ] **Karthik:** do the same on the M2 Max, following `docs/mac_benchmarking_instructions.md`.
- [ ] Check `results/<machine>/per_item.csv` for anything odd: empty outputs, `truncated = True`, or errors.

## 2. Approve the reference summaries
- [ ] **Mohammed or Dr. Smith:** read each `reference_summary` in `data/tasks/policies.json`, then edit it or approve it and set `reference_status` to `"approved"`. Rerun `score.py`.

## 3. Human evaluation
- [ ] **Mohammed:** `python scripts/make_blind_queue.py --machine intel_i7 --raters mohammed karthik`
- [ ] **Both raters:** calibrate on the first 10 items, then rate the rest independently (`docs/human_eval_rubric.md`).
- [ ] **Dr. Smith:** adjudicate the disagreements in `results/human_eval/adjudication.csv`.
- [ ] Run `python scripts/score_human.py`.

## 4. Fill in the paper
- [ ] Run `python scripts/make_paper_tables.py`, then build `paper/main.tex`.
- [ ] Replace every blue author note with prose based on the actual results.
- [ ] Optionally, time yourselves on five tickets and update `cost_model_assumptions` in `configs/experiments.json`.
- [ ] Set `\draftfalse` in `main.tex`. The build must succeed, which proves no [TBD] or author note is left.

## 5. Before submission
- [ ] Confirm the two references marked `VERIFY` in `paper/references.bib`.
- [ ] Each co-author confirms their roles in the Author Contributions section.
- [ ] Check the venue's policy on disclosing generative-AI use, and adjust that section to match.
- [ ] Ask the CSU IRB whether the rating study needs a determination, and record the answer in the Ethics Statement.
- [ ] Have Dr. Singh and Dr. Smith read the full PDF.
