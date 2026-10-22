# Front Matter, Related Work, and Institutional Governance

## Abstract
Higher education institutions face increasing pressure to automate operational workflows while strictly adhering to statutory privacy mandates under the Family Educational Rights and Privacy Act (FERPA) and Title II of the Americans with Disabilities Act (ADA). While proprietary cloud-hosted Large Language Models (LLMs) offer high generative fluencies, their deployment introduces critical data-perimeter risks and recurring subscription overheads. On-device Small Language Models (SLMs) running locally on commodity enterprise workstations present a viable alternative; however, their capacity to execute rigorous institutional text workflows remains under-characterized. In this study, we empirically evaluate two open-weight models (llama3.2:3b and qwen2.5:7b) deployed on a commodity enterprise workstation (Intel Core i7, 16 GB RAM, CPU-only execution) across four authentic higher-education tasks: structured syllabus metadata extraction, institutional policy summarization, support ticket classification, and administrative reply drafting. Our findings demonstrate that while the 3B model achieves higher generation throughput (~108 tokens/sec vs. ~54 tokens/sec), it consistently fails strict JSON schema primitive type casting and hallucinates fictitious administrative policies. Conversely, the 7B model achieves 100% schema validity, strictly adheres to negative formatting constraints, delivers 87.5% classification accuracy, and mitigates hallucination risk through safe slot-filling templating. We conclude that 7B-parameter models represent the practical capability boundary for unattended on-premises administrative automation on commodity campus fleets.

---

## 2. Related Work

### 2.1 Edge & Consumer Hardware Model Inference
Benchmarking local language models on resource-constrained hardware has gained significant momentum as edge quantization formats mature. Husom et al. (2025) systematically evaluated quantized open models in Ollama, establishing that consumer-grade processors can sustain viable operational latencies when properly configured. Similarly, Kurt (2026) demonstrated that 4-bit Medium (Q4_K_M) quantization maintains approximately 99% of full-precision general capability while significantly curbing RAM consumption. However, recent analyses indicate that CPU-bound environments exhibit sharp performance cliffs on strict syntax generation compared to unconstrained matrix operations.

### 2.2 Institutional Privacy & FERPA Compliance
Cloud-based AI architectures present unresolved compliance hurdles in higher education. Dong & Liebowitz (2025) identified that commercial LLM APIs inherently expand an institution's data perimeter, complicating compliance with FERPA data-privacy protections and accessibility guidelines. Operating models on-premises guarantees that course evaluations, student grievances, and accommodation requests never exit institutional control.

### 2.3 Task-Grounded Administrative Benchmarking
Traditional academic benchmarks (e.g., MMLU, GSM8K) fail to evaluate the concrete constraints required in administrative settings. Work in structured outputs (e.g., JSONSchemaBench, 2025) and applied domain triage (Bhetwal et al., 2026) highlights the necessity of evaluating models on format validity, constraint retention, and human intervention costs rather than abstract reasoning puzzles.

---

## 6. Institutional Governance & Operational Feasibility

### 6.1 Labor Overhead and Human Intervention Rate (HIR)
Deploying language models within university administration does not eliminate human labor; rather, it shifts personnel time from initial drafting to verification and error auditing. As our Task 4 results indicate, sub-4B models exhibit a deceptively fluent presentation that masks procedural hallucinations (e.g., inventing nonexistent portal navigation steps or misattributing scheduling conflicts to academic integrity policies). Such hallucinations necessitate thorough human review, effectively yielding an HIR of 1.0. In contrast, 7B models employ transparent slot-filling placeholders ([insert deadline]), reducing human verification to routine variable insertion and substantially lowering administrative overhead.

### 6.2 ADA Title II and Accessibility Auditing
With Department of Justice Title II digital accessibility rules mandating WCAG 2.1 AA compliance across all digital course materials, automated systems must extract and verify syllabus accessibility clauses without hallucinating compliance. The 7B model reliably verified the presence of accommodation policies across all tested disciplines, providing an audit-ready trail for institutional compliance teams.

### 6.3 Deployment Recommendations for Campus IT
1. **Tiered Allocation:** Reserve sub-4B models for low-stakes search indexing or conversational query expansion; mandate $\ge 7\text{B}$ parameter tiers for any workflow requiring structured JSON database ingestion or policy dissemination.
2. **Deterministic Fallbacks:** Implement runtime schema validators (jsonschema) and deterministic regex guards before outputs are stored or dispatched to students.
3. **Hardware Fleet Readiness:** Standard 16 GB enterprise laptops running AVX2-compatible CPUs are fully sufficient for 7B Q4 inference, requiring no specialized GPU procurement for staff workstations.

---

## 7. Conclusion

This study provides an empirical benchmark of on-device small language models on commodity enterprise hardware within a privacy-sensitive university setting. Our results demonstrate that while sub-4B models offer high throughput on CPU, 7B open-weight models (qwen2.5:7b) represent the minimal viable threshold for zero-shot schema adherence, negative constraint compliance, and reliable administrative triage. By deploying 7B SLMs on standard staff workstations, institutions can achieve regulatory compliance under FERPA and ADA Title II without ongoing cloud operational costs.

---

## Author Contributions (CRediT Statement)
- **Mohammed Iliyas Sanjamala:** Conceptualization, Methodology, Software, Investigation, Formal Analysis, Writing – Original Draft, Project Administration.
- **Karthikeyan Prem Kumar:** Data Curation, Validation (Second Human Evaluator), Investigation, Writing – Review & Editing.
- **Richard Smith:** Conceptualization (Higher Education Context), Validation, Supervision (Institutional & Policy Domain), Writing – Review & Editing.
- **Aditi Singh:** Supervision (Technical & Benchmarking Rigor), Methodology, Formal Analysis, Writing – Review & Editing.
