"""LangGraph investigation. StateGraph replaces state, so every node carries it forward."""

import time
from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from eng_workbench.errors import FlowError
from eng_workbench.identity import NOTICE, Actor
from eng_workbench.semantic import RATE_JUMP
from eng_workbench.store import Store
from eng_workbench.tools import ToolGateway

STEP_NAMES = (
    "load_case",
    "retrieve_logs",
    "compare_history",
    "draft_finding",
    "check_citations",
)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    classification: str
    cause: str
    citations: list[str]
    notice: str = Field(default=NOTICE)


class FlowState(TypedDict, total=False):
    investigation_id: str
    tenant_id: str
    actor_id: str
    build_id: str
    failure_code: str
    change_note: str
    chunks: list[dict[str, Any]]
    chunk_ids: list[str]
    rate: float
    prior_mean: float | None
    example_ids: list[str]
    classification: str
    cause: str
    citations: list[str]


class Investigator:
    def __init__(self, store: Store, tools: ToolGateway) -> None:
        self.store = store
        self.tools = tools
        self.fail_remaining: dict[str, int] = {}
        builder: StateGraph[FlowState] = StateGraph(FlowState)
        builder.add_node("load_case", self._load)
        builder.add_node("retrieve_logs", self._retrieve)
        builder.add_node("compare_history", self._compare)
        builder.add_node("draft_finding", self._draft)
        builder.add_node("check_citations", self._check)
        builder.add_edge(START, "load_case")
        builder.add_edge("load_case", "retrieve_logs")
        builder.add_edge("retrieve_logs", "compare_history")
        builder.add_edge("compare_history", "draft_finding")
        builder.add_edge("draft_finding", "check_citations")
        builder.add_edge("check_citations", END)
        self.graph = builder.compile()

    def _carry(self, state: FlowState, payload: dict[str, Any]) -> FlowState:
        carried: dict[str, Any] = dict(state)
        carried.update(payload)
        return carried  # type: ignore[return-value]

    def _guard(self, name: str) -> None:
        left = self.fail_remaining.get(name, 0)
        if left > 0:
            self.fail_remaining[name] = left - 1
            raise RuntimeError("injected")

    def _load(self, state: FlowState) -> FlowState:
        name = "load_case"
        existing = self.store.get_step(state["investigation_id"], name)
        if existing is not None:
            return self._carry(state, existing)
        self._guard(name)
        actor = _actor(state)
        loaded = self.tools.call(actor, "read_build", {"build_id": state["build_id"]})
        if loaded["change_note"] is None:
            raise FlowError("unknown_build", "build is not in this tenant", 404)
        payload: dict[str, Any] = {
            "build_id": state["build_id"],
            "failure_code": state["failure_code"],
            "change_note": loaded["change_note"],
        }
        self.store.save_step(state["investigation_id"], name, payload)
        return self._carry(state, payload)

    def _retrieve(self, state: FlowState) -> FlowState:
        name = "retrieve_logs"
        existing = self.store.get_step(state["investigation_id"], name)
        if existing is not None:
            return self._carry(state, existing)
        self._guard(name)
        actor = _actor(state)
        loaded = self.tools.call(
            actor,
            "search_logs",
            {"build_id": state["build_id"], "code": state["failure_code"]},
        )
        chunks = loaded["chunks"]
        payload = {
            "chunks": chunks,
            "chunk_ids": [str(row["chunk_id"]) for row in chunks],
        }
        self.store.save_step(state["investigation_id"], name, payload)
        return self._carry(state, payload)

    def _compare(self, state: FlowState) -> FlowState:
        name = "compare_history"
        existing = self.store.get_step(state["investigation_id"], name)
        if existing is not None:
            return self._carry(state, existing)
        self._guard(name)
        actor = _actor(state)
        history = self.tools.call(
            actor,
            "compare_history",
            {"build_id": state["build_id"], "code": state["failure_code"]},
        )
        examples = self.tools.call(
            actor,
            "example_failures",
            {"code": state["failure_code"], "before_build": state["build_id"]},
        )
        row = history["row"]
        payload: dict[str, Any] = {
            "rate": None if row is None else row["rate"],
            "prior_mean": None if row is None else row["prior_mean"],
            "example_ids": examples["failure_ids"],
        }
        self.store.save_step(state["investigation_id"], name, payload)
        return self._carry(state, payload)

    def _draft(self, state: FlowState) -> FlowState:
        name = "draft_finding"
        existing = self.store.get_step(state["investigation_id"], name)
        if existing is not None:
            return self._carry(state, existing)
        self._guard(name)
        payload = draft_from_evidence(
            change_note=str(state.get("change_note") or ""),
            chunks=list(state.get("chunks") or []),
            rate=state.get("rate"),
            prior_mean=state.get("prior_mean"),
            example_ids=list(state.get("example_ids") or []),
        )
        self.store.save_step(state["investigation_id"], name, payload)
        return self._carry(state, payload)

    def _check(self, state: FlowState) -> FlowState:
        name = "check_citations"
        existing = self.store.get_step(state["investigation_id"], name)
        if existing is not None:
            return self._carry(state, existing)
        self._guard(name)
        allowed = set(state.get("chunk_ids") or [])
        allowed.update(state.get("example_ids") or [])
        cited = [item for item in state.get("citations") or [] if item in allowed]
        classification = str(state.get("classification") or "insufficient_evidence")
        cause = str(state.get("cause") or "")
        if classification == "regression" and not cited:
            classification = "insufficient_evidence"
            cause = ""
        if classification == "recurring" and not cited:
            classification = "insufficient_evidence"
            cause = ""
        payload = {"classification": classification, "cause": cause, "citations": cited}
        self.store.save_step(state["investigation_id"], name, payload)
        return self._carry(state, payload)

    def investigate(
        self,
        actor: Actor,
        build_id: str,
        failure_code: str,
        investigation_id: str | None = None,
    ) -> dict[str, Any]:
        from eng_workbench.identity import require_scope

        require_scope(actor, "investigation.run")
        if investigation_id is None:
            investigation_id = f"SYN-INV-{self.store.next_id():04d}"
        initial: FlowState = {
            "investigation_id": investigation_id,
            "tenant_id": actor.tenant_id,
            "actor_id": actor.user_id,
            "build_id": build_id,
            "failure_code": failure_code,
        }
        started = time.perf_counter()
        self.graph.invoke(cast(Any, initial))
        wall = time.perf_counter() - started
        merged: dict[str, Any] = {}
        summaries: list[dict[str, str]] = []
        for name in STEP_NAMES:
            step = self.store.get_step(investigation_id, name)
            if step is None:
                raise RuntimeError(f"step {name} missing after the graph returned")
            merged.update(step)
            summaries.append({"name": name, "detail": _summary(name, step)})
        finding = Finding(
            classification=str(merged["classification"]),
            cause=str(merged["cause"]),
            citations=list(merged["citations"]),
            notice=NOTICE,
        )
        row = {
            "investigation_id": investigation_id,
            "tenant_id": actor.tenant_id,
            "requester_id": actor.user_id,
            "build_id": build_id,
            "failure_code": failure_code,
            "classification": finding.classification,
            "cause": finding.cause,
            "citations": finding.citations,
            "notice": finding.notice,
            "status": "DRAFT",
            "wall_seconds": wall,
            "steps": summaries,
        }
        self.store.save_investigation(row)
        self.store.record_usage(actor.user_id, "investigate", f"{build_id}:{failure_code}")
        return row


def draft_from_evidence(
    change_note: str,
    chunks: list[dict[str, Any]],
    rate: object,
    prior_mean: object,
    example_ids: list[str],
) -> dict[str, Any]:
    support = [row for row in chunks if change_note != "" and change_note in str(row["body"])]
    delta = None
    if rate is not None and prior_mean is not None:
        delta = float(rate) - float(prior_mean)  # type: ignore[arg-type]
    if delta is not None and delta >= RATE_JUMP and support:
        return {
            "classification": "regression",
            "cause": change_note,
            "citations": [str(row["chunk_id"]) for row in support],
        }
    if delta is not None and delta >= RATE_JUMP:
        return {"classification": "insufficient_evidence", "cause": "", "citations": []}
    if example_ids:
        return {
            "classification": "recurring",
            "cause": "within historical band",
            "citations": list(example_ids),
        }
    return {"classification": "insufficient_evidence", "cause": "", "citations": []}


def _actor(state: FlowState) -> Actor:
    from eng_workbench.identity import actor_by_id

    found = actor_by_id(str(state["actor_id"]))
    if found is None:
        raise FlowError("unknown_actor", "actor is not registered", 401)
    return found


def _summary(name: str, step: dict[str, Any]) -> str:
    if name == "retrieve_logs":
        return f"chunks {len(step.get('chunk_ids') or [])}"
    if name == "draft_finding":
        return str(step.get("classification") or "")
    if name == "check_citations":
        return f"{step.get('classification')} citations {len(step.get('citations') or [])}"
    if name == "compare_history":
        return f"rate {step.get('rate')}"
    return "loaded"
