"""Small, dependency-light statistics used throughout the paper.

Conventions:
* Proportions get Wilson 95% intervals (well behaved near 0% and 100%,
  which matters for N in the tens).
* Means and macro-F1 get percentile bootstrap 95% intervals (2,000 resamples,
  fixed seed so the paper's numbers are reproducible).
* Paired binary comparisons between two configurations on the same items use
  the exact McNemar test.
"""
from __future__ import annotations

import math
import random
from collections import Counter

import numpy as np


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def bootstrap_ci(values, stat=np.mean, n_boot: int = 2000, seed: int = 0):
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not vals:
        return (float("nan"),) * 3
    arr = np.asarray(vals, dtype=float)
    rng = np.random.default_rng(seed)
    boots = [stat(arr[rng.integers(0, len(arr), len(arr))]) for _ in range(n_boot)]
    return float(stat(arr)), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def macro_f1(gold: list[str], pred: list[str], labels: list[str]) -> float:
    f1s = []
    for lab in labels:
        tp = sum(g == lab and p == lab for g, p in zip(gold, pred))
        fp = sum(g != lab and p == lab for g, p in zip(gold, pred))
        fn = sum(g == lab and p != lab for g, p in zip(gold, pred))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return float(np.mean(f1s))


def macro_f1_ci(gold, pred, labels, n_boot: int = 2000, seed: int = 0):
    rng = random.Random(seed)
    idx = list(range(len(gold)))
    point = macro_f1(gold, pred, labels)
    boots = []
    for _ in range(n_boot):
        s = [rng.choice(idx) for _ in idx]
        boots.append(macro_f1([gold[i] for i in s], [pred[i] for i in s], labels))
    return point, float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def mcnemar_exact(a: list[bool], b: list[bool]) -> dict:
    """Exact two-sided McNemar test on paired binary outcomes."""
    b01 = sum((not x) and y for x, y in zip(a, b))
    b10 = sum(x and (not y) for x, y in zip(a, b))
    n = b01 + b10
    if n == 0:
        return {"b01": 0, "b10": 0, "p": 1.0}
    k = min(b01, b10)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return {"b01": b01, "b10": b10, "p": min(1.0, 2 * p)}


def cohen_kappa(r1: list, r2: list, weights: str | None = None, categories=None) -> float:
    pairs = [(x, y) for x, y in zip(r1, r2) if x is not None and y is not None]
    if not pairs:
        return float("nan")
    cats = sorted(categories or {c for p in pairs for c in p})
    k = len(cats)
    pos = {c: i for i, c in enumerate(cats)}
    obs = np.zeros((k, k))
    for x, y in pairs:
        obs[pos[x], pos[y]] += 1
    obs /= obs.sum()
    exp = np.outer(obs.sum(1), obs.sum(0))
    if weights == "quadratic":
        w = np.array([[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)])
    else:
        w = 1 - np.eye(k)
    denom = (w * exp).sum()
    return float(1 - (w * obs).sum() / denom) if denom else float("nan")


def percentiles(values, ps=(50, 95, 99)) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {f"p{p}": None for p in ps}
    return {f"p{p}": float(np.percentile(vals, p)) for p in ps}


def confusion(gold: list[str], pred: list[str], labels: list[str]) -> dict:
    cols = labels + ["INVALID"]
    c = Counter(zip(gold, pred))
    return {g: {p: c.get((g, p), 0) for p in cols} for g in labels}


def holm(pvalues: dict) -> dict:
    """Holm-Bonferroni adjusted p-values for a family of tests."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj
