"""MCP-shaped tool boundary. A remote MCP server was not started."""

from typing import Any

from eng_workbench.errors import FlowError
from eng_workbench.identity import Actor, require_scope
from eng_workbench.store import Store

TOOL_NAMES = ("search_logs", "compare_history", "read_build", "example_failures", "flash_firmware")
PROTECTED = frozenset({"flash_firmware"})


class ToolGateway:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.calls = 0
        self.calls_by_name: dict[str, int] = {}
        self.accepted_protected = 0

    def handle(self, actor: Actor, message: dict[str, Any]) -> dict[str, Any]:
        method = str(message.get("method") or "")
        request_id = message.get("id", 1)
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": [{"name": name} for name in TOOL_NAMES]},
            }
        if method != "tools/call":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "method"},
            }
        params = message.get("params")
        if not isinstance(params, dict):
            raise FlowError("bad_tool_call", "params must be an object", 400)
        name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise FlowError("bad_tool_call", "arguments must be an object", 400)
        try:
            result = self.call(actor, name, arguments)
        except FlowError as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": exc.status, "message": exc.code},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def call(self, actor: Actor, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        override = arguments.get("tenant_id")
        if override is not None and str(override) != actor.tenant_id:
            self.store.record_audit(actor.user_id, name, "denied", "tenant_override")
            raise FlowError("tenant_boundary", "tenant override is denied", 403)
        if name in PROTECTED:
            self.store.record_audit(actor.user_id, name, "denied", "protected")
            raise FlowError("protected_tool", "protected tool is denied", 403)
        require_scope(actor, "data.read")
        if name not in TOOL_NAMES:
            self.store.record_audit(actor.user_id, name, "denied", "unknown_tool")
            raise FlowError("unknown_tool", "tool is not registered", 404)
        self.calls += 1
        self.calls_by_name[name] = self.calls_by_name.get(name, 0) + 1
        tenant = actor.tenant_id
        if name == "search_logs":
            rows = self.store.search_logs(
                tenant, str(arguments["build_id"]), str(arguments["code"])
            )
            return {"chunks": rows}
        if name == "compare_history":
            row = self.store.history_row(tenant, str(arguments["build_id"]), str(arguments["code"]))
            return {"row": row}
        if name == "read_build":
            note = self.store.change_note(tenant, str(arguments["build_id"]))
            return {"change_note": note}
        if name == "example_failures":
            ids = self.store.example_failures(
                tenant, str(arguments["code"]), str(arguments["before_build"])
            )
            return {"failure_ids": ids}
        raise FlowError("unknown_tool", "tool is not registered", 404)
