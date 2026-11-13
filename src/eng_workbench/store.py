"""SQLite lab store. Postgres uses the same SQL through a thin wrapper."""

import json
import sqlite3
from typing import Any, Protocol

from eng_workbench.identity import TENANT
from eng_workbench.quality import reject_reason
from eng_workbench.semantic import LINEAGE, VIEWS
from eng_workbench.synthetic import dirty_records, lab_records


class Database(Protocol):
    def execute(self, sql: str, params: tuple[object, ...] = ()) -> Any: ...


SCHEMA = (
    """
    CREATE TABLE firmware_builds (
      tenant_id TEXT NOT NULL,
      build_id TEXT NOT NULL,
      version TEXT NOT NULL,
      created_at TEXT NOT NULL,
      change_note TEXT NOT NULL,
      parent_build_id TEXT NOT NULL,
      PRIMARY KEY (tenant_id, build_id)
    )
    """,
    """
    CREATE TABLE devices (
      tenant_id TEXT NOT NULL,
      device_id TEXT NOT NULL,
      model_code TEXT NOT NULL,
      PRIMARY KEY (tenant_id, device_id)
    )
    """,
    """
    CREATE TABLE test_runs (
      tenant_id TEXT NOT NULL,
      run_id TEXT NOT NULL,
      build_id TEXT NOT NULL,
      device_id TEXT NOT NULL,
      suite TEXT NOT NULL,
      started_at TEXT NOT NULL,
      status TEXT NOT NULL,
      PRIMARY KEY (tenant_id, run_id)
    )
    """,
    """
    CREATE TABLE failures (
      tenant_id TEXT NOT NULL,
      failure_id TEXT NOT NULL,
      run_id TEXT NOT NULL,
      build_id TEXT NOT NULL,
      code TEXT NOT NULL,
      observed_at TEXT NOT NULL,
      PRIMARY KEY (tenant_id, failure_id)
    )
    """,
    """
    CREATE TABLE log_chunks (
      tenant_id TEXT NOT NULL,
      chunk_id TEXT NOT NULL,
      run_id TEXT NOT NULL,
      build_id TEXT NOT NULL,
      code TEXT NOT NULL,
      body TEXT NOT NULL,
      PRIMARY KEY (tenant_id, chunk_id)
    )
    """,
    """
    CREATE TABLE telemetry (
      tenant_id TEXT NOT NULL,
      sample_id TEXT NOT NULL,
      run_id TEXT NOT NULL,
      metric TEXT NOT NULL,
      value DOUBLE PRECISION NOT NULL,
      observed_at TEXT NOT NULL,
      PRIMARY KEY (tenant_id, sample_id)
    )
    """,
    """
    CREATE TABLE dq_rejects (
      reject_id INTEGER PRIMARY KEY,
      source_name TEXT NOT NULL,
      reason TEXT NOT NULL,
      raw_text TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE lineage (
      child_name TEXT NOT NULL,
      parent_name TEXT NOT NULL,
      PRIMARY KEY (child_name, parent_name)
    )
    """,
    """
    CREATE TABLE investigations (
      investigation_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL,
      requester_id TEXT NOT NULL,
      build_id TEXT NOT NULL,
      failure_code TEXT NOT NULL,
      classification TEXT NOT NULL,
      cause TEXT NOT NULL,
      citations_json TEXT NOT NULL,
      status TEXT NOT NULL,
      wall_seconds DOUBLE PRECISION NOT NULL,
      steps_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE investigation_steps (
      investigation_id TEXT NOT NULL,
      step_name TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      PRIMARY KEY (investigation_id, step_name)
    )
    """,
    """
    CREATE TABLE reviews (
      review_id TEXT PRIMARY KEY,
      investigation_id TEXT NOT NULL,
      reviewer_id TEXT NOT NULL,
      action TEXT NOT NULL,
      corrected_cause TEXT NOT NULL,
      note TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE usage_events (
      event_id INTEGER PRIMARY KEY,
      actor_id TEXT NOT NULL,
      action TEXT NOT NULL,
      subject_id TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE audit_events (
      audit_id INTEGER PRIMARY KEY,
      actor_id TEXT NOT NULL,
      action TEXT NOT NULL,
      outcome TEXT NOT NULL,
      detail TEXT NOT NULL
    )
    """,
)


class PgDatabase:
    """psycopg connection. The integration test constructs it."""

    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> Any:
        cursor = self.conn.cursor()
        cursor.execute(sql.replace("?", "%s"), params)
        return cursor


class SqliteDatabase:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> Any:
        return self.conn.execute(sql, params)


class Store:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._seq = 0
        self.device_calls = 0

    def next_id(self) -> int:
        self._seq += 1
        return self._seq

    def apply_schema(self) -> None:
        for statement in SCHEMA:
            self.db.execute(statement)
        for name, select in VIEWS:
            self.db.execute(f"CREATE VIEW {name} AS {select}")
        for child, parent in LINEAGE:
            self.db.execute(
                "INSERT INTO lineage (child_name, parent_name) VALUES (?, ?)",
                (child, parent),
            )

    def load_lab(self, include_dirty: bool = True) -> None:
        records = lab_records()
        self._insert_clean(records)
        if include_dirty:
            known = {str(row["build_id"]) for row in records["builds"]}
            for row in dirty_records():
                kind = str(row["kind"])
                reason = reject_reason(kind, row, known)
                if reason is None:
                    raise RuntimeError("dirty row passed quality checks")
                self.db.execute(
                    """
                    INSERT INTO dq_rejects (reject_id, source_name, reason, raw_text)
                    VALUES (?, ?, ?, ?)
                    """,
                    (self.next_id(), kind, reason, json.dumps(row, sort_keys=True)),
                )

    def _insert_clean(self, records: dict[str, list[dict[str, object]]]) -> None:
        known = {str(row["build_id"]) for row in records["builds"]}
        for row in records["builds"]:
            self.db.execute(
                """
                INSERT INTO firmware_builds (
                  tenant_id, build_id, version, created_at, change_note, parent_build_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["tenant_id"],
                    row["build_id"],
                    row["version"],
                    row["created_at"],
                    row["change_note"],
                    row["parent_build_id"],
                ),
            )
        for row in records["devices"]:
            self.db.execute(
                "INSERT INTO devices (tenant_id, device_id, model_code) VALUES (?, ?, ?)",
                (row["tenant_id"], row["device_id"], row["model_code"]),
            )
        for row in records["runs"]:
            reason = reject_reason("run", row, known)
            if reason:
                raise RuntimeError(reason)
            self.db.execute(
                """
                INSERT INTO test_runs (
                  tenant_id, run_id, build_id, device_id, suite, started_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["tenant_id"],
                    row["run_id"],
                    row["build_id"],
                    row["device_id"],
                    row["suite"],
                    row["started_at"],
                    row["status"],
                ),
            )
        for row in records["failures"]:
            reason = reject_reason("failure", row, known)
            if reason:
                raise RuntimeError(reason)
            self.db.execute(
                """
                INSERT INTO failures (
                  tenant_id, failure_id, run_id, build_id, code, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["tenant_id"],
                    row["failure_id"],
                    row["run_id"],
                    row["build_id"],
                    row["code"],
                    row["observed_at"],
                ),
            )
        for row in records["logs"]:
            self.db.execute(
                """
                INSERT INTO log_chunks (
                  tenant_id, chunk_id, run_id, build_id, code, body
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["tenant_id"],
                    row["chunk_id"],
                    row["run_id"],
                    row["build_id"],
                    row["code"],
                    row["body"],
                ),
            )
        for row in records["telemetry"]:
            reason = reject_reason("telemetry", row, known)
            if reason:
                raise RuntimeError(reason)
            self.db.execute(
                """
                INSERT INTO telemetry (
                  tenant_id, sample_id, run_id, metric, value, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["tenant_id"],
                    row["sample_id"],
                    row["run_id"],
                    row["metric"],
                    row["value"],
                    row["observed_at"],
                ),
            )

    def query(self, sql: str, params: tuple[object, ...] = ()) -> list[dict[str, Any]]:
        cursor = self.db.execute(sql, params)
        description = cursor.description or ()
        columns = [str(item[0]) for item in description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def one(self, sql: str, params: tuple[object, ...] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def failure_count(self, tenant_id: str, build_id: str, code: str) -> int:
        row = self.one(
            """
            SELECT COUNT(*) AS n FROM failures
            WHERE tenant_id = ? AND build_id = ? AND code = ?
            """,
            (tenant_id, build_id, code),
        )
        return int(row["n"]) if row else 0

    def change_note(self, tenant_id: str, build_id: str) -> str | None:
        row = self.one(
            """
            SELECT change_note FROM firmware_builds
            WHERE tenant_id = ? AND build_id = ?
            """,
            (tenant_id, build_id),
        )
        return str(row["change_note"]) if row else None

    def search_logs(self, tenant_id: str, build_id: str, code: str) -> list[dict[str, Any]]:
        return self.query(
            """
            SELECT chunk_id, run_id, build_id, code, body
            FROM log_chunks
            WHERE tenant_id = ? AND build_id = ? AND code = ?
            ORDER BY chunk_id
            """,
            (tenant_id, build_id, code),
        )

    def history_row(self, tenant_id: str, build_id: str, code: str) -> dict[str, Any] | None:
        return self.one(
            """
            SELECT tenant_id, build_id, code, runs, failures, rate, prior_mean
            FROM regression_history
            WHERE tenant_id = ? AND build_id = ? AND code = ?
            """,
            (tenant_id, build_id, code),
        )

    def example_failures(self, tenant_id: str, code: str, before_build: str) -> list[str]:
        rows = self.query(
            """
            SELECT failure_id FROM failures
            WHERE tenant_id = ? AND code = ? AND build_id < ?
            ORDER BY failure_id DESC
            LIMIT 2
            """,
            (tenant_id, code, before_build),
        )
        return [str(row["failure_id"]) for row in rows]

    def pass_rates(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.query(
            """
            SELECT build_id, runs, passes, pass_rate
            FROM build_quality
            WHERE tenant_id = ?
            ORDER BY build_id
            """,
            (tenant_id,),
        )

    def trend(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.query(
            """
            SELECT build_id, code, failures
            FROM failure_trend
            WHERE tenant_id = ?
            ORDER BY build_id, code
            """,
            (tenant_id,),
        )

    def compare(self, tenant_id: str, left: str, right: str) -> list[dict[str, Any]]:
        rows = self.query(
            """
            SELECT build_id, code, failures, rate
            FROM regression_history
            WHERE tenant_id = ? AND build_id IN (?, ?)
            ORDER BY code, build_id
            """,
            (tenant_id, left, right),
        )
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            code = str(row["code"])
            slot = grouped.setdefault(
                code,
                {
                    "code": code,
                    "left_rate": None,
                    "right_rate": None,
                    "left_failures": 0,
                    "right_failures": 0,
                },
            )
            if row["build_id"] == left:
                slot["left_rate"] = row["rate"]
                slot["left_failures"] = row["failures"]
            if row["build_id"] == right:
                slot["right_rate"] = row["rate"]
                slot["right_failures"] = row["failures"]
        return [grouped[code] for code in sorted(grouped)]

    def mean_temperature(self, tenant_id: str, build_id: str) -> float | None:
        row = self.one(
            """
            SELECT AVG(t.value) AS mean_c
            FROM telemetry t
            JOIN test_runs r ON r.tenant_id = t.tenant_id AND r.run_id = t.run_id
            WHERE t.tenant_id = ? AND r.build_id = ? AND t.metric = 'temperature_c'
            """,
            (tenant_id, build_id),
        )
        if row is None or row["mean_c"] is None:
            return None
        return float(row["mean_c"])

    def builds(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.query(
            """
            SELECT build_id, version, created_at, change_note
            FROM firmware_builds
            WHERE tenant_id = ?
            ORDER BY build_id
            """,
            (tenant_id,),
        )

    def dq_count(self) -> int:
        row = self.one("SELECT COUNT(*) AS n FROM dq_rejects")
        return int(row["n"]) if row else 0

    def dq_by_reason(self) -> list[dict[str, Any]]:
        return self.query(
            "SELECT reason, COUNT(*) AS n FROM dq_rejects GROUP BY reason ORDER BY reason"
        )

    def record_usage(self, actor_id: str, action: str, subject_id: str) -> None:
        self.db.execute(
            """
            INSERT INTO usage_events (event_id, actor_id, action, subject_id)
            VALUES (?, ?, ?, ?)
            """,
            (self.next_id(), actor_id, action, subject_id),
        )

    def record_audit(self, actor_id: str, action: str, outcome: str, detail: str) -> None:
        self.db.execute(
            """
            INSERT INTO audit_events (audit_id, actor_id, action, outcome, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (self.next_id(), actor_id, action, outcome, detail),
        )

    def denial_count(self) -> int:
        row = self.one(
            "SELECT COUNT(*) AS n FROM audit_events WHERE outcome = 'denied'"
        )
        return int(row["n"]) if row else 0

    def save_step(self, investigation_id: str, name: str, payload: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT INTO investigation_steps (investigation_id, step_name, payload_json)
            VALUES (?, ?, ?)
            """,
            (investigation_id, name, json.dumps(payload, sort_keys=True)),
        )

    def get_step(self, investigation_id: str, name: str) -> dict[str, Any] | None:
        row = self.one(
            """
            SELECT payload_json FROM investigation_steps
            WHERE investigation_id = ? AND step_name = ?
            """,
            (investigation_id, name),
        )
        if row is None:
            return None
        loaded = json.loads(str(row["payload_json"]))
        if not isinstance(loaded, dict):
            raise RuntimeError("step payload was not an object")
        return loaded

    def save_investigation(self, row: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT INTO investigations (
              investigation_id, tenant_id, requester_id, build_id, failure_code,
              classification, cause, citations_json, status, wall_seconds, steps_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["investigation_id"],
                row["tenant_id"],
                row["requester_id"],
                row["build_id"],
                row["failure_code"],
                row["classification"],
                row["cause"],
                json.dumps(row["citations"]),
                row["status"],
                row["wall_seconds"],
                json.dumps(row["steps"]),
            ),
        )

    def get_investigation(self, investigation_id: str) -> dict[str, Any] | None:
        row = self.one(
            "SELECT * FROM investigations WHERE investigation_id = ?",
            (investigation_id,),
        )
        if row is None:
            return None
        row["citations"] = json.loads(str(row["citations_json"]))
        row["steps"] = json.loads(str(row["steps_json"]))
        return row

    def list_investigations(self, tenant_id: str) -> list[dict[str, Any]]:
        rows = self.query(
            """
            SELECT * FROM investigations
            WHERE tenant_id = ?
            ORDER BY investigation_id
            """,
            (tenant_id,),
        )
        for row in rows:
            row["citations"] = json.loads(str(row["citations_json"]))
            row["steps"] = json.loads(str(row["steps_json"]))
        return rows

    def set_status(self, investigation_id: str, status: str, cause: str) -> None:
        self.db.execute(
            "UPDATE investigations SET status = ?, cause = ? WHERE investigation_id = ?",
            (status, cause, investigation_id),
        )

    def save_review(self, row: dict[str, Any]) -> None:
        self.db.execute(
            """
            INSERT INTO reviews (
              review_id, investigation_id, reviewer_id, action, corrected_cause, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["review_id"],
                row["investigation_id"],
                row["reviewer_id"],
                row["action"],
                row["corrected_cause"],
                row["note"],
            ),
        )

    def get_review(self, investigation_id: str) -> dict[str, Any] | None:
        return self.one(
            "SELECT * FROM reviews WHERE investigation_id = ?",
            (investigation_id,),
        )

    def correction_stats(self) -> dict[str, int]:
        reviews = self.one("SELECT COUNT(*) AS n FROM reviews")
        corrections = self.one(
            "SELECT COUNT(*) AS n FROM reviews WHERE action = 'correct'"
        )
        return {
            "reviews": int(reviews["n"]) if reviews else 0,
            "corrections": int(corrections["n"]) if corrections else 0,
        }

    def usage_summary(self) -> dict[str, Any]:
        actors = self.query("SELECT DISTINCT actor_id FROM usage_events ORDER BY actor_id")
        repeats = self.query(
            """
            SELECT subject_id, COUNT(*) AS n
            FROM usage_events
            WHERE action = 'investigate'
            GROUP BY subject_id
            HAVING COUNT(*) > 1
            """
        )
        total = self.one(
            "SELECT COUNT(*) AS n FROM usage_events WHERE action = 'investigate'"
        )
        return {
            "distinct_actors": [str(row["actor_id"]) for row in actors],
            "investigate_events": int(total["n"]) if total else 0,
            "repeated_subjects": len(repeats),
        }


def build_lab_store(include_dirty: bool = True) -> Store:
    store = Store(SqliteDatabase())
    store.apply_schema()
    store.load_lab(include_dirty=include_dirty)
    return store


def empty_store() -> Store:
    store = Store(SqliteDatabase())
    store.apply_schema()
    return store


# Imported by health to show the default tenant without querying.
DEFAULT_TENANT = TENANT
