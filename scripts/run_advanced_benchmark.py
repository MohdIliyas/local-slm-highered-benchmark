import time
import json
import requests
import psutil
import numpy as np

def run_advanced_benchmark(model_name, quantization, temperature, prompt, ground_truth=None):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "options": {
            "temperature": temperature,
            "seed": 42
        }
    }
    
    start_time = time.time()
    response = requests.post(url, json=payload, stream=True)
    
    ttft = None
    tokens = 0
    eval_durations = []
    
    for line in response.iter_lines():
        if line:
            body = json.loads(line.decode('utf-8'))
            if ttft is None:
                ttft = time.time() - start_time
            if "eval_duration" in body:
                eval_durations.append(body["eval_duration"])
            if body.get("done", False):
                tokens = body.get("eval_count", 0)
                total_duration = body.get("total_duration", 1)
                
    total_time = (time.time() - start_time)
    tps = tokens / (total_duration / 1e9) if total_duration > 0 else 0
    
    metrics = {
        "model": model_name,
        "quantization": quantization,
        "temperature": temperature,
        "ttft_sec": ttft,
        "throughput_tps": tps,
        "p50_latency": np.percentile(eval_durations, 50) if eval_durations else 0,
        "p95_latency": np.percentile(eval_durations, 95) if eval_durations else 0,
        "p99_latency": np.percentile(eval_durations, 99) if eval_durations else 0,
        "ram_usage_gb": psutil.virtual_memory().used / (1024**3)
    }
    return metrics

if __name__ == "__main__":
    print("[INFO] Advanced parameter harness initialized.")
