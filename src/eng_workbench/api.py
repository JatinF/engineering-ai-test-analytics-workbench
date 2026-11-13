"""HTTP API for the simulated workbench."""

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from eng_workbench.agent import Investigator
from eng_workbench.errors import FlowError
from eng_workbench.gates import adapter_report
from eng_workbench.identity import NOTICE, ORG, Actor, actor_for_token
from eng_workbench.metrics import render, snapshot
from eng_workbench.review import submit_review
from eng_workbench.store import Store, build_lab_store
from eng_workbench.tools import ToolGateway


class RunBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    build_id: str
    failure_code: str


class ReviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["approve", "correct"]
    corrected_cause: str = ""
    note: str = ""


class ToolBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jsonrpc: str
    id: int | str
    method: str
    params: dict[str, Any] | None = None


def _dist() -> Path | None:
    candidates = (
        Path("/app/web/dist"),
        Path(__file__).resolve().parents[2] / "web" / "dist",
    )
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


def _bearer(request: Request) -> Actor:
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise FlowError("unauthorized", "bearer token is required", 401)
    actor = actor_for_token(header.removeprefix("Bearer ").strip())
    if actor is None:
        raise FlowError("unauthorized", "bearer token is required", 401)
    return actor


def create_app(store: Store | None = None) -> FastAPI:
    app = FastAPI(title="Engineering AI Test Analytics Workbench")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.store = store if store is not None else build_lab_store()
    app.state.tools = ToolGateway(app.state.store)
    app.state.agent = Investigator(app.state.store, app.state.tools)

    @app.exception_handler(FlowError)
    def on_flow(_: Request, exc: FlowError) -> JSONResponse:
        body = {"error": exc.code, "message": exc.message}
        return JSONResponse(status_code=exc.status, content=body)

    @app.get("/health")
    def health() -> dict[str, Any]:
        allow = os.environ.get("ENG_WORKBENCH_ALLOW_REMOTE") == "1"
        return {
            "status": "ok",
            "organization": ORG,
            "notice": NOTICE,
            "device_calls": app.state.store.device_calls,
            "adapters": adapter_report(os.environ.get("DATABASE_URL"), allow),
        }

    @app.get("/api/v1/builds")
    def builds(request: Request) -> dict[str, Any]:
        actor = _bearer(request)
        return {"builds": app.state.store.builds(actor.tenant_id)}

    @app.post("/api/v1/investigations")
    def start(body: RunBody, request: Request) -> dict[str, Any]:
        actor = _bearer(request)
        return app.state.agent.investigate(actor, body.build_id, body.failure_code)

    @app.get("/api/v1/investigations/{investigation_id}")
    def read_investigation(investigation_id: str, request: Request) -> dict[str, Any]:
        actor = _bearer(request)
        row = app.state.store.get_investigation(investigation_id)
        if row is None or row["tenant_id"] != actor.tenant_id:
            raise FlowError("not_found", "investigation is not in this tenant", 404)
        return row

    @app.get("/api/v1/investigations")
    def list_investigations(request: Request) -> dict[str, Any]:
        actor = _bearer(request)
        return {"investigations": app.state.store.list_investigations(actor.tenant_id)}

    @app.post("/api/v1/investigations/{investigation_id}/review")
    def review(investigation_id: str, body: ReviewBody, request: Request) -> dict[str, Any]:
        actor = _bearer(request)
        return submit_review(
            app.state.store,
            actor,
            investigation_id,
            body.action,
            body.corrected_cause,
            body.note,
        )

    @app.get("/api/v1/builds/compare")
    def compare(left: str, right: str, request: Request) -> dict[str, Any]:
        actor = _bearer(request)
        return {"rows": app.state.store.compare(actor.tenant_id, left, right)}

    @app.get("/api/v1/dashboard")
    def dashboard(request: Request) -> dict[str, Any]:
        actor = _bearer(request)
        store = app.state.store
        temps = []
        for build in store.builds(actor.tenant_id):
            temps.append(
                {
                    "build_id": build["build_id"],
                    "mean_temperature_c": store.mean_temperature(
                        actor.tenant_id, str(build["build_id"])
                    ),
                }
            )
        stats = store.correction_stats()
        reviewed = stats["reviews"]
        return {
            "notice": NOTICE,
            "pass_rates": store.pass_rates(actor.tenant_id),
            "trend": store.trend(actor.tenant_id),
            "mean_temperature_c": temps,
            "dq_failures": store.dq_count(),
            "dq_by_reason": store.dq_by_reason(),
            "usage": store.usage_summary(),
            "reviews": reviewed,
            "corrections": stats["corrections"],
            "correction_rate": (stats["corrections"] / reviewed) if reviewed else 0.0,
            "device_calls": store.device_calls,
        }

    @app.get("/metrics")
    def metrics() -> PlainTextResponse:
        return PlainTextResponse(render(snapshot(app.state.store)), media_type="text/plain")

    @app.post("/api/v1/tools")
    def tools(body: ToolBody, request: Request) -> dict[str, Any]:
        actor = _bearer(request)
        message: dict[str, Any] = {
            "jsonrpc": body.jsonrpc,
            "id": body.id,
            "method": body.method,
            "params": body.params,
        }
        return app.state.tools.handle(actor, message)

    dist = _dist()
    if dist is not None:
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(dist / "index.html")

    return app


app = create_app()
