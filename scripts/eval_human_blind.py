import json
import random
import os
import requests

def setup_blind_review():
    print("\n[+] Setting up Double-Blind Human Evaluation Protocol (Phase 4)")
    print("-" * 65)
    
    with open('data/policies/batch_policies.json', 'r', encoding='utf-8') as f:
        policies = json.load(f)
        
    with open('prompts/policy_prompt.txt', 'r', encoding='utf-8') as f:
        policy_prompt = f.read()
        
    MODELS = ["llama3.2:3b", "qwen2.5:7b"]
    blind_items = []
    item_counter = 1

    for model in MODELS:
        for item in policies:
            payload = {
                "model": model,
                "prompt": policy_prompt.replace("{{POLICY_TEXT}}", item['text']),
                "stream": False,
                "options": {"temperature": 0.0, "seed": 42}
            }
            res = requests.post("http://localhost:11434/api/generate", json=payload).json()
            output_text = res.get("response", "").strip()
            
            blind_items.append({
                "blind_id": f"BLIND-VAL-{item_counter:03d}",
                "task": "Policy Summarization",
                "source_model_hidden": model,
                "anonymized_output": output_text,
                "rater_1_score": None,
                "rater_2_score": None
            })
            item_counter += 1

    random.shuffle(blind_items)
    os.makedirs('results/human_eval', exist_ok=True)
    output_file = 'results/human_eval/blind_queue.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(blind_items, f, indent=2)
        
    print(f"[?] Generated {len(blind_items)} blinded evaluation items.")
    print(f"[?] Saved review queue to: {output_file}")
    print("    - Mohammed can now independently score items under 'rater_1_score' (1-5 rubric).")

if __name__ == "__main__":
    setup_blind_review()
