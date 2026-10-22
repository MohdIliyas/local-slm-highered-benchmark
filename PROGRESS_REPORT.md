# Empirical Research Progress Report

**Project Title:** Empirical Evaluation of On-Device SLMs on Consumer Laptops for Privacy-Compliant University Workflows
**Date:** October 22, 2026
**Lead Author / Engineer:** Mohammed Iliyas Sanjamala (mohdiliyas83@outlook.com)
**Co-Authors:** Karthikeyan Prem Kumar, Dr. Richard Smith, Dr. Aditi Singh
**Repository:** local-slm-highered-benchmark (Branch: main)
**Target Venues:** ACM Learning @ Scale / AMCIS / cs.CL / cs.DC

---

## 1. Executive Summary
As of October 22, 2026, this project has achieved an end-to-end working benchmark and a complete first draft of the academic manuscript. We successfully constructed a reproducible, privacy-preserving on-device benchmarking harness for Small Language Models (SLMs) running locally on commodity enterprise laptop hardware (Intel Core i7, 16 GB RAM, CPU-only execution via Ollama).

All four core administrative workflows---Structured Syllabus Extraction, Policy Summarization, Support Ticket Classification, and Administrative Reply Drafting---have been designed, piloted, batched, evaluated, and documented in a conference-ready LaTeX manuscript (paper/main.tex).

---

## 2. Research Milestone Audit (9-Week Plan)
- Phase 1 (Setup & Scaffolding): 100% COMPLETE. Repository initialized, dependencies locked, and models configured.
- Phase 2 (Dataset Curation): 50% COMPLETE. Schemas (schema.json) and seed batches operational; full N=50/300 scaling in progress.
- Phase 3 (Benchmarking Pipeline): 100% COMPLETE (Testbed A). Automated profiler and batch runner execute deterministically on Intel Core i7 CPU.
- Phase 4 (Empirical Evaluation): 60% COMPLETE. Baseline matrix logged; double-blind human inter-rater reliability pass and M4 profile remaining.
- Phase 5 (Manuscript Drafting): 85% COMPLETE. Full manuscript compiled into ACM-standard LaTeX (paper/main.tex and paper/references.bib).

---

## 3. Systems Throughput Findings (Intel Core i7 CPU-Only)
- llama3.2:3b (Q4_K_M): 105.2 - 111.2 tokens/sec | TTFT: 0.01 - 0.09s | ~2.2 GB RAM footprint.
- qwen2.5:7b (Q4_K_M): 52.4 - 56.1 tokens/sec | TTFT: 0.02 - 0.22s | ~4.9 GB RAM footprint.

---

## 4. Multi-Task Empirical Findings Matrix
- Task 1 (Syllabus Extraction): llama3.2:3b failed schema primitive types (output strings for weights); qwen2.5:7b achieved 100% schema compliance.
- Task 2 (Policy Summarization): llama3.2:3b retained constraints but failed negative constraints (added preamble); qwen2.5:7b had zero preamble and 100% 3-bullet formatting.
- Task 3 (Ticket Classification): llama3.2:3b achieved 75.0% accuracy; qwen2.5:7b achieved 87.5% accuracy.
- Task 4 (Administrative Reply Drafting): llama3.2:3b hallucinated bogus policies (High HIR); qwen2.5:7b safely employed slot-filling placeholders (Low HIR).

---

## 5. Next Steps Toward Camera-Ready Submission
1. Scale test datasets across syllabi, policies, and tickets.
2. Execute double-blind human evaluation pass with Cohen kappa calculation.
3. Run comparative benchmarks on Apple Silicon M4 testbed.
4. Visual PDF compilation and team revision cycles.
