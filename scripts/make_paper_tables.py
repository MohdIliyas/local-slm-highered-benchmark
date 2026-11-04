#!/usr/bin/env python3
"""Write paper/generated/*.tex from results. Never type a number into main.tex.

Usage:
    python scripts/make_paper_tables.py                       # intel_i7 + apple_m4
    python scripts/make_paper_tables.py --machines intel_i7   # one machine

Anything not yet measured renders as \\tbd (a red [TBD] in the PDF), so a
missing experiment is visible instead of silently filled in.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.tasks import ROOT, load_json  # noqa: E402

GEN = ROOT / "paper" / "generated"
MODELS = ["llama3.2-3b-q4", "llama3.2-3b-q8", "qwen2.5-7b-q4", "qwen2.5-7b-q8"]
PRETTY = {"llama3.2-3b-q4": r"Llama 3.2 3B & \texttt{Q4\_K\_M}",
          "llama3.2-3b-q8": r"Llama 3.2 3B & \texttt{Q8\_0}",
          "qwen2.5-7b-q4": r"Qwen 2.5 7B & \texttt{Q4\_K\_M}",
          "qwen2.5-7b-q8": r"Qwen 2.5 7B & \texttt{Q8\_0}"}
MACRO = {"llama3.2-3b-q4": "LlamaQfour", "llama3.2-3b-q8": "LlamaQeight",
         "qwen2.5-7b-q4": "QwenQfour", "qwen2.5-7b-q8": "QwenQeight"}
MACHINE_MACRO = {"intel_i7": "Intel", "intel_i7_cpu": "IntelNoGPU", "apple_m4": "Apple"}
MACHINE_LABEL = {"intel_i7": "Windows laptop, GPU offload (Ollama default)",
                 "intel_i7_cpu": "Windows laptop, CPU only (\\texttt{num\\_gpu}=0)",
                 "apple_m4": "Apple M4 (Metal)"}
TBD = r"\tbd{}"


def get(d, *path):
    for p in path:
        if not isinstance(d, dict) or p not in d or d[p] is None:
            return None
        d = d[p]
    return d


def pct(block, digits=0):
    v = get(block, "value")
    return TBD if v is None else f"{100 * v:.{digits}f}"


def pct_ci(block):
    v = get(block, "value")
    if v is None:
        return TBD
    return rf"{100 * v:.0f} {{\scriptsize[{100 * block['ci_low']:.0f}, {100 * block['ci_high']:.0f}]}}"


def num(v, fmt="{:.1f}"):
    return TBD if v is None else fmt.format(v)


def invented_pct(drafting_block):
    """Share of drafts that invented a URL, e-mail address or phone number (worst of the three)."""
    if drafting_block is None:
        return TBD
    vals = [get(drafting_block, k, "value") or 0 for k in ("invented_url", "invented_email", "invented_phone")]
    return f"{100 * max(vals):.0f}"


def tex_escape(s: str) -> str:
    return str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("%", r"\%") \
        .replace("&", r"\&").replace("#", r"\#").replace("(R)", "").replace("(TM)", "")


def load_summary(machine):
    p = ROOT / "results" / machine / "summary.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_manifest(machine):
    ms = sorted((ROOT / "results" / machine / "main").glob("manifest_*.json")) or \
        sorted((ROOT / "results" / machine / "cpu_only").glob("manifest_*.json"))
    return json.loads(ms[-1].read_text(encoding="utf-8")) if ms else None


def _raw_calls(machine, preset):
    p = ROOT / "results" / machine / preset / "raw.jsonl"
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("kind") == "call" and not r.get("error"):
            out[(r["model_key"], r["task"], r["item_id"], r["temperature"], r["seed"])] = r
    return out


def extra_macros(sums, primary_machine) -> list[str]:
    """Numbers the prose cites that are not in a table, computed from raw logs."""
    import statistics as st
    L = ["% ---- prose numbers (from raw logs)"]
    for machine, preset in [("intel_i7", "main"), ("intel_i7_cpu", "cpu_only"), ("apple_m4", "main")]:
        mm = MACHINE_MACRO[machine]
        calls = _raw_calls(machine, preset)
        sy = get(sums.get(machine) or {}, "systems") or {}
        for model in MODELS:
            k = f"{mm}{MACRO[model]}"
            w = [r["wall_s"] for key, r in calls.items() if key[0] == model and key[1] == "drafting"]
            L.append(rf"\newcommand{{\DraftSec{k}}}{{{num(st.median(w)) if w else TBD}}}")
            L.append(rf"\newcommand{{\Ttft{k}}}{{{num(get(sy, model, 'ttft_s_by_task', 'policy', 'p50'), '{:.2f}')}}}")
    gpu, cpu = _raw_calls("intel_i7", "main"), _raw_calls("intel_i7_cpu", "cpu_only")
    common = [k for k in gpu if k in cpu]
    L.append(rf"\newcommand{{\IdentGpuCpu}}{{{sum(gpu[k]['text'] == cpu[k]['text'] for k in common) if common else TBD}}}")
    L.append(rf"\newcommand{{\NIdentCompared}}{{{len(common) if common else TBD}}}")
    old = {}
    ap = ROOT / "results" / "archive" / "intel_i7_main_run1" / "raw.jsonl"
    if ap.exists():
        for line in ap.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("kind") == "call":
                old[(r["model_key"], r["task"], r["item_id"], r["temperature"], r["seed"])] = r
    rc = [k for k in gpu if k in old]
    L.append(rf"\newcommand{{\IdentRerun}}{{{sum(gpu[k]['text'] == old[k]['text'] for k in rc) if rc else TBD}}}")
    L.append(rf"\newcommand{{\NRerunCompared}}{{{len(rc) if rc else TBD}}}")
    pt = get(sums.get(primary_machine) or {}, "paired_tests") or {}
    def test(task, key, a, b):
        return pt.get(f"{task}:{key}:{a}_vs_{b}") or {}
    t = test("extraction", "schema_valid", "llama3.2-3b-q4", "llama3.2-3b-q8")
    L += [rf"\newcommand{{\QuantLlamaSchemaImp}}{{{t.get('b01', TBD)}}}",
          rf"\newcommand{{\QuantLlamaSchemaWor}}{{{t.get('b10', TBD)}}}",
          rf"\newcommand{{\QuantLlamaSchemaP}}{{{num(t.get('p'), '{:.3f}')}}}",
          rf"\newcommand{{\QuantLlamaSchemaHolm}}{{{num(t.get('p_holm'), '{:.3f}')}}}"]
    quant = [v.get("p_holm") for k, v in pt.items()
             if k.split(":")[2] in ("llama3.2-3b-q4_vs_llama3.2-3b-q8", "qwen2.5-7b-q4_vs_qwen2.5-7b-q8")]
    L.append(rf"\newcommand{{\MinHolmQuant}}{{{num(min(quant), '{:.2f}') if quant else TBD}}}")
    size = [v.get("p_holm") for k, v in pt.items()
            if k.split(":")[0] in ("extraction", "policy", "classification")
            and k.split(":")[2].startswith("llama") and "_vs_qwen" in k.split(":")[2]]
    L.append(rf"\newcommand{{\MaxHolmSize}}{{{num(max(size), '{:.3f}') if size else TBD}}}")
    L.append(rf"\newcommand{{\NSizeSig}}{{{sum(p < 0.05 for p in size) if size else TBD}}}")
    L.append(rf"\newcommand{{\NSizeTests}}{{{len(size) if size else TBD}}}")
    temp = get(sums.get(primary_machine) or {}, "temperature") or {}
    for model in ("llama3.2-3b-q4", "qwen2.5-7b-q4"):
        for T, tag in (("0.2", "Lo"), ("0.7", "Hi")):
            tb = get(temp, model, T) or {}
            k = f"{MACRO[model]}{tag}"
            sa = get(tb, "extraction", "schema_valid", "seed_agreement")
            ca = get(tb, "classification", "accuracy_strict", "seed_agreement")
            L += [rf"\newcommand{{\TempSchema{k}}}{{{pct(get(tb, 'extraction', 'schema_valid'))}}}",
                  rf"\newcommand{{\TempAgreeSchema{k}}}{{{num(sa * 100 if sa is not None else None, '{:.0f}')}}}",
                  rf"\newcommand{{\TempAcc{k}}}{{{pct(get(tb, 'classification', 'accuracy_strict'))}}}",
                  rf"\newcommand{{\TempAgreeAcc{k}}}{{{num(ca * 100 if ca is not None else None, '{:.0f}')}}}",
                  rf"\newcommand{{\TempAllRetain{k}}}{{{pct(get(tb, 'policy', 'all_constraints_retained'))}}}"]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machines", nargs="+", default=["intel_i7", "intel_i7_cpu", "apple_m4"])
    ap.add_argument("--primary", default="intel_i7", help="machine whose quality results the paper reports")
    args = ap.parse_args()
    GEN.mkdir(parents=True, exist_ok=True)

    sums = {m: load_summary(m) for m in args.machines}
    mans = {m: load_manifest(m) for m in args.machines}
    primary = sums.get(args.primary)
    human_p = ROOT / "results" / "human_eval" / "summary.json"
    human = json.loads(human_p.read_text(encoding="utf-8")) if human_p.exists() else None

    # ---------------------------------------------------------------- macros
    L = ["% AUTO-GENERATED by scripts/make_paper_tables.py -- do not edit by hand.",
         "% ---- dataset sizes (from data/tasks)"]
    L.append(rf"\newcommand{{\NSyllabi}}{{{len(load_json('syllabi.json'))}}}")
    L.append(rf"\newcommand{{\NPolicies}}{{{len(load_json('policies.json'))}}}")
    L.append(rf"\newcommand{{\NTickets}}{{{len(load_json('tickets.json'))}}}")
    L.append(rf"\newcommand{{\NDrafting}}{{{sum(t.get('use_for_drafting', False) for t in load_json('tickets.json'))}}}")
    L.append(rf"\newcommand{{\NConstraints}}{{{sum(len(p['constraints']) for p in load_json('policies.json'))}}}")
    L.append("% ---- values")
    for machine in args.machines:
        mm = MACHINE_MACRO.get(machine, machine.replace("_", ""))
        man = mans.get(machine) or {}
        L.append(rf"\newcommand{{\{mm}CPU}}{{{tex_escape(man['cpu']) if man.get('cpu') else TBD}}}")
        L.append(rf"\newcommand{{\{mm}RAM}}{{{man['ram_total_gb'] if man.get('ram_total_gb') else TBD}}}")
        raw_gpus = man.get("gpus") or []
        smi = [g.split(":", 1)[-1].strip() if g.startswith("nvidia-smi:") else g.replace("NVIDIA NVIDIA", "NVIDIA", 1)
               for g in raw_gpus if g.startswith(("nvidia-smi:", "NVIDIA"))]
        gpus = [re.sub(r",\s*(\d+)\s*MiB", lambda m: f", {round(int(m.group(1)) / 1024)} GB", g) for g in smi] \
            or [g.removeprefix("adapter: ") for g in raw_gpus]
        L.append(rf"\newcommand{{\{mm}GPU}}{{{tex_escape('; '.join(gpus)) if gpus else TBD}}}")
        L.append(rf"\newcommand{{\{mm}OS}}{{{tex_escape(man['os']) if man.get('os') else TBD}}}")
        L.append(rf"\newcommand{{\{mm}Ollama}}{{{tex_escape(man['ollama_version']) if man.get('ollama_version') else TBD}}}")
        s = sums.get(machine) or {}
        for model in MODELS:
            sy = get(s, "systems", model) or {}
            key = f"{mm}{MACRO[model]}"
            L.append(rf"\newcommand{{\Tps{key}}}{{{num(get(sy, 'decode_tps', 'mean'))}}}")
            L.append(rf"\newcommand{{\Itl{key}}}{{{num(get(sy, 'itl_ms', 'p50'))}}}")
            L.append(rf"\newcommand{{\ItlNineNine{key}}}{{{num(get(sy, 'itl_ms', 'p99'))}}}")
            L.append(rf"\newcommand{{\Size{key}}}{{{num(get(sy, 'model_size_gb'))}}}")
    q = (primary or {}).get("quality", {})
    for model in MODELS:
        k = MACRO[model]
        qm = q.get(model, {})
        L += [rf"\newcommand{{\Schema{k}}}{{{pct(get(qm, 'extraction', 'schema_valid'))}}}",
              rf"\newcommand{{\FieldAcc{k}}}{{{pct(get(qm, 'extraction', 'field_accuracy'))}}}",
              rf"\newcommand{{\TypeErr{k}}}{{{pct(get(qm, 'extraction', 'weight_type_error'))}}}",
              rf"\newcommand{{\Wrap{k}}}{{{pct(get(qm, 'extraction', 'wrapper_text'))}}}",
              rf"\newcommand{{\Format{k}}}{{{pct(get(qm, 'policy', 'format_compliant'))}}}",
              rf"\newcommand{{\Preamble{k}}}{{{pct(get(qm, 'policy', 'no_preamble'))}}}",
              rf"\newcommand{{\Retain{k}}}{{{pct(get(qm, 'policy', 'constraint_retention'))}}}",
              rf"\newcommand{{\AllRetain{k}}}{{{pct(get(qm, 'policy', 'all_constraints_retained'))}}}",
              rf"\newcommand{{\Acc{k}}}{{{pct(get(qm, 'classification', 'accuracy_strict'))}}}",
              rf"\newcommand{{\AccLenient{k}}}{{{pct(get(qm, 'classification', 'accuracy_lenient'))}}}",
              rf"\newcommand{{\MacroFone{k}}}{{{num(get(qm, 'classification', 'macro_f1', 'value'), '{:.2f}')}}}",
              rf"\newcommand{{\Invented{k}}}{{{invented_pct(get(qm, 'drafting'))}}}"]
        hb = get(human, "by_model_task", f"{model}|drafting") or {}
        raters = (human or {}).get("raters", [])
        hirs = [get(hb, r, "hir") for r in raters if get(hb, r, "hir")]
        hir = sum(h[0] for h in hirs) / len(hirs) if hirs else None
        L.append(rf"\newcommand{{\Hir{k}}}{{{num(hir * 100 if hir is not None else None, '{:.0f}')}}}")
    ag = (human or {}).get("agreement", {})
    L.append(rf"\newcommand{{\KappaQuality}}{{{num(ag.get('quality_weighted_kappa'), '{:.2f}')}}}")
    L.append(rf"\newcommand{{\KappaEdit}}{{{num(ag.get('edit_kappa'), '{:.2f}')}}}")
    L.append(rf"\newcommand{{\NRated}}{{{(human or {}).get('n_items') or TBD}}}")
    cs = json.loads((ROOT / "configs" / "experiments.json").read_text(encoding="utf-8")).get("cost_model_assumptions", {})
    for name, key in [("CostManual", "minutes_manual_draft"), ("CostReview", "minutes_review_ok_draft"),
                      ("CostFix", "minutes_fix_flagged_draft"), ("CostVolume", "monthly_ticket_volume")]:
        L.append(rf"\newcommand{{\{name}}}{{{cs[key] if key in cs else TBD}}}")
    L += extra_macros(sums, args.primary)
    (GEN / "macros.tex").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- systems table
    T = [r"\begin{tabular}{llrrrrrrr}", r"\toprule",
         r" & & Size & Decode & Prefill & TTFT & \multicolumn{3}{c}{Inter-token latency (ms)} \\",
         r"\cmidrule(lr){7-9}",
         r"Model & Quant. & (GB) & (tok/s) & (tok/s) & p50 (s) & p50 & p95 & p99 \\", r"\midrule"]
    for i, machine in enumerate(args.machines):
        if i:
            T.append(r"\midrule")
        label = MACHINE_LABEL.get(machine, tex_escape(machine))
        T.append(rf"\multicolumn{{9}}{{l}}{{\textit{{{label}}}}} \\")
        s = sums.get(machine) or {}
        for model in MODELS:
            sy = get(s, "systems", model) or {}
            tps, sd = get(sy, "decode_tps", "mean"), get(sy, "decode_tps", "sd")
            dec = TBD if tps is None else (f"{tps:.1f} $\\pm$ {sd:.1f}" if sd is not None else f"{tps:.1f}")
            T.append(rf"{PRETTY[model]} & {num(get(sy, 'model_size_gb'))} & {dec} & "
                     rf"{num(get(sy, 'prefill_tps_median'), '{:.0f}')} & "
                     rf"{num(get(sy, 'ttft_s_by_task', 'policy', 'p50'), '{:.2f}')} & "
                     rf"{num(get(sy, 'itl_ms', 'p50'))} & {num(get(sy, 'itl_ms', 'p95'))} & {num(get(sy, 'itl_ms', 'p99'))} \\")
    T += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_systems.tex").write_text("\n".join(T) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- quality table
    Q = [r"\begin{tabular}{llrrrrrrr}", r"\toprule",
         r" & & \multicolumn{3}{c}{Extraction} & \multicolumn{2}{c}{Policy summary} & \multicolumn{2}{c}{Classification} \\",
         r"\cmidrule(lr){3-5}\cmidrule(lr){6-7}\cmidrule(lr){8-9}",
         r"Model & Quant. & Schema \% & Fields \% & Str.\ wt.\ \% & Format \% & Constr.\ \% & Acc.\ \% & Macro-F1 \\",
         r"\midrule"]
    for model in MODELS:
        qm = q.get(model, {})
        Q.append(rf"{PRETTY[model]} & {pct_ci(get(qm, 'extraction', 'schema_valid'))} & "
                 rf"{pct(get(qm, 'extraction', 'field_accuracy'))} & {pct(get(qm, 'extraction', 'weight_type_error'))} & "
                 rf"{pct_ci(get(qm, 'policy', 'format_compliant'))} & {pct(get(qm, 'policy', 'constraint_retention'))} & "
                 rf"{pct_ci(get(qm, 'classification', 'accuracy_strict'))} & "
                 rf"{num(get(qm, 'classification', 'macro_f1', 'value'), '{:.2f}')} \\")
    Q += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_quality.tex").write_text("\n".join(Q) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- reference-based metrics
    R = [r"\begin{tabular}{llrrrr}", r"\toprule",
         r"Model & Quant. & ROUGE-1 & ROUGE-2 & ROUGE-L & BERTScore \\", r"\midrule"]
    for model in MODELS:
        pm = get(q, model, "policy") or {}
        R.append(rf"{PRETTY[model]} & {num(get(pm, 'rouge1_f', 'value'), '{:.3f}')} & "
                 rf"{num(get(pm, 'rouge2_f', 'value'), '{:.3f}')} & {num(get(pm, 'rougeL_f', 'value'), '{:.3f}')} & "
                 rf"{num(get(pm, 'bertscore_f', 'value'), '{:.3f}')} \\")
    R += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_reference.tex").write_text("\n".join(R) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- temperature table
    temp = (primary or {}).get("temperature", {})
    X = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
         r" & & Schema \% & Format \% & Acc.\ \% & \multicolumn{2}{c}{Seed agreement \%} \\",
         r"\cmidrule(lr){6-7}",
         r"Model & $T$ & & & & Schema & Acc. \\", r"\midrule"]
    for model in ["llama3.2-3b-q4", "qwen2.5-7b-q4"]:
        name = PRETTY[model].split("&")[0].strip()
        qm = q.get(model, {})
        X.append(rf"{name} & 0.0 & {pct(get(qm, 'extraction', 'schema_valid'))} & "
                 rf"{pct(get(qm, 'policy', 'format_compliant'))} & {pct(get(qm, 'classification', 'accuracy_strict'))} & -- & -- \\")
        for T_ in ("0.2", "0.7"):
            tb = get(temp, model, T_) or {}
            sa = get(tb, "extraction", "schema_valid", "seed_agreement")
            ca = get(tb, "classification", "accuracy_strict", "seed_agreement")
            X.append(rf" & {T_} & {pct(get(tb, 'extraction', 'schema_valid'))} & {pct(get(tb, 'policy', 'format_compliant'))} & "
                     rf"{pct(get(tb, 'classification', 'accuracy_strict'))} & "
                     rf"{num(sa * 100 if sa is not None else None, '{:.0f}')} & {num(ca * 100 if ca is not None else None, '{:.0f}')} \\")
    X += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_temperature.tex").write_text("\n".join(X) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------- human eval table
    H = [r"\begin{tabular}{llrrrr}", r"\toprule",
         r"Model & Quant. & Quality (1--5) & HIR \% & Factual err.\ \% & Invented contact \% \\", r"\midrule"]
    raters = (human or {}).get("raters", [])
    for model in MODELS:
        hb = get(human, "by_model_task", f"{model}|drafting") or {}
        qual = [get(hb, r, "mean_quality") for r in raters if get(hb, r, "mean_quality") is not None]
        hirs = [get(hb, r, "hir")[0] for r in raters if get(hb, r, "hir")]
        fac = [get(hb, r, "factual_error_rate")[0] for r in raters if get(hb, r, "factual_error_rate")]
        avg = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
        hir_cell = TBD if not hirs else (f"{100 * avg(hirs):.0f}" if len(hirs) == 1 else
                                         f"{100 * avg(hirs):.0f} {{\\scriptsize({100 * min(hirs):.0f}--{100 * max(hirs):.0f})}}")
        H.append(rf"{PRETTY[model]} & {num(avg(qual), '{:.2f}')} & {hir_cell} & "
                 rf"{num(avg(fac) * 100 if fac else None, '{:.0f}')} & "
                 rf"{invented_pct(get(q, model, 'drafting'))} \\")
    H += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_human.tex").write_text("\n".join(H) + "\n", encoding="utf-8")
    print("Wrote paper/generated/{macros,tab_systems,tab_quality,tab_reference,tab_temperature,tab_human}.tex")


if __name__ == "__main__":
    main()
