# Mac Benchmarking & Evaluation Guide
**Project:** Empirical Evaluation of On-Device Large Language Models on Consumer Hardware for Privacy-Compliant University Workflows  
**Repository:** `MohdIliyas/local-slm-highered-benchmark`

---

## 1. Context & Research Focus

### **The Core Problem**
Higher education institutions face increasing pressure to automate administrative workflows (such as syllabus extraction, helpdesk support ticket triage, and policy compliance audits) while strictly complying with statutory privacy mandates under:
* **FERPA (Family Educational Rights and Privacy Act):** Protecting student records from third-party commercial cloud exposure.
* **ADA Title II (Americans with Disabilities Act):** Ensuring digital accessibility and compliance across course materials, web content, and institutional documentation.

### **Why Institutional Accessibility Matters Beyond Alt-Text**
In higher education governance, compliance with ADA Title II and institutional privacy mandates extends far beyond basic website alt-text. It encompasses structural, legal, and operational requirements:
* **Document and Syllabus Remediation:** Automated extraction must accurately capture accessibility clauses, disability resource contact routing, and accommodation timelines (e.g., ensuring required 3-day turnaround times for document remediation).
* **Information Parity:** Automated text summarization of complex institutional policies must retain all legal constraints without omission or hallucination.
* **Strict Data Perimeters:** Transmitting unvetted student records, PII, and accommodation grievances to third-party cloud APIs creates severe regulatory and legal exposure. Running local open-weight Large Language Models (LLMs) on commodity hardware guarantees that sensitive student data never leaves the institutional boundary.

---

## 2. Step-by-Step Instructions for Karthik (Apple Silicon Mac Execution)

Follow these exact steps in your Mac terminal (`Terminal` or `iTerm2`) to execute the benchmark suite and log your performance metrics:

### **Step 1: Clone the Repository & Navigate In**
```bash
git clone https://github.com/MohdIliyas/local-slm-highered-benchmark.git
cd local-slm-highered-benchmark
```

### **Step 2: Set Up the Python Virtual Environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### **Step 3: Ensure Ollama is Running & Pull Target Models**
*(Make sure the Ollama application is running on your Mac)*
```bash
ollama pull llama3.2:3b
ollama pull qwen2.5:7b
```

### **Step 4: Run the Batch Evaluation Suite**
```bash
python scripts/run_batch_eval.py
```

### **Step 5: Commit and Push Results Back to GitHub**
Once the script finishes executing:
```bash
git add results/
git commit -m "Add Apple Silicon Mac benchmark results"
git push origin main
```