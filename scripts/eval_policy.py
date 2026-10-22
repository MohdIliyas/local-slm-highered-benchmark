import requests
import argparse

CRITICAL_CONSTRAINTS = [
    "24 hours",
    "48 hours",
    "20%",
    "5",
    "fa"
]

def evaluate(model, endpoint="http://localhost:11434"):
    with open('prompts/policy_prompt.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    with open('data/policies/sample_policy.txt', 'r', encoding='utf-8') as f:
        policy_text = f.read()

    prompt = prompt_template.replace("{{POLICY_TEXT}}", policy_text)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42}
    }

    print(f"\n[+] Running Task 2 Policy Summarization on: {model}")
    print("-" * 65)

    res = requests.post(f"{endpoint}/api/generate", json=payload).json()
    summary = res.get("response", "").strip()

    print(f"Generated Summary:\n{summary}\n")
    print("-" * 65)

    # 1. Structural Check: Count bullet points (including unicode bullet •)
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    bullet_lines = [
        l for l in lines 
        if l.startswith(("-", "*", ">", "•")) or (len(l) > 2 and l[0].isdigit() and l[1] in [".", ")"])
    ]
    bullet_count = len(bullet_lines)
    bullet_passed = (bullet_count == 3)

    # Conversational preamble check
    has_preamble = not (summary.startswith(("-", "*", ">", "•")) or (summary[0].isdigit() if summary else False))

    # 2. Constraint Retention Check
    summary_lower = summary.lower()
    matched_constraints = [c for c in CRITICAL_CONSTRAINTS if c in summary_lower]
    retention_rate = (len(matched_constraints) / len(CRITICAL_CONSTRAINTS)) * 100

    print("Evaluation Results:")
    print(f" - Bullet Count: {bullet_count}/3 -> {'PASS' if bullet_passed else 'FAIL'}")
    print(f" - Zero-Preamble Compliance: {'FAIL (conversational preamble present)' if has_preamble else 'PASS'}")
    print(f" - Constraint Retention: {len(matched_constraints)}/{len(CRITICAL_CONSTRAINTS)} ({retention_rate:.1f}%)")
    for c in CRITICAL_CONSTRAINTS:
        found = c in summary_lower
        print(f"   * [{ 'OK' if found else 'X' }] Constraint '{c}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    args = parser.parse_args()
    evaluate(args.model)
