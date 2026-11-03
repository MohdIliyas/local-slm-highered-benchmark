#!/usr/bin/env python3
"""End-to-end test against the mock server. Run: python tests/test_pipeline.py

Checks that the runner, resume logic, scorer, blind-queue builder, human
scorer and paper-table generator all work together, and that per-token
timing is not distorted by response buffering.
"""
import csv
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import mock_ollama  # noqa: E402

EP = None  # set in main() once the mock server has picked a free port
M = "mock_test"


STEP = [0]


def run(*args):
    STEP[0] += 1
    print(f"[step {STEP[0]}] {' '.join(args)}", flush=True)
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"FAILED: {' '.join(args)}")
    return r.stdout


def main():
    global EP
    srv = mock_ollama.serve(0)  # any free port, so a stale run can't block this one
    EP = f"http://127.0.0.1:{srv.server_port}"
    shutil.rmtree(ROOT / "results" / M, ignore_errors=True)
    he = ROOT / "results" / "human_eval"
    backup = None
    if he.exists():
        backup = ROOT / "results" / "_human_eval_backup"
        shutil.rmtree(backup, ignore_errors=True)
        he.rename(backup)
    try:
        run("scripts/run_experiments.py", "--machine", M, "--preset", "main", "--endpoint", EP)
        out = run("scripts/run_experiments.py", "--machine", M, "--preset", "main", "--endpoint", EP)
        assert out.count("already complete") == 4, "resume should skip all four models"
        run("scripts/run_experiments.py", "--machine", M, "--preset", "temperature", "--endpoint", EP)
        run("scripts/score.py", "--machine", M)
        s = json.loads((ROOT / "results" / M / "summary.json").read_text(encoding="utf-8"))

        q3, q7 = s["quality"]["llama3.2-3b-q4"], s["quality"]["qwen2.5-7b-q4"]
        assert q3["extraction"]["weight_type_error"]["value"] > 0.5, "3B mock emits string weights"
        assert q7["extraction"]["schema_valid"]["value"] == 1.0
        assert q3["policy"]["no_preamble"]["value"] == 0.0 and q7["policy"]["no_preamble"]["value"] == 1.0
        assert q3["drafting"]["invented_phone"]["value"] == 1.0 and q7["drafting"]["invented_phone"]["value"] == 0.0
        assert "rougeL_f" in q7["policy"]
        for m, sy in s["systems"].items():
            assert sy["itl_ms"]["p50"] > 0.3, f"{m}: ITL p50 {sy['itl_ms']['p50']} -> tokens are being bundled"
            assert sy["chunks_per_token_median"] == 1.0
            assert sy["model_size_gb"] and sy["cold_start_load_s"]
        assert s["systems"]["qwen2.5-7b-q4"]["itl_ms"]["p50"] > s["systems"]["llama3.2-3b-q4"]["itl_ms"]["p50"]
        assert s["systems"]["qwen2.5-7b-q8"]["model_size_gb"] > s["systems"]["qwen2.5-7b-q4"]["model_size_gb"]
        assert set(s["temperature"]) == {"llama3.2-3b-q4", "qwen2.5-7b-q4"}
        assert any(k.startswith("extraction:schema_valid:llama3.2-3b-q4_vs_qwen2.5-7b-q4") for k in s["paired_tests"])

        run("scripts/make_blind_queue.py", "--machine", M, "--raters", "r1", "r2")
        key = json.loads((he / "key" / "blind_key.json").read_text(encoding="utf-8"))
        queue = (he / "queue.md").read_text(encoding="utf-8")
        assert len(key) == 4 * (16 + 16)
        assert not any(m in queue for m in ["llama", "qwen"]), "model names leaked into the blind queue"
        rng = random.Random(0)
        for rater in ("r1", "r2"):
            p = he / f"ratings_{rater}.csv"
            rows = list(csv.DictReader(p.open(encoding="utf-8")))
            for r in rows:
                bad = "llama" in key[r["blind_id"]]["model_key"]
                r["quality_1to5"] = str(rng.choice([2, 3]) if bad else rng.choice([4, 5]))
                r["needs_substantive_edit_YN"] = "Y" if bad and rng.random() < 0.8 else "N"
                r["factual_error_YN"] = "Y" if bad and rng.random() < 0.5 else "N"
            with p.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=rows[0].keys())
                w.writeheader()
                w.writerows(rows)
        run("scripts/score_human.py")
        hs = json.loads((he / "summary.json").read_text(encoding="utf-8"))
        assert hs["agreement"]["quality_weighted_kappa"] > 0.5
        assert hs["cost_sensitivity"]["per_model"]

        run("scripts/make_paper_tables.py", "--machines", M, "--primary", M)
        macros = (ROOT / "paper" / "generated" / "macros.tex").read_text(encoding="utf-8")
        line = next(l for l in macros.splitlines() if r"\TpsmocktestQwenQfour}" in l)
        assert "tbd" not in line, "measured value should replace the placeholder"
        print("ALL CHECKS PASSED")
        print(json.dumps({m: {"itl_ms": v["itl_ms"], "size_gb": round(v["model_size_gb"], 2)}
                          for m, v in s["systems"].items()}, indent=1))
    finally:
        srv.shutdown()
        shutil.rmtree(ROOT / "results" / M, ignore_errors=True)
        shutil.rmtree(he, ignore_errors=True)
        if backup:
            backup.rename(he)
        gen = ROOT / "paper" / "generated"
        # regenerate placeholders so the test leaves no fake numbers in the paper
        subprocess.run([sys.executable, "scripts/make_paper_tables.py"], cwd=ROOT, capture_output=True)


if __name__ == "__main__":
    main()
