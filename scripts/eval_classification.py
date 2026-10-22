import json
import requests
import argparse

def evaluate(model, endpoint="http://localhost:11434"):
    with open('data/emails/synthetic_tickets.json', 'r', encoding='utf-8') as f:
        tickets = json.load(f)
        
    with open('prompts/classification_prompt.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()
        
    correct = 0
    print(f"\n[+] Evaluating Model: {model} on Task 3 (Classification)")
    print("-" * 65)
    
    for item in tickets:
        prompt = prompt_template.replace("{{TICKET_TEXT}}", item['text'])
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "seed": 42}
        }
        res = requests.post(f"{endpoint}/api/generate", json=payload).json()
        pred = res.get("response", "").strip()
        
        # Exact match or normalized containment check
        is_match = (pred.lower() == item['category'].lower()) or (item['category'].lower() in pred.lower())
        if is_match:
            correct += 1
            status = "MATCH"
        else:
            status = "MISMATCH"
            
        print(f"[{item['id']}] Expected: {item['category']:<22} | Pred: {pred:<22} | {status}")
        
    acc = (correct / len(tickets)) * 100
    print("-" * 65)
    print(f"[?] Accuracy for {model}: {correct}/{len(tickets)} ({acc:.1f}%)\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    args = parser.parse_args()
    evaluate(args.model)
