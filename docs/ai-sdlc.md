# How this repository was written

This repository was written in a Grok Build session. It was not written in Claude Code.

The phrase-and-rate rule and the 0.90 floors were in the source before `scripts/benchmark.py` wrote `benchmarks/latest.json`. The held-out synonym on `SYN-FW-419` was part of the scenario. The lexicon was not expanded after the score.

The agent wall-clock samples were higher than the four-query SQL samples. The recommendation stays `keep_agent` because the floors are about citation and agreement, not about beating that SQL path on time.
