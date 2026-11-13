"""Measure the lab on this workstation and write benchmarks/latest.json."""

import json
import math
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

from eng_workbench.agent import Investigator
from eng_workbench.decision import CITATION_FLOOR, SUCCESS_FLOOR
from eng_workbench.gold import CASES
from eng_workbench.identity import DATASET_ID, IDA
from eng_workbench.store import build_lab_store
from eng_workbench.study import run_study
from eng_workbench.tools import ToolGateway


def nearest_rank(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = math.ceil(fraction * len(ordered)) - 1
    return ordered[max(0, index)]


def hardware() -> dict[str, Any]:
    script = (
        "$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 "
        "Name, NumberOfCores, NumberOfLogicalProcessors; "
        "$os = Get-CimInstance Win32_OperatingSystem | Select-Object "
        "FreePhysicalMemory, TotalVisibleMemorySize; "
        "[pscustomobject]@{name=$cpu.Name; cores=$cpu.NumberOfCores; "
        "logical=$cpu.NumberOfLogicalProcessors; free_kb=[int64]$os.FreePhysicalMemory; "
        "total_kb=[int64]$os.TotalVisibleMemorySize} | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    return {
        "processor": payload["name"],
        "cores": payload["cores"],
        "logical_processors": payload["logical"],
        "free_physical_memory_kb": payload["free_kb"],
        "total_visible_memory_kb": payload["total_kb"],
        "python": platform.python_version(),
        "system": platform.system(),
    }


def manual_lookup(store: Any) -> None:
    store.change_note(IDA.tenant_id, "SYN-FW-417")
    store.history_row(IDA.tenant_id, "SYN-FW-417", "SYN-CODE-THERM")
    store.search_logs(IDA.tenant_id, "SYN-FW-417", "SYN-CODE-THERM")
    store.example_failures(IDA.tenant_id, "SYN-CODE-THERM", "SYN-FW-417")


def main() -> None:
    store = build_lab_store()
    report = run_study(store)
    for build_id, code in CASES[:4]:
        Investigator(store, ToolGateway(store)).investigate(IDA, build_id, code)
    agent = Investigator(store, ToolGateway(store))
    agent_samples: list[float] = []
    for _ in range(40):
        started = time.perf_counter()
        agent.investigate(IDA, "SYN-FW-417", "SYN-CODE-THERM")
        agent_samples.append(time.perf_counter() - started)
    manual_samples: list[float] = []
    for _ in range(40):
        started = time.perf_counter()
        manual_lookup(store)
        manual_samples.append(time.perf_counter() - started)
    usage = store.usage_summary()
    payload = {
        "dataset": DATASET_ID,
        "hardware": hardware(),
        "cases": report["cases"],
        "successful_investigation_rate": report["successful_investigation_rate"],
        "citation_accuracy": report["citation_accuracy"],
        "human_correction_rate": report["human_correction_rate"],
        "disagreements": report["disagreements"],
        "recommendation": report["recommendation"],
        "success_floor": SUCCESS_FLOOR,
        "citation_floor": CITATION_FLOOR,
        "unauthorized_protected_tool_actions": report["unauthorized_protected_tool_actions"],
        "dq_failures": store.dq_count(),
        "device_calls": store.device_calls,
        "tokens": 0,
        "price": "none",
        "hosted_model": "not-run",
        "agent_wall_seconds": {
            "repeats": 40,
            "case": "SYN-FW-417 SYN-CODE-THERM",
            "min": min(agent_samples),
            "p50": nearest_rank(agent_samples, 0.50),
            "p95": nearest_rank(agent_samples, 0.95),
            "max": max(agent_samples),
        },
        "manual_sql_wall_seconds": {
            "repeats": 40,
            "min": min(manual_samples),
            "p50": nearest_rank(manual_samples, 0.50),
            "p95": nearest_rank(manual_samples, 0.95),
            "max": max(manual_samples),
        },
        "adoption_fixture": usage,
        "note": (
            "Adoption counts are the controlled fixture in this process, "
            "not engineer usage in a company. Price was not applied."
        ),
    }
    target = Path(__file__).resolve().parents[1] / "benchmarks" / "latest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
