import argparse
import csv
import os
import time
import requests
import psutil

def get_ram_usage_mb():
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / (1024 * 1024), 2)

def run_inference(endpoint, model, prompt, system_prompt="", temperature=0.0, seed=42):
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "seed": seed
        }
    }
    
    start_time = time.perf_counter()
    response = requests.post(f"{endpoint}/api/generate", json=payload)
    total_wall_clock = time.perf_counter() - start_time
    
    if response.status_code != 200:
        raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")
        
    data = response.json()
    
    prompt_eval_dur_s = data.get("prompt_eval_duration", 0) / 1e9
    eval_dur_s = data.get("eval_duration", 0) / 1e9
    eval_count = data.get("eval_count", 0)
    prompt_eval_count = data.get("prompt_eval_count", 0)
    
    tokens_per_second = round(eval_count / eval_dur_s, 2) if eval_dur_s > 0 else 0.0
    
    return {
        "response_text": data.get("response", "").strip(),
        "ttft_s": round(prompt_eval_dur_s, 4),
        "eval_dur_s": round(eval_dur_s, 4),
        "total_wall_clock_s": round(total_wall_clock, 4),
        "prompt_tokens": prompt_eval_count,
        "eval_tokens": eval_count,
        "tokens_per_second": tokens_per_second,
        "peak_ram_mb": get_ram_usage_mb()
    }

def main():
    parser = argparse.ArgumentParser(description="Empirical SLM Benchmarking Harness")
    parser.add_argument("--machine", type=str, choices=["intel_i7", "apple_m4"], required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--quant", type=str, default="default")
    parser.add_argument("--task", type=str, default="pilot_test")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--endpoint", type=str, default="http://localhost:11434")
    
    args = parser.parse_args()
    
    output_dir = os.path.join("results", args.machine)
    os.makedirs(output_dir, exist_ok=True)
    csv_file = os.path.join(output_dir, f"{args.task}_metrics.csv")
    
    file_exists = os.path.isfile(csv_file)
    fields = [
        "timestamp", "machine", "model", "quant", "task", "run_id",
        "ttft_s", "eval_dur_s", "total_wall_clock_s", "prompt_tokens",
        "eval_tokens", "tokens_per_second", "peak_ram_mb", "raw_response"
    ]
    
    print(f"\n[+] Starting Benchmark: {args.model} ({args.quant}) on {args.machine}")
    print(f"[+] Output logging to: {csv_file}\n")
    
    test_prompt = "Summarize the key attendance and grading dispute policy for an introductory computer science course in three concise bullet points."
    
    with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not file_exists:
            writer.writeheader()
            
        for run_id in range(1, args.runs + 1):
            print(f"--> Executing Run {run_id}/{args.runs}...")
            metrics = run_inference(args.endpoint, args.model, test_prompt)
            
            row = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "machine": args.machine,
                "model": args.model,
                "quant": args.quant,
                "task": args.task,
                "run_id": run_id,
                "ttft_s": metrics["ttft_s"],
                "eval_dur_s": metrics["eval_dur_s"],
                "total_wall_clock_s": metrics["total_wall_clock_s"],
                "prompt_tokens": metrics["prompt_tokens"],
                "eval_tokens": metrics["eval_tokens"],
                "tokens_per_second": metrics["tokens_per_second"],
                "peak_ram_mb": metrics["peak_ram_mb"],
                "raw_response": metrics["response_text"].replace("\n", " ")
            }
            writer.writerow(row)
            f.flush()
            print(f"    Done: TTFT={metrics['ttft_s']}s | Speed={metrics['tokens_per_second']} tps | RAM={metrics['peak_ram_mb']}MB")
            time.sleep(1)

    print("\n[?] Benchmark batch finished successfully.\n")

if __name__ == "__main__":
    main()
