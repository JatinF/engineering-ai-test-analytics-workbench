import json
from pathlib import Path

from eng_workbench.store import build_lab_store
from eng_workbench.study import run_study


def test_benchmark_file_matches_the_scorer() -> None:
    payload = json.loads(Path("benchmarks/latest.json").read_text(encoding="utf-8"))
    report = run_study(build_lab_store())
    assert payload["successful_investigation_rate"] == report["successful_investigation_rate"]
    assert payload["citation_accuracy"] == report["citation_accuracy"]
    assert payload["human_correction_rate"] == report["human_correction_rate"]
    assert payload["recommendation"] == report["recommendation"]
    assert payload["disagreements"] == report["disagreements"]
    assert payload["dq_failures"] == 9
    assert payload["price"] == "none"
    assert payload["tokens"] == 0
    assert payload["device_calls"] == 0
    assert payload["agent_wall_seconds"]["p50"] > payload["manual_sql_wall_seconds"]["p50"]
    assert payload["adoption_fixture"]["investigate_events"] == 60
