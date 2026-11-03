"""Thin streaming client for a local Ollama server.

Measurement notes (these are reported in the paper's methodology):

* TTFT is measured client-side, from just before the HTTP request is sent to
  the arrival of the first streamed chunk that contains generated text.
* Inter-token latency (ITL) is the gap between consecutive streamed chunks that
  contain text. Ollama streams roughly one token per chunk; the chunk count is
  logged next to the server's ``eval_count`` so any merging is visible.
* Decode throughput uses the server's own counters:
  ``eval_count / eval_duration``. It excludes model load and prompt prefill.
* Memory is read two ways. ``model_size_bytes`` and ``model_size_vram_bytes``
  come from ``/api/ps`` (what Ollama reports the loaded model occupies).
  ``peak_ollama_rss_bytes`` is the peak resident set size summed over all
  Ollama processes, sampled every 50 ms while the request runs. Whole-system
  memory is deliberately NOT used, because it includes the browser, IDE, etc.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any

import requests

try:
    import psutil
except ImportError:  # memory sampling is optional
    psutil = None


DEFAULT_ENDPOINT = "http://localhost:11434"


def _ollama_processes():
    """Find Ollama's processes by name only.

    Reading every process's command line is very slow on Windows, so we match
    on the executable name and do it once per request, not on every sample.
    """
    if psutil is None:
        return []
    procs = []
    for p in psutil.process_iter(["name"]):
        try:
            name = (p.info.get("name") or "").lower()
            if "ollama" in name or "llama-server" in name or "llama_server" in name:
                procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs


class RssSampler:
    """Samples summed RSS of Ollama processes in a background thread.

    The process list is resolved once when sampling starts; each sample then
    reads memory for just those few processes, which is cheap on every OS.
    """

    def __init__(self, interval_s: float = 0.05):
        self.interval_s = interval_s
        self.peak = 0
        self._procs = []
        self._stop = threading.Event()
        self._thread = None

    def _sample_once(self):
        total = 0
        for p in self._procs:
            try:
                total += p.memory_info().rss
            except Exception:
                continue
        self.peak = max(self.peak, total)

    def _run(self):
        while not self._stop.is_set():
            self._sample_once()
            self._stop.wait(self.interval_s)

    def __enter__(self):
        if psutil is not None:
            self._procs = _ollama_processes()
            if self._procs:
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
            self._sample_once()


@dataclass
class GenerationResult:
    model: str
    text: str
    ttft_s: float | None
    wall_s: float
    itl_s: list[float] = field(default_factory=list)
    n_text_chunks: int = 0
    eval_count: int | None = None
    eval_duration_ns: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_duration_ns: int | None = None
    load_duration_ns: int | None = None
    total_duration_ns: int | None = None
    decode_tps: float | None = None
    model_size_bytes: int | None = None
    model_size_vram_bytes: int | None = None
    peak_ollama_rss_bytes: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OllamaClient:
    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, timeout_s: float = 600):
        self.endpoint = endpoint.rstrip("/")
        self.timeout_s = timeout_s

    # ---- server metadata -------------------------------------------------
    def version(self) -> str | None:
        try:
            return requests.get(f"{self.endpoint}/api/version", timeout=10).json().get("version")
        except Exception:
            return None

    def show(self, model: str) -> dict:
        try:
            r = requests.post(f"{self.endpoint}/api/show", json={"model": model}, timeout=30)
            r.raise_for_status()
            d = r.json()
            return {
                "details": d.get("details", {}),
                "model_info_keys": len(d.get("model_info", {}) or {}),
            }
        except Exception as e:
            return {"error": str(e)}

    def digest(self, model: str) -> str | None:
        try:
            tags = requests.get(f"{self.endpoint}/api/tags", timeout=10).json().get("models", [])
            for m in tags:
                if m.get("name") == model or m.get("model") == model:
                    return m.get("digest")
        except Exception:
            pass
        return None

    def loaded(self) -> list[dict]:
        try:
            return requests.get(f"{self.endpoint}/api/ps", timeout=10).json().get("models", [])
        except Exception:
            return []

    def unload_all(self):
        """Evict every loaded model so memory readings are not polluted."""
        for m in self.loaded():
            try:
                requests.post(f"{self.endpoint}/api/generate",
                              json={"model": m.get("name") or m.get("model"), "keep_alive": 0},
                              timeout=60)
            except Exception:
                pass
        time.sleep(1.0)

    # ---- generation ------------------------------------------------------
    def generate(self, model: str, prompt: str, *, temperature: float, seed: int,
                 num_predict: int = 512, num_ctx: int = 4096,
                 keep_alive: str = "30m") -> GenerationResult:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": keep_alive,
            "options": {
                "temperature": temperature,
                "seed": seed,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
        }
        pieces: list[str] = []
        chunk_times: list[float] = []
        final: dict = {}
        ttft = None
        err = None
        t0 = time.perf_counter()
        with RssSampler() as sampler:
            try:
                with requests.post(f"{self.endpoint}/api/generate", json=payload,
                                   stream=True, timeout=self.timeout_s) as r:
                    r.raise_for_status()
                    # chunk_size=None yields each HTTP chunk as it arrives. The default
                    # (512 bytes) bundles several tokens together and makes inter-token
                    # gaps look like zero.
                    for line in r.iter_lines(chunk_size=None):
                        if not line:
                            continue
                        now = time.perf_counter()
                        body = json.loads(line)
                        if body.get("error"):
                            err = body["error"]
                            break
                        tok = body.get("response", "")
                        if tok:
                            if ttft is None:
                                ttft = now - t0
                            chunk_times.append(now)
                            pieces.append(tok)
                        if body.get("done"):
                            final = body
                            break
            except Exception as e:  # network errors, timeouts
                err = f"{type(e).__name__}: {e}"
            wall = time.perf_counter() - t0
            loaded = self.loaded()

        itl = [b - a for a, b in zip(chunk_times, chunk_times[1:])]
        res = GenerationResult(
            model=model, text="".join(pieces), ttft_s=ttft, wall_s=wall, itl_s=itl,
            n_text_chunks=len(chunk_times), error=err,
            eval_count=final.get("eval_count"),
            eval_duration_ns=final.get("eval_duration"),
            prompt_eval_count=final.get("prompt_eval_count"),
            prompt_eval_duration_ns=final.get("prompt_eval_duration"),
            load_duration_ns=final.get("load_duration"),
            total_duration_ns=final.get("total_duration"),
            peak_ollama_rss_bytes=(sampler.peak or None),
        )
        if res.eval_count and res.eval_duration_ns:
            res.decode_tps = res.eval_count / (res.eval_duration_ns / 1e9)
        for m in loaded:
            if (m.get("name") or m.get("model")) == model:
                res.model_size_bytes = m.get("size")
                res.model_size_vram_bytes = m.get("size_vram")
        return res
