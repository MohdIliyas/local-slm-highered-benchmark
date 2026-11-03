#!/usr/bin/env python3
"""Build a blinded human-evaluation queue from the main run.

Usage:
    python scripts/make_blind_queue.py --machine intel_i7 --raters mohammed karthik

Creates (in results/human_eval/):
    queue.md                    what raters read: source text + output, no model names
    ratings_<rater>.csv         one blank sheet per rater
    key/blind_key.json          blind_id -> model. Raters must NOT open this folder.

Items are shuffled with a fixed seed, so the same run always gives the same queue.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.tasks import ROOT, load_json  # noqa: E402

TASKS = ("drafting", "policy")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="intel_i7")
    ap.add_argument("--raters", nargs="+", required=True)
    ap.add_argument("--models", nargs="*", help="limit to these model keys (default: all)")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    raw = ROOT / "results" / args.machine / "main" / "raw.jsonl"
    if not raw.exists():
        sys.exit(f"{raw} not found; run the main preset first.")
    src = {t["id"]: t["text"] for t in load_json("tickets.json")}
    src.update({p["id"]: p["text"] for p in load_json("policies.json")})

    calls = {}
    for line in raw.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["kind"] == "call" and r["task"] in TASKS and r["temperature"] == 0.0 and not r.get("error"):
            if args.models and r["model_key"] not in args.models:
                continue
            calls[(r["model_key"], r["task"], r["item_id"])] = r
    items = list(calls.values())
    rng = random.Random(args.seed)
    rng.shuffle(items)

    out = ROOT / "results" / "human_eval"
    (out / "key").mkdir(parents=True, exist_ok=True)
    key, md = {}, ["# Human evaluation queue\n",
                   "Rate each item using docs/human_eval_rubric.md. Record scores in your own ratings CSV.\n",
                   "Do not open results/human_eval/key/.\n"]
    for i, r in enumerate(items, 1):
        bid = f"H{i:03d}"
        key[bid] = {"model_key": r["model_key"], "task": r["task"], "item_id": r["item_id"]}
        label = "Student inquiry" if r["task"] == "drafting" else "Policy text"
        md += [f"\n---\n\n## {bid}  ({r['task']})\n", f"**{label}:**\n\n> {src[r['item_id']]}\n",
               "**Model output:**\n", "```text\n" + r["text"].strip() + "\n```\n"]
    (out / "queue.md").write_text("\n".join(md), encoding="utf-8")
    (out / "key" / "blind_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    for rater in args.raters:
        p = out / f"ratings_{rater}.csv"
        if p.exists():
            print(f"  {p.name} exists, not overwriting")
            continue
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["blind_id", "task", "quality_1to5", "needs_substantive_edit_YN", "factual_error_YN", "notes"])
            for bid, k in key.items():
                w.writerow([bid, k["task"], "", "", "", ""])
    print(f"{len(items)} items -> results/human_eval/queue.md; sheets for: {', '.join(args.raters)}")


if __name__ == "__main__":
    main()
