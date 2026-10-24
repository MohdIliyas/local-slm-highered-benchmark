# Karthik's Step-by-Step Action Checklist

## Part 1: Apple Silicon M4 Benchmarking
1. Clone repo, setup venv, pip install requirements.
2. Ensure Ollama is running and models are pulled.
3. Run python scripts\run_benchmark.py --output results\apple_m4\ and python scripts\run_batch_eval.py --device apple_m4.
4. Push results to GitHub.

## Part 2: Double-Blind Review
1. Pull latest changes.
2. Score items in esults/human_eval/blind_queue.json under ater_2_score.
3. Compute Cohen's Kappa and push updates.

## Part 3: PDF Compilation
1. Run pdflatex build sequence inside paper/.
