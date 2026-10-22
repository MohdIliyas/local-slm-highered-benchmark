import json
import requests
import jsonschema

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

def run_batch():
    summary_results = {}

    with open('data/syllabi/schema.json', 'r', encoding='utf-8-sig') as f:
        schema = json.load(f)
    with open('prompts/extraction_prompt.txt', 'r', encoding='utf-8-sig') as f:
        ext_prompt_tmpl = f.read()
    with open('data/syllabi/batch_syllabi.json', 'r', encoding='utf-8-sig') as f:
        syllabi_batch = json.load(f)

    with open('prompts/policy_prompt.txt', 'r', encoding='utf-8-sig') as f:
        pol_prompt_tmpl = f.read()
    with open('data/policies/batch_policies.json', 'r', encoding='utf-8-sig') as f:
        policy_batch = json.load(f)

    with open('prompts/classification_prompt.txt', 'r', encoding='utf-8-sig') as f:
        cls_prompt_tmpl = f.read()
    with open('data/emails/synthetic_tickets.json', 'r', encoding='utf-8-sig') as f:
        ticket_batch = json.load(f)

    for model in MODELS:
        print(f"\n=======================================================")
        print(f"[+] Running Full Batch Benchmark Suite on: {model}")
        print(f"=======================================================")
        summary_results[model] = {}

        # 1. Syllabus Extraction Batch
        valid_json_count = 0
        schema_valid_count = 0
        for item in syllabi_batch:
            raw = query_ollama(model, ext_prompt_tmpl.replace("{{SYLLABUS_TEXT}}", item['text']))
            start_idx, end_idx = raw.find('{'), raw.rfind('}')
            clean = raw[start_idx:end_idx + 1] if (start_idx != -1 and end_idx != -1 and end_idx > start_idx) else raw
            try:
                parsed = json.loads(clean)
                valid_json_count += 1
                jsonschema.validate(instance=parsed, schema=schema)
                schema_valid_count += 1
            except:
                pass
        summary_results[model]["task1_extraction"] = {
            "total": len(syllabi_batch),
            "valid_json": valid_json_count,
            "schema_compliant": schema_valid_count,
            "schema_rate_pct": round((schema_valid_count / len(syllabi_batch)) * 100, 1)
        }

        # 2. Policy Summarization Batch
        total_constraints = 0
        matched_constraints = 0
        bullet_pass_count = 0
        preamble_pass_count = 0
        for item in policy_batch:
            summary = query_ollama(model, pol_prompt_tmpl.replace("{{POLICY_TEXT}}", item['text']))
            summary_lower = summary.lower()
            lines = [l.strip() for l in summary.splitlines() if l.strip()]
            bullets = [l for l in lines if l.startswith(("-", "*", ">", "•")) or (len(l) > 2 and l[0].isdigit() and l[1] in [".", ")"])]
            if len(bullets) == 3:
                bullet_pass_count += 1
            if summary.startswith(("-", "*", ">", "•")) or (summary[0].isdigit() if summary else False):
                preamble_pass_count += 1
            for c in item["constraints"]:
                total_constraints += 1
                if c.lower() in summary_lower:
                    matched_constraints += 1
        summary_results[model]["task2_policy"] = {
            "total_policies": len(policy_batch),
            "bullet_format_adherence": f"{bullet_pass_count}/{len(policy_batch)}",
            "zero_preamble_adherence": f"{preamble_pass_count}/{len(policy_batch)}",
            "constraint_retention_pct": round((matched_constraints / total_constraints) * 100, 1)
        }

        # 3. Ticket Classification Batch
        cls_correct = 0
        for item in ticket_batch:
            pred = query_ollama(model, cls_prompt_tmpl.replace("{{TICKET_TEXT}}", item['text'])).strip()
            if (pred.lower() == item['category'].lower()) or (item['category'].lower() in pred.lower()):
                cls_correct += 1
        summary_results[model]["task3_classification"] = {
            "total_tickets": len(ticket_batch),
            "correct": cls_correct,
            "accuracy_pct": round((cls_correct / len(ticket_batch)) * 100, 1)
        }

    with open('results/intel_i7/batch_eval_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary_results, f, indent=2)

    print("\n[OK] Batch Benchmark Complete. Saved to results/intel_i7/batch_eval_summary.json")

if __name__ == "__main__":
    run_batch()
