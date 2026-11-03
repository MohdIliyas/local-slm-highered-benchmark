#!/usr/bin/env python3
"""Score human ratings: agreement, Human Intervention Rate (HIR), cost sensitivity.

Usage:
    python scripts/score_human.py

HIR definition (stated in the paper): the share of outputs a rater judged to
need a substantive edit before they could be sent or published. Reported per
rater, plus a consensus value: items where raters disagree are resolved by
results/human_eval/adjudication.csv (columns blind_id, needs_substantive_edit_YN)
if it exists; otherwise lower ("both raters flagged") and upper ("either rater
flagged") bounds are reported.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import stats  # noqa: E402
from bench.tasks import ROOT  # noqa: E402

HE = ROOT / "results" / "human_eval"


def yn(v):
    v = (v or "").strip().upper()
    return True if v in ("Y", "YES", "1", "TRUE") else False if v in ("N", "NO", "0", "FALSE") else None


def load_ratings():
    raters = {}
    for p in sorted(HE.glob("ratings_*.csv")):
        rows = {}
        for r in csv.DictReader(p.open(encoding="utf-8-sig")):
            q = r["quality_1to5"].strip()
            rows[r["blind_id"]] = {"quality": int(q) if q else None,
                                   "edit": yn(r["needs_substantive_edit_YN"]),
                                   "factual": yn(r["factual_error_YN"])}
        if any(v["quality"] is not None for v in rows.values()):
            raters[p.stem.removeprefix("ratings_")] = rows
    return raters


def main():
    key_path = HE / "key" / "blind_key.json"
    if not key_path.exists():
        sys.exit("No blind key; run scripts/make_blind_queue.py first.")
    key = json.loads(key_path.read_text(encoding="utf-8"))
    raters = load_ratings()
    if not raters:
        sys.exit("No completed ratings_*.csv files yet.")
    adjud = {}
    ap = HE / "adjudication.csv"
    if ap.exists():
        adjud = {r["blind_id"]: yn(r["needs_substantive_edit_YN"]) for r in csv.DictReader(ap.open(encoding="utf-8-sig"))}

    names = sorted(raters)
    summary = {"raters": names, "n_items": len(key), "agreement": {}, "by_model_task": {}}
    if len(names) >= 2:
        a, b = raters[names[0]], raters[names[1]]
        ids = [i for i in key if i in a and i in b]
        summary["agreement"] = {
            "pair": names[:2],
            "quality_weighted_kappa": stats.cohen_kappa([a[i]["quality"] for i in ids], [b[i]["quality"] for i in ids],
                                                        weights="quadratic", categories=[1, 2, 3, 4, 5]),
            "edit_kappa": stats.cohen_kappa([a[i]["edit"] for i in ids], [b[i]["edit"] for i in ids]),
            "edit_percent_agreement": float(np.mean([a[i]["edit"] == b[i]["edit"] for i in ids
                                                     if a[i]["edit"] is not None and b[i]["edit"] is not None])),
            "factual_kappa": stats.cohen_kappa([a[i]["factual"] for i in ids], [b[i]["factual"] for i in ids]),
            "n_disagreements_edit": sum(a[i]["edit"] != b[i]["edit"] for i in ids),
            "adjudicated": len(adjud),
        }

    groups = defaultdict(list)
    for bid, k in key.items():
        groups[(k["model_key"], k["task"])].append(bid)
    for (m, t), ids in sorted(groups.items()):
        block = {"n": len(ids)}
        for name in names:
            r = raters[name]
            q = [r[i]["quality"] for i in ids if i in r and r[i]["quality"] is not None]
            e = [r[i]["edit"] for i in ids if i in r and r[i]["edit"] is not None]
            f = [r[i]["factual"] for i in ids if i in r and r[i]["factual"] is not None]
            block[name] = {"mean_quality": float(np.mean(q)) if q else None,
                           "hir": stats.wilson(sum(e), len(e)) if e else None,
                           "factual_error_rate": stats.wilson(sum(f), len(f)) if f else None}
        if len(names) >= 2:
            both, either, cons = [], [], []
            for i in ids:
                flags = [raters[n][i]["edit"] for n in names if i in raters[n] and raters[n][i]["edit"] is not None]
                if len(flags) < 2:
                    continue
                both.append(all(flags)); either.append(any(flags))
                cons.append(adjud.get(i, flags[0]) if len(set(flags)) > 1 else flags[0])
            block["hir_lower_both"] = stats.wilson(sum(both), len(both))
            block["hir_upper_either"] = stats.wilson(sum(either), len(either))
            if adjud:
                block["hir_consensus"] = stats.wilson(sum(cons), len(cons))
        summary["by_model_task"][f"{m}|{t}"] = block

    cfg = json.loads((ROOT / "configs" / "experiments.json").read_text(encoding="utf-8"))["cost_model_assumptions"]
    cost = {"assumptions": cfg, "per_model": {}}
    for k, block in summary["by_model_task"].items():
        m, t = k.split("|")
        if t != "drafting":
            continue
        hirs = [block[n]["hir"][0] for n in names if block.get(n, {}).get("hir")]
        if not hirs:
            continue
        hir = float(np.mean(hirs))
        per_ticket = cfg["minutes_manual_draft"] - cfg["minutes_review_ok_draft"] - hir * cfg["minutes_fix_flagged_draft"]
        cost["per_model"][m] = {"hir_mean_of_raters": hir, "minutes_saved_per_ticket": per_ticket,
                                "hours_saved_per_month": per_ticket * cfg["monthly_ticket_volume"] / 60}
    summary["cost_sensitivity"] = cost
    (HE / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Wrote results/human_eval/summary.json")


if __name__ == "__main__":
    main()
