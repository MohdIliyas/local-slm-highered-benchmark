# Karthik's Action Checklist: Cross-Platform Benchmarking & Double-Blind Review

**Project Title:** Empirical Evaluation of On-Device SLMs on Consumer Laptops for Privacy-Compliant University Workflows
**Lead Author:** Mohammed Iliyas Sanjamala
**Collaborator:** Karthikeyan Prem Kumar

## 1. Apple Silicon M4 Benchmarking
- Clone repository, run python scripts\run_benchmark.py --output results\apple_m4\ and python scripts\run_batch_eval.py --device apple_m4, then push results.

## 2. Double-Blind Review (Phase 4)
- Pull latest changes, open esults/human_eval/blind_queue.json, score items under ater_2_score, compute Cohen's Kappa, and push.
