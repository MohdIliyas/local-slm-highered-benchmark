# Empirical Evaluation of On-Device SLMs on Consumer Laptops for Privacy-Compliant University Workflows

**Authors:** Mohammed Iliyas Sanjamalagit1$, Karthikeyan Prem Kumargit1$, Richard Smithgit2$, Aditi Singhgit1$  
git1$ *Department of Computer Science*  
git2$ *Center for Digital Learning and Academic Technology*  
*(Institutional identity and geographic location anonymized for administrative privacy)*  
**Corresponding Author:** mohdiliyas83@outlook.com

---

## 1. Introduction

Higher education institutions face conflicting pressures at the intersection of operational scaling and statutory compliance. Expanding administrative workloads—including student helpdesk triage, syllabus compliance auditing, and policy communication—present natural use-cases for generative artificial intelligence. However, standard commercial implementations relying on proprietary cloud APIs (e.g., OpenAI, Anthropic) introduce substantial data governance vulnerabilities under the Family Educational Rights and Privacy Act (FERPA) and institutional data-perimeter mandates (Dong & Liebowitz, 2025). Transmitting student inquiries, grade dispute appeals, and unvetted course materials beyond campus boundaries creates unacceptable institutional exposure.

Simultaneously, regulatory obligations—such as the Department of Justice Title II digital accessibility guidelines—demand rigorous, accurate processing of course artifacts and student communications. While large-scale centralized models demonstrate strong conversational fluencies, university IT departments require privacy-preserving, cost-effective alternatives that run directly on existing campus hardware fleets without dedicated GPU servers or per-token operational expenditures.

Recent advancements in quantization (e.g., llama.cpp GGUF formats) and small language models (SLMs) spanning 3B to 7B parameters suggest that edge deployment on commodity x86 office laptops is theoretically feasible (Husom et al., 2025; Kurt, 2026). Nevertheless, significant empirical questions remain regarding whether sub-8B models possess sufficient capability to reliably execute bounded administrative operations without catastrophic constraint degradation or deceptive hallucinations.

This paper delivers an empirical evaluation of on-device open-weight SLMs (llama3.2:3b and qwen2.5:7b) deployed on a standard university enterprise laptop. Moving away from generic benchmarks (e.g., MMLU, GSM8K), we evaluate model capabilities across four authentic administrative workflows:
1. **Structured Syllabus Metadata Extraction** against strict JSON schema typing contracts.
2. **Institutional Policy Summarization** evaluating numeric constraint preservation and negative prompt adherence.
3. **Support Ticket Classification** across an 8-class digital learning taxonomy.
4. **Administrative Reply Drafting** characterizing hallucination risks and measuring Human Intervention Rates (HIR).

---

## 3. Methodology & Experimental Setup

### 3.1 Hardware Environment & Deployment Stack
To reflect realistic institutional procurement rather than idealized high-performance computing clusters, experiments were conducted on an enterprise-standard x86 mobile workstation:
- **Processor:** Intel Core i7 CPU (16 cores, base AVX2 instruction set).
- **System Memory:** 16 GB DDR5 RAM.
- **Acceleration:** CPU-only execution (zero dedicated GPU compute / integrated graphics).
- **Operating System:** Windows 11 Enterprise running Windows Subsystem / PowerShell environment.

Local inference was orchestrated via Ollama (v0.5.x) serving 4-bit Medium quantized weights (Q4_K_M) using default llama.cpp CPU thread allocations. To eliminate stochastic variance and ensure deterministic reproducibility across comparative runs, all inferences enforced greedy decoding ($\text{temperature} = 0.0$, $\text{seed} = 42$).

### 3.2 Evaluation Workflows & Task Formulations

#### Task 1: Structured Syllabus Extraction
Evaluates zero-shot information extraction and structured output adherence. Syllabi from STEM, Humanities, and Business disciplines are provided to the model with instructions to output raw JSON strictly conforming to a predefined schema (jsonschema). Scoring evaluates both JSON syntactic parseability and schema-level field type validation (string identifiers vs. numeric grading weights).

#### Task 2: Policy Summarization & Constraint Retention
Assesses the model's ability to compress dense regulatory prose into exactly three bullet points while retaining all quantitative bounds (e.g., notification windows, appeal deadlines, and attendance percentages). The evaluation harness automatically parses bullet structure, checks for forbidden conversational preambles, and computes the exact retention rate of critical operational constraints.

#### Task 3: Support Ticket Classification
Measures intent triage accuracy across eight distinct operational categories (*LMS Access, Grade Disputes, Online Proctoring, Accessibility/Captions, Course Enrollment, Login/Account Lockout, Exam Rescheduling, General Inquiries*). The model must emit only the predicted category label, which is evaluated against hand-annotated ground truth.

#### Task 4: Administrative Reply Drafting & Human Intervention Rate (HIR)
Assesses the downstream usability of model-drafted student communications regarding sensitive procedures (e.g., final exam time conflicts). Rather than relying solely on automated n-gram overlap metrics (e.g., ROUGE), outputs are assessed through a Human-in-the-Loop protocol to calculate the **Human Intervention Rate (HIR)**: the frequency with which human coordinators must intervene to correct deceptive factual hallucinations, fictitious policy references, or fabricated user portal workflows prior to student transmission.
