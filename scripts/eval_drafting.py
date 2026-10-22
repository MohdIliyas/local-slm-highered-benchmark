import json
import requests
import argparse

SELECTED_TICKETS = ["TICK-002", "TICK-007"]

def evaluate(model, endpoint="http://localhost:11434"):
    with open('prompts/drafting_prompt.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    with open('data/emails/synthetic_tickets.json', 'r', encoding='utf-8') as f:
        tickets = json.load(f)

    target_tickets = [t for t in tickets if t['id'] in SELECTED_TICKETS]

    print(f"\n[+] Running Task 4 Administrative Reply Drafting on: {model}")
    print("=" * 70)

    for item in target_tickets:
        prompt = prompt_template.replace("{{STUDENT_INQUIRY}}", item['text'])
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "seed": 42}
        }

        res = requests.post(f"{endpoint}/api/generate", json=payload).json()
        draft = res.get("response", "").strip()

        has_subject = "subject:" in draft.lower()
        has_signoff = "academic support services" in draft.lower()
        word_count = len(draft.split())

        print(f"\n[{item['id']} - {item['category']}]")
        print(f"Student Inquiry: \"{item['text']}\"")
        print("-" * 70)
        print(f"Generated Draft:\n{draft}\n")
        print("-" * 70)
        print("Automated Structural Checks:")
        print(f"  - Subject Line Included: {'[OK]' if has_subject else '[X]'}")
        print(f"  - Target Sign-off Included: {'[OK]' if has_signoff else '[X]'}")
        print(f"  - Length: {word_count} words")
        print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    args = parser.parse_args()
    evaluate(args.model)
