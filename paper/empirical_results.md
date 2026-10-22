# 5. Empirical Results & Discussion

We conducted an empirical evaluation of on-device small language models (llama3.2:3b and qwen2.5:7b) deployed on a commodity enterprise workstation (Intel Core i7, 16 GB RAM, CPU-only inference via Ollama) across four representative university administrative workflows. All experiments were conducted using greedy decoding ($\text{temperature}=0.0$, $\text{seed}=42$) to ensure strict determinism and reproducibility.

---

## 5.1 Systems Performance & Inference Throughput

Both evaluated model tiers operated comfortably above interactive human reading speeds (~15–20 tokens/sec), establishing the baseline viability of commodity x86 CPUs for local institutional automation without dedicated GPU accelerators.

| Model | Parameter Tier | Quantization | Eval Throughput (TPS) | Time to First Token (TTFT) | Memory Footprint (RAM) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **llama3.2:3b** | 3.21B | Q4_K_M | **105.2 – 111.2 tps** | 0.01 – 0.09s (cached) | ~2.2 GB |
| **qwen2.5:7b** | 7.61B | Q4_K_M | **52.4 – 56.1 tps** | 0.02 – 0.22s (cached) | ~4.9 GB |

While the sub-4B tier achieved roughly double the generative throughput of the 7B model, quality evaluations across structured and constrained tasks revealed pronounced capability bifurcations between the two scales.

---

## 5.2 Task-Grounded Benchmark Findings

### Task 1: Structured Syllabus Extraction
- **Objective:** Extract structured metadata (course_code, instructor_name, office_hours, grading_breakdown, has_accessibility_statement) complying strictly with a standard JSON schema.
- **Empirical Finding:** llama3.2:3b consistently generated valid JSON syntax but exhibited a 100% failure rate against JSON Schema type constraints by outputting percentage weights as strings ("30%") rather than raw numbers (30). In contrast, qwen2.5:7b strictly observed primitive type casting rules, achieving 100% schema compliance across multi-disciplinary syllabi.

### Task 2: Policy Summarization & Constraint Retention
- **Objective:** Summarize multi-clause academic policies into exactly three bullet points while preserving critical quantitative thresholds (notification windows, percentages, appeal deadlines) without introductory preamble.
- **Empirical Finding:** 
  - qwen2.5:7b demonstrated strict negative constraint adherence, generating zero conversational filler and capturing ground-truth conditions (e.g., semantic retention of deadline windows like "five business days").
  - llama3.2:3b successfully retained numerical constraints but consistently violated negative formatting guidelines by prepending conversational preambles (e.g., *"Here are three concise bullet points..."*).

### Task 3: Support Ticket Classification
- **Objective:** Classify student support inquiries across an 8-class operational taxonomy.
- **Empirical Finding:** 
  - llama3.2:3b achieved **75.0%** classification accuracy, frequently confusing overlapping administrative and technical categories (e.g., misclassifying LMS enrollment latency as generic inquiries).
  - qwen2.5:7b achieved **87.5%** accuracy, demonstrating superior semantic disambiguation on operational boundaries (e.g., distinguishing remote proctoring failures from multi-factor account lockouts).

### Task 4: Administrative Reply Drafting & Human Intervention Rate (HIR)
- **Objective:** Draft professional, empathetic student inquiry replies adhering to standard institutional sign-offs while avoiding hallucinated administrative policies.
- **Empirical Finding:** 
  - **High Intervention Rate (llama3.2:3b):** The 3B model hallucinated non-existent portal buttons and fabricated fictitious institutional policy clauses (e.g., citing a non-existent *"Academic Integrity Policy Section 3.2.1"* for a standard exam scheduling conflict), necessitating mandatory human correction before dispatch.
  - **Low Intervention Rate (qwen2.5:7b):** The 7B model avoided deceptive institutional claims by adopting safe bracketed placeholders ([insert deadline], [insert email address]), reducing the human oversight cost to routine slot-filling.

---

## 5.3 Comparative Summary Matrix

| Metric / Dimension | llama3.2:3b | qwen2.5:7b | Institutional Recommendation |
| :--- | :--- | :--- | :--- |
| **Inference Speed** | **Fast** (~108 tps) | **Moderate** (~54 tps) | Both suitable for interactive real-time use. |
| **JSON Schema Typing** | Fails primitive constraints | 100% compliant | 7B required for automated database ingestion. |
| **Formatting Adherence** | Prone to conversational filler | Strict negative compliance | 7B required for programmatic summary pipelines. |
| **Classification Accuracy** | 75.0% | **87.5%** | 7B required for automated triage dispatch. |
| **Hallucination Risk (HIR)** | High (fabricates policies) | Low (uses placeholders) | 3B requires full human re-authoring; 7B requires slot-filling. |
