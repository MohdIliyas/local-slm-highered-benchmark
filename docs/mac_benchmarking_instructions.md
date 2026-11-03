# Running the benchmark on the Apple M4 Mac

**For:** Karthik
**Time needed:** about 10 minutes of setup. The full run is unattended and can take a few hours. Leave the Mac plugged in, with sleep turned off.

Please follow these steps in order. Every command is run in Terminal from inside the repository folder.

## 1. Get the code

If you already cloned the repo earlier, run `git pull` instead of cloning.

```bash
git clone https://github.com/MohdIliyas/local-slm-highered-benchmark.git
cd local-slm-highered-benchmark
```

## 2. Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Check that everything works without models

```bash
python tests/test_pipeline.py
```

The last lines should say `ALL CHECKS PASSED`. If they don't, stop and send the output to Mohammed.

## 4. Install the models

Make sure the Ollama app is running (its icon shows in the menu bar), then:

```bash
ollama pull llama3.2:3b-instruct-q4_K_M
ollama pull llama3.2:3b-instruct-q8_0
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull qwen2.5:7b-instruct-q8_0
```

These are exact tags. Please don't substitute `llama3.2:3b` or `qwen2.5:7b`, because those are different builds and the results wouldn't be comparable.

## 5. Prepare the machine

These steps make the timing measurements fair:

- Quit other apps, especially browsers, Docker, and anything else running a model.
- Plug in the charger. On battery, macOS may slow the chip down.
- Turn off sleep. On recent macOS, go to System Settings → Battery → Options → "Prevent automatic sleeping on power adapter when the display is off". As an alternative, run the experiments with `caffeinate -i` in front of the command.

## 6. Run

```bash
python scripts/run_experiments.py --machine apple_m4 --preset smoke
```

The smoke run takes about 5 minutes. If it finishes without errors, start the real runs:

```bash
caffeinate -i python scripts/run_experiments.py --machine apple_m4 --preset main
caffeinate -i python scripts/run_experiments.py --machine apple_m4 --preset temperature
python scripts/score.py --machine apple_m4
```

If anything interrupts a run, run the same command again. It picks up where it stopped.

## 7. Send the results back

```bash
git checkout -b apple-m4-results
git add results/apple_m4
git commit -m "Apple M4 benchmark results"
git push -u origin apple-m4-results
```

Then open a pull request on GitHub. Please **don't** push directly to `main`, and never use `--force`. A branch keeps your results safe even if someone else pushes at the same time.

## 8. Human ratings (separate step, after Mohammed shares the queue)

1. Pull the latest changes.
2. Open `results/human_eval/queue.md` and rate each item in `results/human_eval/ratings_karthik.csv`, following `docs/human_eval_rubric.md`.
3. Don't open the `results/human_eval/key/` folder, and don't compare individual scores with Mohammed until you have both finished.
4. Commit only your own CSV, on a branch, and open a pull request.
