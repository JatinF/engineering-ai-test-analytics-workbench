"""Row checks applied before a record is stored."""

from eng_workbench.synthetic import KNOWN_CODES


def reject_reason(kind: str, row: dict[str, object], known_builds: set[str]) -> str | None:
    if kind == "run":
        build_id = str(row.get("build_id") or "")
        if build_id == "" or build_id not in known_builds:
            return "missing_build"
        started = str(row.get("started_at") or "")
        if started >= "2099":
            return "future_timestamp"
        return None
    if kind == "failure":
        code = str(row.get("code") or "")
        if code not in KNOWN_CODES:
            return "unknown_code"
        return None
    if kind == "telemetry":
        started = str(row.get("observed_at") or "")
        if started >= "2099":
            return "future_timestamp"
        value = float(row["value"])  # type: ignore[arg-type]
        if value < 0:
            return "negative_telemetry"
        return None
    return "unknown_kind"
