# Archived runs

## `intel_i7_main_run1/`

This was the first full `main` run on the Windows laptop (November 3, 2026, harness commit `135e341`). It was superseded for two reasons:

- **Inflated TTFT.** The client connected to `localhost`. On Windows, that tries IPv6 first and then falls back to IPv4, which added about 2.05 s to every request's client-side time to first token and wall time. Server-side counters were unaffected: decode throughput, prefill throughput, and inter-token latency are valid. Fixed by connecting to `127.0.0.1`.
- **GPU not recorded.** Ollama offloaded models to the laptop's discrete GPU. The manifest from this run does not record which GPU it was.

The run is kept because its greedy (`T=0`) outputs serve as a reproducibility check against the rerun. Do not cite its TTFT values.
