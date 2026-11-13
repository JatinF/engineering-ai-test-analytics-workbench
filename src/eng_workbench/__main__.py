"""Serve the API, print one draft, or print the study summary."""

import argparse
import json

import uvicorn

from eng_workbench.identity import IDA
from eng_workbench.store import build_lab_store
from eng_workbench.study import run_study


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eng-workbench")
    parser.add_argument("command", choices=("serve", "demo", "eval"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command == "serve":
        uvicorn.run("eng_workbench.api:app", host=args.host, port=args.port)
        return
    store = build_lab_store()
    if args.command == "eval":
        report = run_study(store)
        report.pop("rows", None)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    from eng_workbench.agent import Investigator
    from eng_workbench.tools import ToolGateway

    agent = Investigator(store, ToolGateway(store))
    draft = agent.investigate(IDA, "SYN-FW-417", "SYN-CODE-THERM")
    print(
        json.dumps(
            {
                "investigation_id": draft["investigation_id"],
                "classification": draft["classification"],
                "citations": draft["citations"],
                "notice": draft["notice"],
                "status": draft["status"],
                "device_calls": store.device_calls,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
