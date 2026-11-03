#!/usr/bin/env python3
"""Score raw runs and write results/<machine>/summary.json + per_item.csv.

Usage:
    python scripts/score.py --machine intel_i7
    python scripts/score.py --machine intel_i7 --bertscore   # needs `pip install bert-score`

Everything the paper reports is computed here, from raw.jsonl, so any number
in the manuscript can be traced back to a specific model output.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import scoring, stats  # noqa: E402
from bench.tasks import ROOT, LABELS, load_json, load_schema  # noqa: E402

BINARY_KEY = {  # the headline pass/fail metric per task, used for paired tests
    "extraction": "schema_valid",
    "policy": "format_compliant",
    "classification": "correct_strict",
    "drafting": "has_required_signoff",
}


def load_raw(machine: str, preset: str):
    p = ROOT / "results" / machine / preset / "raw.jsonl"
    if not p.exists():
        return [], []
    calls, colds = [], []
    seen = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["kind"] == "cold_start":
            colds.append(r)
        elif r["kind"] == "call" and not r.get("error"):
            # if an item was re-run, keep the last successful attempt
            seen[(r["model_key"], r["task"], r["item_id"], r["temperature"], r["seed"])] = r
    calls = list(seen.values())
    return calls, colds


def score_calls(calls, rouge):
    syl = {s["id"]: s["gold"] for s in load_json("syllabi.json")}
    pol = {p["id"]: p for p in load_json("policies.json")}
    tic = {t["id"]: t["label"] for t in load_json("tickets.json")}
    schema = load_schema()
    for r in calls:
        t, txt, iid = r["task"], r["text"], r["item_id"]
        if t == "extraction":
            r["score"] = scoring.score_extraction(txt, syl[iid], schema)
        elif t == "policy":
            r["score"] = scoring.score_policy(txt, pol[iid], rouge)
        elif t == "classification":
            r["score"] = scoring.score_classification(txt, tic[iid], LABELS)
            r["gold_label"] = tic[iid]
        elif t == "drafting":
            r["score"] = scoring.score_drafting(txt)
        r["truncated"] = bool(r.get("eval_count") and r["eval_count"] >= r["num_predict"])
    return calls


def add_bertscore(calls):
    from bert_score import score as bscore
    pol = {p["id"]: p for p in load_json("policies.json")}
    items = [r for r in calls if r["task"] == "policy" and pol[r["item_id"]].get("reference_summary")]
    if not items:
        return
    cands = [" ".join(scoring.strip_bullet(b) for b in scoring.split_bullets(r["text"])[1]) or r["text"] for r in items]
    refs = [" ".join(pol[r["item_id"]]["reference_summary"]) for r in items]
    _, _, f = bscore(cands, refs, lang="en", rescale_with_baseline=True, verbose=False)
    for r, v in zip(items, f.tolist()):
        r["score"]["bertscore_f"] = v


def prop(rows, key):
    vals = [bool(r["score"][key]) for r in rows if r["score"].get(key) is not None]
    p, lo, hi = stats.wilson(sum(vals), len(vals))
    return {"value": p, "ci_low": lo, "ci_high": hi, "k": sum(vals), "n": len(vals)}


def mean(rows, key):
    v, lo, hi = stats.bootstrap_ci([r["score"].get(key) for r in rows])
    return {"value": v, "ci_low": lo, "ci_high": hi, "n": len(rows)}


def item_mean(rows, key):
    """Average over seeds within each item first, then bootstrap over items."""
    by_item = defaultdict(list)
    for r in rows:
        if r["score"].get(key) is not None:
            by_item[r["item_id"]].append(float(r["score"][key]))
    v, lo, hi = stats.bootstrap_ci([np.mean(x) for x in by_item.values()])
    agree = [len(set(x)) == 1 for x in by_item.values()]
    return {"value": v, "ci_low": lo, "ci_high": hi, "n_items": len(by_item),
            "seed_agreement": (sum(agree) / len(agree)) if agree else None}


def quality_block(rows, task, multi_seed=False):
    agg = item_mean if multi_seed else None
    def P(k):
        return agg(rows, k) if multi_seed else prop(rows, k)
    def M(k):
        return agg(rows, k) if multi_seed else mean(rows, k)
    out = {"n_calls": len(rows), "truncated": sum(r["truncated"] for r in rows)}
    if task == "extraction":
        for k in ["json_valid", "schema_valid", "weight_type_error", "wrapper_text",
                  "course_code_correct", "instructor_correct", "accessibility_correct", "grading_correct"]:
            out[k] = P(k)
        out["field_accuracy"] = M("field_accuracy")
    elif task == "policy":
        for k in ["exactly_three_bullets", "no_preamble", "no_trailing_text", "format_compliant",
                  "all_constraints_retained"]:
            out[k] = P(k)
        for k in ["constraint_retention", "rouge1_f", "rouge2_f", "rougeL_f", "bertscore_f"]:
            if any(r["score"].get(k) is not None for r in rows):
                out[k] = M(k)
    elif task == "classification":
        out["accuracy_strict"] = P("correct_strict")
        out["accuracy_lenient"] = P("correct_lenient")
        out["valid_label_rate"] = P("valid_label")
        if not multi_seed:
            gold = [r["gold_label"] for r in rows]
            pred = [r["score"]["pred_strict"] for r in rows]
            f, lo, hi = stats.macro_f1_ci(gold, pred, LABELS)
            out["macro_f1"] = {"value": f, "ci_low": lo, "ci_high": hi, "n": len(rows)}
            out["confusion"] = stats.confusion(gold, pred, LABELS)
    elif task == "drafting":
        for k in ["has_subject_line", "has_required_signoff", "invented_url", "invented_email",
                  "invented_phone", "uses_placeholders"]:
            out[k] = P(k)
    return out


def systems_block(rows, colds):
    decode = [r for r in rows if r["task"] in ("extraction", "policy", "drafting")]
    itl_ms = [x * 1000 for r in decode for x in r.get("itl_s", [])]
    tps = [r["decode_tps"] for r in decode if r.get("decode_tps")]
    by_task_ttft = {}
    for t in ("extraction", "policy", "classification", "drafting"):
        tt = [r["ttft_s"] for r in rows if r["task"] == t and r.get("ttft_s") is not None]
        if tt:
            by_task_ttft[t] = stats.percentiles(tt, (50, 95))
    prefill = [r["prompt_eval_count"] / (r["prompt_eval_duration_ns"] / 1e9) for r in rows
               if r.get("prompt_eval_count") and r.get("prompt_eval_duration_ns")]
    sizes = [r["model_size_bytes"] for r in rows if r.get("model_size_bytes")]
    rss = [r["peak_ollama_rss_bytes"] for r in rows if r.get("peak_ollama_rss_bytes")]
    chunk_ratio = [r["n_text_chunks"] / r["eval_count"] for r in decode if r.get("eval_count")]
    return {
        "n_calls": len(rows),
        "decode_tps": {"mean": float(np.mean(tps)) if tps else None,
                       "sd": float(np.std(tps, ddof=1)) if len(tps) > 1 else None},
        "prefill_tps_median": float(np.median(prefill)) if prefill else None,
        "itl_ms": stats.percentiles(itl_ms),
        "n_itl_samples": len(itl_ms),
        "chunks_per_token_median": float(np.median(chunk_ratio)) if chunk_ratio else None,
        "ttft_s_by_task": by_task_ttft,
        "model_size_gb": max(sizes) / 1024 ** 3 if sizes else None,
        "model_size_vram_gb": (max(r.get("model_size_vram_bytes") or 0 for r in rows) / 1024 ** 3) if rows else None,
        "peak_ollama_rss_gb": max(rss) / 1024 ** 3 if rss else None,
        "cold_start_load_s": [c["load_duration_ns"] / 1e9 for c in colds if c.get("load_duration_ns")],
    }


def paired_tests(rows, pairs):
    out = {}
    for task, key in BINARY_KEY.items():
        for a, b in pairs:
            ra = {r["item_id"]: bool(r["score"][key]) for r in rows if r["model_key"] == a and r["task"] == task}
            rb = {r["item_id"]: bool(r["score"][key]) for r in rows if r["model_key"] == b and r["task"] == task}
            common = sorted(set(ra) & set(rb))
            if common:
                res = stats.mcnemar_exact([ra[i] for i in common], [rb[i] for i in common])
                out[f"{task}:{key}:{a}_vs_{b}"] = {**res, "n": len(common)}
    return out


def write_csv(calls, path):
    cols = ["preset", "model_key", "task", "item_id", "temperature", "seed", "decode_tps", "ttft_s",
            "eval_count", "truncated"]
    score_keys = sorted({k for r in calls for k, v in r["score"].items() if not isinstance(v, (list, dict))})
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols + score_keys + ["output"])
        for r in sorted(calls, key=lambda r: (r["preset"], r["model_key"], r["task"], r["item_id"])):
            w.writerow([r.get(c) for c in cols] + [r["score"].get(k) for k in score_keys] + [r["text"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", required=True)
    ap.add_argument("--bertscore", action="store_true")
    args = ap.parse_args()

    try:
        from rouge_score import rouge_scorer
        rouge = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    except ImportError:
        rouge = None
        print("rouge-score not installed; skipping ROUGE")

    main_calls, colds = load_raw(args.machine, "main")
    if not main_calls:  # a CPU-only machine label stores its greedy run under cpu_only/
        main_calls, colds = load_raw(args.machine, "cpu_only")
    temp_calls, _ = load_raw(args.machine, "temperature")
    if not main_calls:
        sys.exit(f"No results/{args.machine}/main (or cpu_only)/raw.jsonl yet. Run scripts/run_experiments.py first.")
    score_calls(main_calls, rouge)
    score_calls(temp_calls, rouge)
    if args.bertscore:
        add_bertscore(main_calls + temp_calls)

    models = sorted({r["model_key"] for r in main_calls})
    summary = {"machine": args.machine, "models": models, "quality": {}, "systems": {}, "temperature": {}}
    for m in models:
        rows = [r for r in main_calls if r["model_key"] == m]
        summary["quality"][m] = {t: quality_block([r for r in rows if r["task"] == t], t)
                                 for t in sorted({r["task"] for r in rows})}
        summary["systems"][m] = systems_block(rows, [c for c in colds if c["model_key"] == m])

    for m in sorted({r["model_key"] for r in temp_calls}):
        for T in sorted({r["temperature"] for r in temp_calls}):
            rows = [r for r in temp_calls if r["model_key"] == m and r["temperature"] == T]
            summary["temperature"].setdefault(m, {})[str(T)] = {
                t: quality_block([r for r in rows if r["task"] == t], t, multi_seed=True)
                for t in sorted({r["task"] for r in rows})}

    pairs = [(a, b) for a in models for b in models if a < b]
    tests = paired_tests(main_calls, pairs)
    for k, v in stats.holm({k: v["p"] for k, v in tests.items()}).items():
        tests[k]["p_holm"] = v
    summary["paired_tests"] = tests

    out_dir = ROOT / "results" / args.machine
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(main_calls + temp_calls, out_dir / "per_item.csv")
    print(f"Wrote results/{args.machine}/summary.json and per_item.csv")


if __name__ == "__main__":
    main()
