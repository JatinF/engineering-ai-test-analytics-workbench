"""Human labels for the fixed scenario.

The phrase-and-rate rule matches the agent on every case except the held-out
synonym. That label was written with the scenario, not taken from a model run.
The agent module does not import this file.
"""

from typing import Any

from eng_workbench.identity import TENANT
from eng_workbench.store import Store

CASES = (
    ("SYN-FW-417", "SYN-CODE-THERM"),
    ("SYN-FW-418", "SYN-CODE-LINK"),
    ("SYN-FW-419", "SYN-CODE-LAT"),
    ("SYN-FW-416", "SYN-CODE-POWER"),
    ("SYN-FW-414", "SYN-CODE-POWER"),
    ("SYN-FW-413", "SYN-CODE-LAT"),
    ("SYN-FW-412", "SYN-CODE-LINK"),
    ("SYN-FW-411", "SYN-CODE-THERM"),
    ("SYN-FW-417", "SYN-CODE-LINK"),
    ("SYN-FW-418", "SYN-CODE-THERM"),
    ("SYN-FW-419", "SYN-CODE-POWER"),
    ("SYN-FW-416", "SYN-CODE-LINK"),
    ("SYN-FW-415", "SYN-CODE-POWER"),
    ("SYN-FW-419", "SYN-CODE-THERM"),
    ("SYN-FW-413", "SYN-CODE-LINK"),
    ("SYN-FW-412", "SYN-CODE-POWER"),
)

# Logs say "queue depth pause" and do not repeat the change note.
HOLD_OUT = {("SYN-FW-419", "SYN-CODE-LAT"): "regression"}


def phrase_expectation(store: Store, build_id: str, code: str) -> dict[str, Any]:
    from eng_workbench.semantic import RATE_JUMP

    note = store.change_note(TENANT, build_id) or ""
    chunks = store.search_logs(TENANT, build_id, code)
    row = store.history_row(TENANT, build_id, code)
    examples = store.example_failures(TENANT, code, build_id)
    support = [item for item in chunks if note != "" and note in str(item["body"])]
    delta = None
    if row is not None and row["rate"] is not None and row["prior_mean"] is not None:
        delta = float(row["rate"]) - float(row["prior_mean"])
    if delta is not None and delta >= RATE_JUMP and support:
        return {
            "classification": "regression",
            "cause": note,
            "citations": [str(item["chunk_id"]) for item in support],
        }
    if delta is not None and delta >= RATE_JUMP:
        return {"classification": "insufficient_evidence", "cause": "", "citations": []}
    if examples:
        return {
            "classification": "recurring",
            "cause": "within historical band",
            "citations": list(examples),
        }
    return {"classification": "insufficient_evidence", "cause": "", "citations": []}


def human_expectation(store: Store, build_id: str, code: str) -> dict[str, Any]:
    rule = phrase_expectation(store, build_id, code)
    if (build_id, code) not in HOLD_OUT:
        return {
            "classification": rule["classification"],
            "cause": rule["cause"],
            "citations": list(rule["citations"]),
            "rule_classification": rule["classification"],
        }
    chunks = store.search_logs(TENANT, build_id, code)
    return {
        "classification": "regression",
        "cause": store.change_note(TENANT, build_id) or "",
        "citations": [str(row["chunk_id"]) for row in chunks],
        "rule_classification": rule["classification"],
    }
