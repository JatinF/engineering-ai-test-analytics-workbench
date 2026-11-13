import importlib.util
from pathlib import Path

import pytest

from eng_workbench.agent import Investigator
from eng_workbench.decision import choose
from eng_workbench.errors import FlowError
from eng_workbench.gates import ensure_local
from eng_workbench.gold import CASES, human_expectation
from eng_workbench.identity import IDA, OTHER_TENANT, TENANT
from eng_workbench.pipeline import TASKS
from eng_workbench.store import build_lab_store
from eng_workbench.study import run_study
from eng_workbench.tools import ToolGateway


def test_lab_counts_and_temperature(store) -> None:
    assert store.failure_count(TENANT, "SYN-FW-417", "SYN-CODE-THERM") == 12
    assert store.failure_count(TENANT, "SYN-FW-418", "SYN-CODE-LINK") == 11
    assert store.failure_count(TENANT, "SYN-FW-419", "SYN-CODE-LAT") == 10
    assert len(CASES) == 16
    assert store.dq_count() == 9
    reasons = {row["reason"]: row["n"] for row in store.dq_by_reason()}
    assert reasons["missing_build"] == 3
    assert reasons["unknown_code"] == 2
    assert reasons["future_timestamp"] == 2
    assert reasons["negative_telemetry"] == 2
    mean = store.mean_temperature(TENANT, "SYN-FW-417")
    assert mean is not None
    assert round(mean, 3) == 54.025
    clean = build_lab_store(include_dirty=False)
    assert clean.dq_count() == 0


def test_semantic_pass_rate_and_tenant_isolation(store) -> None:
    rates = {row["build_id"]: row["pass_rate"] for row in store.pass_rates(TENANT)}
    assert rates["SYN-FW-417"] == pytest.approx(21 / 40)
    assert store.failure_count(TENANT, "SYN-FW-M01", "SYN-CODE-MARSH") == 0
    assert store.failure_count(OTHER_TENANT, "SYN-FW-M01", "SYN-CODE-MARSH") == 2
    leaked = store.search_logs(TENANT, "SYN-FW-M01", "SYN-CODE-MARSH")
    assert leaked == []
    marsh = store.search_logs(OTHER_TENANT, "SYN-FW-M01", "SYN-CODE-MARSH")
    assert marsh[0]["body"] == "marshline only marker"


def test_agent_matches_human_labels_except_holdout(store) -> None:
    report = run_study(store)
    assert report["cases"] == 16
    assert report["unauthorized_protected_tool_actions"] == 0
    assert report["flash_error"] == "protected_tool"
    assert report["device_calls"] == 0
    assert report["disagreements"] == ["SYN-FW-419 SYN-CODE-LAT"]
    assert report["recommendation"] == choose(
        report["successful_investigation_rate"],
        report["citation_accuracy"],
        report["unauthorized_protected_tool_actions"],
    )
    held = human_expectation(store, "SYN-FW-419", "SYN-CODE-LAT")
    assert held["classification"] == "regression"
    assert held["rule_classification"] == "insufficient_evidence"


def test_decision_floors() -> None:
    assert choose(0.95, 0.95, 0) == "keep_agent"
    assert choose(0.89, 0.99, 0) == "sql_only"
    assert choose(0.99, 0.89, 0) == "sql_only"
    assert choose(0.99, 0.99, 1) == "sql_only"


def test_retry_does_not_repeat_search(store) -> None:
    tools = ToolGateway(store)
    agent = Investigator(store, tools)
    agent.fail_remaining["compare_history"] = 1
    with pytest.raises(RuntimeError, match="injected"):
        agent.investigate(IDA, "SYN-FW-417", "SYN-CODE-THERM", "SYN-INV-RETRY")
    assert tools.calls_by_name.get("search_logs") == 1
    agent.investigate(IDA, "SYN-FW-417", "SYN-CODE-THERM", "SYN-INV-RETRY")
    assert tools.calls_by_name.get("search_logs") == 1


def test_same_actor_cannot_review(store, nell) -> None:
    from eng_workbench.review import submit_review

    agent = Investigator(store, ToolGateway(store))
    draft = agent.investigate(nell, "SYN-FW-416", "SYN-CODE-POWER")
    with pytest.raises(FlowError) as caught:
        submit_review(store, nell, draft["investigation_id"], "approve", "", "")
    assert caught.value.code == "same_actor"


def test_citation_checker_drops_foreign_ids(store) -> None:
    from eng_workbench.agent import draft_from_evidence

    drafted = draft_from_evidence(
        "raised the thermal throttle floor",
        [{"chunk_id": "SYN-LOG-KEEP", "body": "raised the thermal throttle floor"}],
        0.3,
        0.02,
        [],
    )
    assert drafted["citations"] == ["SYN-LOG-KEEP"]
    agent = Investigator(store, ToolGateway(store))
    state = {
        "investigation_id": "SYN-INV-CITE",
        "chunk_ids": ["SYN-LOG-KEEP"],
        "example_ids": [],
        "classification": "regression",
        "cause": "raised the thermal throttle floor",
        "citations": ["SYN-LOG-KEEP", "SYN-LOG-M01-MARS-00"],
    }
    checked = agent._check(state)  # noqa: SLF001
    assert checked["citations"] == ["SYN-LOG-KEEP"]


def test_remote_url_is_blocked_without_echo() -> None:
    secret = "https://warehouse.example.invalid/lab"
    with pytest.raises(FlowError) as caught:
        ensure_local(secret, allow_remote=False)
    assert caught.value.code == "remote_blocked"
    assert "example.invalid" not in caught.value.message
    assert secret not in str(caught.value)


def test_agent_source_does_not_encode_the_holdout() -> None:
    source = Path("src/eng_workbench/agent.py").read_text(encoding="utf-8")
    assert "gold" not in source
    assert "SYN-FW-419" not in source
    assert "queue depth" not in source


def test_airflow_task_order_matches_the_pipeline() -> None:
    path = Path("orchestration/dags/lab_pipeline.py")
    spec = importlib.util.spec_from_file_location("lab_pipeline", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.TASKS == TASKS
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("airflow.models")


def test_terraform_sketch_is_unapplied() -> None:
    text = Path("deploy/terraform/main.tf").read_text(encoding="utf-8")
    assert "applied = false" in text
    assert "aws_eks_cluster" in text
