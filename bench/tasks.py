"""Loads task data and builds prompts. One place defines what each task is."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "tasks"
PROMPTS = ROOT / "prompts"

LABELS = [
    "LMS Access", "Grade Disputes", "Online Proctoring", "Accessibility/Captions",
    "Course Enrollment", "Login/Account Lockout", "Exam Rescheduling", "General Inquiries",
]

# Generation length caps per task (tokens). Generous enough not to truncate
# correct answers; logged so truncation can be audited.
NUM_PREDICT = {"extraction": 512, "policy": 384, "classification": 16, "drafting": 600}


def _read(path: Path):
    return path.read_text(encoding="utf-8-sig")


def load_json(name: str):
    return json.loads(_read(DATA / name))


def load_schema() -> dict:
    return json.loads(_read(ROOT / "data" / "syllabi" / "schema.json"))


def template(name: str) -> str:
    return _read(PROMPTS / f"{name}_prompt.txt")


def build_items(task: str) -> list[dict]:
    """Return [{'id', 'prompt', 'gold'}] for a task."""
    if task == "extraction":
        tmpl = template("extraction")
        return [{"id": s["id"], "prompt": tmpl.replace("{{SYLLABUS_TEXT}}", s["text"]), "gold": s["gold"]}
                for s in load_json("syllabi.json")]
    if task == "policy":
        tmpl = template("policy")
        return [{"id": p["id"], "prompt": tmpl.replace("{{POLICY_TEXT}}", p["text"]), "gold": p}
                for p in load_json("policies.json")]
    if task == "classification":
        tmpl = template("classification")
        return [{"id": t["id"], "prompt": tmpl.replace("{{TICKET_TEXT}}", t["text"]), "gold": t["label"]}
                for t in load_json("tickets.json")]
    if task == "drafting":
        tmpl = template("drafting")
        return [{"id": t["id"], "prompt": tmpl.replace("{{STUDENT_INQUIRY}}", t["text"]), "gold": t["label"]}
                for t in load_json("tickets.json") if t.get("use_for_drafting")]
    raise ValueError(f"unknown task {task}")
