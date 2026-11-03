"""Per-item scoring. Every function takes one model output and one gold item
and returns a flat dict of metrics, so results can be aggregated uniformly.
"""
from __future__ import annotations

import json
import re

import jsonschema

BULLET_RE = re.compile(r"^\s*(?:[-*\u2022\u2013\u25cf>]|\d+[.)])\s+")

NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15",
    "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
    "twenty": "20", "twenty-one": "21", "twenty one": "21", "thirty": "30",
    "forty-five": "45", "forty five": "45", "sixty": "60", "ninety": "90",
}


def normalize_text(s: str) -> str:
    """Lowercase, spell numbers as digits, unify percent forms and spacing."""
    s = s.lower().replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("**", "").replace("__", "")
    for word in sorted(NUMBER_WORDS, key=len, reverse=True):
        s = re.sub(rf"\b{word}\b", NUMBER_WORDS[word], s)
    s = re.sub(r"(\d)\s*(?:percent|per cent)\b", r"\1%", s)
    s = re.sub(r"(\d)\s+%", r"\1%", s)
    s = re.sub(r"\(\d+\)", "", s)  # "ten (10) days" -> "10 days" after word mapping
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


# --------------------------------------------------------------------------
# Task 1: syllabus extraction
# --------------------------------------------------------------------------
def extract_json_object(raw: str):
    """Return (parsed_or_None, had_wrapper_text)."""
    stripped = raw.strip()
    fenced = re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped, flags=re.S).strip()
    start, end = fenced.find("{"), fenced.rfind("}")
    if start == -1 or end <= start:
        return None, True
    candidate = fenced[start:end + 1]
    wrapper = bool(stripped[:1] != "{" or stripped[-1:] != "}")
    try:
        return json.loads(candidate), wrapper
    except json.JSONDecodeError:
        return None, wrapper


def _norm_code(s) -> str:
    return re.sub(r"[\s\-_]", "", str(s or "")).upper()


def _norm_name(s) -> set[str]:
    s = str(s or "").lower().replace(".", "")
    stop = {"dr", "prof", "professor", "profesora", "mr", "ms", "mrs", "phd", "edd", "msn", "rn",
            "mfa", "mba", "md", "pe", "he", "him", "she", "her", "they", "them"}
    return {t for t in re.findall(r"[a-z]+", s) if len(t) > 1 and t not in stop}


def _to_float(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.search(r"-?\d+(?:\.\d+)?", v)
        return float(m.group()) if m else None
    return None


def _group(category: str) -> str:
    """'Exam 2' -> 'exam', 'Midterm II' -> 'midterm', 'Project 3' -> 'project'."""
    return re.sub(r"\s+(\d+|[ivx]+)$", "", category.strip().lower())


def _gold_weight_variants(gold: dict) -> list[list[float]]:
    """Accept itemized ('Exam 1 15, Exam 2 15') or merged ('Exams 30') answers."""
    split = sorted(float(g["weight_percent"]) for g in gold["grading_breakdown"])
    merged = {}
    for g in gold["grading_breakdown"]:
        merged[_group(g["category"])] = merged.get(_group(g["category"]), 0.0) + float(g["weight_percent"])
    return [split, sorted(merged.values())]


def _weights_match(pred: list[float], gold: list[float]) -> bool:
    return len(pred) == len(gold) and all(abs(a - b) < 0.51 for a, b in zip(pred, gold))


def score_extraction(raw: str, gold: dict, schema: dict) -> dict:
    parsed, wrapper = extract_json_object(raw)
    out = {
        "json_valid": parsed is not None,
        "wrapper_text": wrapper,
        "schema_valid": False,
        "weight_type_error": False,
        "course_code_correct": False,
        "instructor_correct": False,
        "accessibility_correct": False,
        "grading_correct": False,
    }
    if not isinstance(parsed, dict):
        out["field_accuracy"] = 0.0
        return out
    try:
        jsonschema.validate(parsed, schema)
        out["schema_valid"] = True
    except jsonschema.ValidationError:
        pass

    grading = parsed.get("grading_breakdown") or []
    if isinstance(grading, list):
        out["weight_type_error"] = any(
            isinstance(g, dict) and isinstance(g.get("weight_percent"), str) for g in grading)
        pred_w = sorted(w for w in (_to_float(g.get("weight_percent")) for g in grading
                                    if isinstance(g, dict)) if w is not None)
    else:
        pred_w = []
    out["grading_correct"] = any(_weights_match(pred_w, g) for g in _gold_weight_variants(gold))
    out["course_code_correct"] = _norm_code(parsed.get("course_code")) == _norm_code(gold["course_code"])
    gold_name = _norm_name(gold["instructor_name"])
    out["instructor_correct"] = bool(gold_name) and gold_name <= _norm_name(parsed.get("instructor_name"))
    out["accessibility_correct"] = parsed.get("has_accessibility_statement") is gold["has_accessibility_statement"]
    fields = ["course_code_correct", "instructor_correct", "accessibility_correct", "grading_correct"]
    out["field_accuracy"] = sum(out[f] for f in fields) / len(fields)
    return out


# --------------------------------------------------------------------------
# Task 2: policy summarization
# --------------------------------------------------------------------------
def split_bullets(text: str) -> tuple[list[str], list[str]]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    bullets = [l for l in lines if BULLET_RE.match(l)]
    return lines, bullets


def strip_bullet(line: str) -> str:
    return BULLET_RE.sub("", line).replace("**", "").strip()


def _contains(haystack: str, needle: str) -> bool:
    """Whole-phrase match: '5 business days' must not match '15 business days'."""
    return re.search(rf"(?<![\w$.]){re.escape(needle)}(?![\w%])", haystack) is not None


def score_policy(raw: str, gold: dict, rouge_scorer=None) -> dict:
    lines, bullets = split_bullets(raw)
    norm = normalize_text(raw)
    # a constraint is a string, or a list of acceptable surface forms
    alts = [c if isinstance(c, list) else [c] for c in gold["constraints"]]
    hits = [any(_contains(norm, normalize_text(a)) for a in group) for group in alts]
    out = {
        "n_bullets": len(bullets),
        "exactly_three_bullets": len(bullets) == 3,
        "no_preamble": bool(lines) and bool(BULLET_RE.match(lines[0])),
        "no_trailing_text": bool(lines) and bool(BULLET_RE.match(lines[-1])),
        "constraint_retention": sum(hits) / len(hits) if hits else None,
        "all_constraints_retained": all(hits) if hits else None,
        "missed_constraints": [g[0] for g, h in zip(alts, hits) if not h],
    }
    out["format_compliant"] = out["exactly_three_bullets"] and out["no_preamble"] and out["no_trailing_text"]
    if rouge_scorer is not None and gold.get("reference_summary"):
        pred = " ".join(strip_bullet(b) for b in bullets) if bullets else raw
        ref = " ".join(gold["reference_summary"])
        sc = rouge_scorer.score(ref, pred)
        out.update({"rouge1_f": sc["rouge1"].fmeasure, "rouge2_f": sc["rouge2"].fmeasure,
                    "rougeL_f": sc["rougeL"].fmeasure})
    return out


# --------------------------------------------------------------------------
# Task 3: ticket classification
# --------------------------------------------------------------------------
def score_classification(raw: str, gold_label: str, labels: list[str]) -> dict:
    cleaned = raw.strip().strip("`*\"' .").splitlines()[0].strip() if raw.strip() else ""
    cleaned = re.sub(r"^(category|label)\s*:\s*", "", cleaned, flags=re.I).strip("`*\"' .")
    strict = next((l for l in labels if l.lower() == cleaned.lower()), None)
    mentioned = [l for l in labels if l.lower() in raw.lower()]
    lenient = strict or (mentioned[0] if len(mentioned) == 1 else None)
    return {
        "pred_strict": strict or "INVALID",
        "pred_lenient": lenient or "INVALID",
        "valid_label": strict is not None,
        "correct_strict": strict == gold_label,
        "correct_lenient": lenient == gold_label,
    }


# --------------------------------------------------------------------------
# Task 4: reply drafting (automatic checks only; quality is human-rated)
# --------------------------------------------------------------------------
URL_RE = re.compile(r"https?://|www\.", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}")
PLACEHOLDER_RE = re.compile(r"\[[^\]]{2,40}\]")


def score_drafting(raw: str) -> dict:
    text = raw.strip()
    return {
        "has_subject_line": bool(re.match(r"^\**subject\s*:", text, re.I)),
        "has_required_signoff": "academic support services" in text.lower()[-200:],
        "invented_url": bool(URL_RE.search(text)),
        "invented_email": bool(EMAIL_RE.search(text)),
        "invented_phone": bool(PHONE_RE.search(text)),
        "uses_placeholders": bool(PLACEHOLDER_RE.search(text)),
        "n_words": len(text.split()),
    }
