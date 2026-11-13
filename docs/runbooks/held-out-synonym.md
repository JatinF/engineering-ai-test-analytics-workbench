# Held-out synonym

`SYN-FW-419` / `SYN-CODE-LAT` is the disagreement in `benchmarks/latest.json`.

The human label is regression. The agent returns `insufficient_evidence` because the chunks say "queue depth pause" and do not contain "raised the command queue cap".

The scripted review corrects the cause. Do not add the synonym to the rule just to raise the success rate. A change to the rule needs a new scenario and a new measurement.
