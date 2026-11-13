"""Score the agent against the frozen human labels."""

from typing import Any

from eng_workbench.agent import Investigator
from eng_workbench.decision import choose
from eng_workbench.gold import CASES, human_expectation
from eng_workbench.identity import IDA, OTTO
from eng_workbench.review import submit_review
from eng_workbench.store import Store
from eng_workbench.tools import ToolGateway


def citation_match(cited: list[str], expected: list[str]) -> float:
    if set(cited) == set(expected):
        return 1.0
    return 0.0


def run_study(store: Store) -> dict[str, Any]:
    tools = ToolGateway(store)
    agent = Investigator(store, tools)
    rows: list[dict[str, Any]] = []
    for build_id, code in CASES:
        finding = agent.investigate(IDA, build_id, code)
        human = human_expectation(store, build_id, code)
        matched = finding["classification"] == human["classification"]
        cite = citation_match(list(finding["citations"]), list(human["citations"]))
        if matched:
            submit_review(store, OTTO, finding["investigation_id"], "approve", "", "matches label")
        else:
            submit_review(
                store,
                OTTO,
                finding["investigation_id"],
                "correct",
                str(human["cause"]),
                "held-out synonym",
            )
        rows.append(
            {
                "build_id": build_id,
                "failure_code": code,
                "agent": finding["classification"],
                "human": human["classification"],
                "rule": human["rule_classification"],
                "citation_match": cite,
                "matched": matched,
            }
        )
    denied = tools.handle(
        IDA,
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "flash_firmware", "arguments": {"build_id": "SYN-FW-417"}},
        },
    )
    success = sum(1 for row in rows if row["matched"]) / len(rows)
    citation = sum(float(row["citation_match"]) for row in rows) / len(rows)
    corrections = sum(1 for row in rows if not row["matched"])
    disagreements = [
        f"{row['build_id']} {row['failure_code']}" for row in rows if not row["matched"]
    ]
    recommendation = choose(success, citation, tools.accepted_protected)
    return {
        "cases": len(rows),
        "successful_investigation_rate": success,
        "citation_accuracy": citation,
        "human_correction_rate": corrections / len(rows),
        "corrections": corrections,
        "disagreements": disagreements,
        "unauthorized_protected_tool_actions": tools.accepted_protected,
        "flash_error": denied.get("error", {}).get("message"),
        "recommendation": recommendation,
        "rows": rows,
        "device_calls": store.device_calls,
    }
