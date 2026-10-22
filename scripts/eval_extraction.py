import json
import requests
import argparse
import jsonschema

def evaluate(model, endpoint="http://localhost:11434"):
    with open('data/syllabi/schema.json', 'r', encoding='utf-8') as f:
        schema = json.load(f)

    with open('prompts/extraction_prompt.txt', 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    with open('data/syllabi/sample_syllabus.txt', 'r', encoding='utf-8') as f:
        syllabus_text = f.read()

    prompt = prompt_template.replace("{{SYLLABUS_TEXT}}", syllabus_text)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42}
    }

    print(f"\n[+] Running Task 1 Syllabus Extraction on: {model}")
    print("-" * 65)

    res = requests.post(f"{endpoint}/api/generate", json=payload).json()
    raw = res.get("response", "").strip()

    # Robust extraction: slice between the first '{' and last '}'
    start_idx = raw.find('{')
    end_idx = raw.rfind('}')

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        clean = raw[start_idx:end_idx + 1]
    else:
        clean = raw

    print(f"Parsed JSON Candidate:\n{clean}\n")
    print("-" * 65)

    try:
        parsed = json.loads(clean)
        jsonschema.validate(instance=parsed, schema=schema)
        print(f"[?] Schema Validity: PASSED (100% compliant with schema.json)")
    except json.JSONDecodeError as e:
        print(f"[?] JSON Parse Error: Invalid JSON syntax -> {e}")
    except jsonschema.ValidationError as e:
        print(f"[?] Schema Validation Error: Schema mismatch -> {e.message}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    args = parser.parse_args()
    evaluate(args.model)
