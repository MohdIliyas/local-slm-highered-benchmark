#!/usr/bin/env python3
"""Run a preset from configs/experiments.json and append raw results.

Usage:
    python scripts/run_experiments.py --machine intel_i7 --preset smoke
    python scripts/run_experiments.py --machine intel_i7 --preset main
    python scripts/run_experiments.py --machine apple_m4 --preset main

Raw output: results/<machine>/<preset>/raw.jsonl (one JSON object per call).
The run is resumable: rerunning skips calls already in raw.jsonl, so a crash
or a closed laptop lid costs nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import sysinfo  # noqa: E402
from bench.ollama_client import OllamaClient, DEFAULT_ENDPOINT  # noqa: E402
from bench.tasks import ROOT, NUM_PREDICT, build_items  # noqa: E402


def call_key(model_key, task, item_id, temp, seed):
    return f"{model_key}|{task}|{item_id}|{temp}|{seed}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", required=True, help="label, e.g. intel_i7 or apple_m4")
    ap.add_argument("--preset", default="main")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--config", default=str(ROOT / "configs" / "experiments.json"))
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    preset = cfg["presets"][args.preset]
    tags = cfg["models"]
    client = OllamaClient(args.endpoint)

    if client.version() is None:
        sys.exit(f"Cannot reach Ollama at {args.endpoint}. Is it running?")
    missing = [tags[m] for m in preset["models"] if client.digest(tags[m]) is None]
    if missing:
        sys.exit("Models not pulled yet. Run:\n" + "\n".join(f"  ollama pull {t}" for t in missing))

    out_dir = ROOT / "results" / args.machine / args.preset
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "raw.jsonl"
    done = set()
    if raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("kind") == "call" and not r.get("error"):
                done.add(call_key(r["model_key"], r["task"], r["item_id"], r["temperature"], r["seed"]))

    manifest = sysinfo.collect(client, [tags[m] for m in preset["models"]])
    manifest.update({"machine": args.machine, "preset": args.preset, "preset_config": preset})
    (out_dir / f"manifest_{int(time.time())}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    items = {t: build_items(t) for t in preset["tasks"]}
    if preset.get("limit_per_task"):
        items = {t: v[: preset["limit_per_task"]] for t, v in items.items()}

    total = sum(len(v) for v in items.values()) * len(preset["temperatures"]) * len(preset["seeds"]) * len(preset["models"])
    n = 0
    with raw_path.open("a", encoding="utf-8") as fh:
        for mk in preset["models"]:
            tag = tags[mk]
            todo = [(t, it, T, s) for t in preset["tasks"] for it in items[t]
                    for T in preset["temperatures"] for s in preset["seeds"]
                    if call_key(mk, t, it["id"], T, s) not in done]
            n += sum(len(v) for v in items.values()) * len(preset["temperatures"]) * len(preset["seeds"]) - len(todo)
            if not todo:
                print(f"[{mk}] already complete")
                continue
            print(f"[{mk}] unloading other models, cold-start load of {tag}")
            client.unload_all()
            num_gpu = preset.get("num_gpu")
            cold = client.generate(tag, "Reply with the word ready.", temperature=0.0, seed=0, num_predict=8,
                                   num_gpu=num_gpu)
            fh.write(json.dumps({"kind": "cold_start", "machine": args.machine, "model_key": mk, "model": tag,
                                 **{k: v for k, v in cold.to_dict().items() if k != "itl_s"}}) + "\n")
            fh.flush()
            for task, it, T, seed in todo:
                n += 1
                res = client.generate(tag, it["prompt"], temperature=T, seed=seed, num_predict=NUM_PREDICT[task],
                                      num_gpu=num_gpu)
                rec = {"kind": "call", "machine": args.machine, "preset": args.preset, "model_key": mk,
                       "task": task, "item_id": it["id"], "temperature": T, "seed": seed,
                       "num_predict": NUM_PREDICT[task], "num_gpu": num_gpu, **res.to_dict()}
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                status = "ERR " + res.error if res.error else f"{res.decode_tps or 0:.1f} tok/s"
                print(f"  [{n}/{total}] {mk} {task} {it['id']} T={T} s={seed}: {status}")
    print(f"\nDone. Raw results in {raw_path.relative_to(ROOT)}")
    print(f"Next: python scripts/score.py --machine {args.machine}")


if __name__ == "__main__":
    main()
