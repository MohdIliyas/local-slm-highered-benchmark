# On-Device Small Language Models for University Administration

Benchmark harness, data, and manuscript for evaluating open-weight **small language models (SLMs)** running locally on commodity hardware, for four university administrative tasks:

| Task | Items | What counts as a pass |
|---|---|---|
| Syllabus extraction | 24 syllabi | Schema-valid JSON with correct fields and numeric weights |
| Policy summarization | 16 policies | Exactly three bullets, no preamble, every deadline and threshold kept |
| Ticket classification | 64 tickets (8 classes) | Output is exactly the correct category name |
| Reply drafting | 16 inquiries | Rated blind by two people; no invented contact details |

The models are Llama 3.2 3B and Qwen 2.5 7B, each at `Q4_K_M` and `Q8_0`, run through Ollama. The machines are an Intel Core i7 workstation (CPU only) and an Apple M2 Max Mac.

All task data are **synthetic** and written for this study (`data/tasks/`). No real student information is used or stored.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.2:3b-instruct-q4_K_M
ollama pull llama3.2:3b-instruct-q8_0
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull qwen2.5:7b-instruct-q8_0

python scripts/run_experiments.py --machine intel_i7 --preset smoke        # ~5 min sanity check
python scripts/run_experiments.py --machine intel_i7 --preset main         # all models x all tasks
python scripts/run_experiments.py --machine intel_i7 --preset temperature  # sampling ablation
python scripts/score.py --machine intel_i7
python scripts/make_paper_tables.py
```

Runs are resumable. If one stops partway, run the same command again, and calls that already finished are skipped.

Use `--machine apple_m2max` on the Mac. Step-by-step instructions are in [`docs/mac_benchmarking_instructions.md`](docs/mac_benchmarking_instructions.md).

## Human evaluation

```bash
python scripts/make_blind_queue.py --machine intel_i7 --raters mohammed karthik
# each rater reads results/human_eval/queue.md and fills in ratings_<name>.csv
python scripts/score_human.py
python scripts/make_paper_tables.py
```

The rubric is in [`docs/human_eval_rubric.md`](docs/human_eval_rubric.md). Raters must not open `results/human_eval/key/`.

## How numbers get into the paper

No number in `paper/main.tex` is typed by hand. The data flows like this:

```
raw.jsonl  ->  score.py  ->  summary.json  ->  make_paper_tables.py  ->  paper/generated/*.tex
```

Anything not yet measured prints as a red **[TBD]**. Setting `\draftfalse` in `main.tex` makes the build fail while any [TBD] or author note remains, so an unmeasured value cannot reach a submitted PDF.

## Repository layout

```
bench/              harness library: Ollama client, scoring, statistics, system info
scripts/            run_experiments, score, make_blind_queue, score_human, make_paper_tables
configs/            model tags, presets, cost-model assumptions
data/tasks/         syllabi, policies, tickets (synthetic, with gold labels)
prompts/            prompt templates for the four tasks
results/<machine>/  raw outputs, manifests (hardware + versions), summary.json, per_item.csv
results/pilot/      earlier pilot outputs, kept for reference (not used in the paper)
paper/              main.tex, references.bib, generated/ tables
docs/               Mac instructions, human-eval rubric, archived progress reports
tests/              mock Ollama server and an end-to-end pipeline test
```

## Testing without models

```bash
python tests/test_pipeline.py
```

This test runs the whole pipeline against a fake Ollama server: the runner, resume, scoring, blind queue, human scoring, and table generation. It finishes in about a minute.

## Measurement notes

- **Decode throughput** is computed from Ollama's own token counter and decode time, so it excludes model loading and prompt processing.
- **TTFT and inter-token latency** are measured client-side on the streamed response, one HTTP chunk at a time.
- **Memory** is the loaded model's size as reported by Ollama, plus peak resident memory of Ollama's processes. It is never whole-system memory.
- **Latency** comes from the same distinct prompts as the quality results. Repeating one prompt would let Ollama's prompt cache make it look artificially fast.
