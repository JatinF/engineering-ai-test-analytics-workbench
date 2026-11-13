"""Prometheus text for the in-process counters. Grafana was not run."""

from typing import Any


def render(snapshot: dict[str, Any]) -> str:
    lines = [
        "# TYPE eng_investigations_total gauge",
        f"eng_investigations_total {snapshot['investigations']}",
        "# TYPE eng_dq_failures_total gauge",
        f"eng_dq_failures_total {snapshot['dq_failures']}",
        "# TYPE eng_denials_total gauge",
        f"eng_denials_total {snapshot['denials']}",
        "# TYPE eng_corrections_total gauge",
        f"eng_corrections_total {snapshot['corrections']}",
        "# TYPE eng_device_calls_total gauge",
        "eng_device_calls_total 0",
    ]
    return "\n".join(lines) + "\n"


def snapshot(store: Any) -> dict[str, int]:
    stats = store.correction_stats()
    investigations = store.one("SELECT COUNT(*) AS n FROM investigations")
    return {
        "investigations": int(investigations["n"]) if investigations else 0,
        "dq_failures": store.dq_count(),
        "denials": store.denial_count(),
        "corrections": stats["corrections"],
    }
