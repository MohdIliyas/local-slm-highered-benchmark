# -*- coding: utf-8 -*-
import json
import requests
import os

MODELS = ["llama3.2:3b", "qwen2.5:7b"]
ENDPOINT = "http://localhost:11434"

def query_ollama(model, prompt):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42}
    }
    res = requests.post(f"{ENDPOINT}/api/generate", json=payload).json()
    return res.get("response", "").strip()

def run_evaluation():
    print("[+] Starting Full Evaluation Suite on Public Institutional Samples...")

    with open('data/policies/public_sample_policies.json', 'r', encoding='utf-8') as f:
        policies = json.load(f)

    with open('data/emails/public_sample_tickets.json', 'r', encoding='utf-8') as f:
        tickets = json.load(f)

    results = {}

    for model in MODELS:
        print(f"\n=======================================================")
        print(f"Evaluating Model: {model}")
        print(f"=======================================================")
        results[model] = {}

        # Task 2: Policy Summarization & Constraint Check
        policy_results = []
        for item in policies:
            prompt = f"Summarize this policy into exactly 3 bullet points, starting immediately with bullets without preamble:\n\n{item['text']}"
            output = query_ollama(model, prompt)
            
            has_preamble = not (output.startswith("-") or output.startswith("*") or output.startswith("-") or output[0].isdigit())
            
            policy_results.append({
                "id": item["id"],
                "output": output,
                "has_preamble_violation": has_preamble
            })
        results[model]["policy_summarization"] = policy_results

        # Task 3: Ticket Classification
        ticket_results = []
        for item in tickets:
            prompt = f"Classify this support ticket into one of the following categories: [LMS Access, Grade Disputes, Online Proctoring, Accessibility/Captions, Course Enrollment, Login/Account Lockout, Exam Rescheduling, General Inquiries]. Return ONLY the category name:\n\n{item['text']}"
            pred = query_ollama(model, prompt)
            is_correct = item['category'].lower() in pred.lower()
            
            ticket_results.append({
                "id": item["id"],
                "expected": item["category"],
                "predicted": pred,
                "correct": is_correct
            })
        results[model]["ticket_classification"] = ticket_results

    os.makedirs('results/intel_i7', exist_ok=True)
    with open('results/intel_i7/public_eval_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print("\n[✔] Evaluation Complete! Results saved to results/intel_i7/public_eval_results.json")

if __name__ == "__main__":
    run_evaluation()
