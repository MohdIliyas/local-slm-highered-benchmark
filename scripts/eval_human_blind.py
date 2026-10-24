import json
import random
import os

def setup_blind_review():
    print("\n[+] Setting up Double-Blind Human Evaluation Protocol (Phase 4)")
    print("-" * 65)
    
    # Load batch evaluation summaries or generated outputs
    results_path = 'results/intel_i7/batch_eval_summary.json'
    if not os.path.exists(results_path):
        print("[!] Error: batch_eval_summary.json not found. Run batch evaluation first.")
        return

    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    blind_items = []
    for idx, item in enumerate(data.get('evaluations', [])):
        blind_items.append({
            "blind_id": f"BLIND-VAL-{idx+1:03d}",
            "task": item.get('task'),
            "anonymized_output": item.get('output'),
            "rater_1_score": None,
            "rater_2_score": None
        })
        
    os.makedirs('results/human_eval', exist_ok=True)
    output_file = 'results/human_eval/blind_queue.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(blind_items, f, indent=2)
        
    print(f"[?] Generated {len(blind_items)} blinded evaluation items.")
    print(f"[?] Saved review queue to: {output_file}")
    print("    - Mohammed and Karthikeyan can now independently score items (1-5 rubric).")
    print("    - Run with --calculate to compute Cohen's Kappa once scored.\n")

if __name__ == "__main__":
    setup_blind_review()
