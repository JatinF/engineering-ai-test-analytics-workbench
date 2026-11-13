"""Local-only gates. Unset URLs stay not-run. Health does not dial."""

from urllib.parse import urlparse

from eng_workbench.errors import FlowError

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def classify_url(url: str | None, allow_remote: bool) -> str:
    if url is None or url.strip() == "":
        return "not-run"
    host = (urlparse(url).hostname or "").lower()
    if host in LOCAL_HOSTS:
        return "local"
    if allow_remote:
        return "remote"
    return "blocked"


def ensure_local(url: str | None, allow_remote: bool) -> None:
    kind = classify_url(url, allow_remote)
    if kind == "blocked":
        raise FlowError("remote_blocked", "remote host is blocked", 403)


def adapter_report(database_url: str | None, allow_remote: bool) -> dict[str, str]:
    if database_url is None or database_url.strip() == "":
        database = "sqlite-default"
    else:
        database = classify_url(database_url, allow_remote)
    return {
        "database": database,
        "hosted_model": "not-run",
        "airflow_scheduler": "not-run",
        "terraform": "not-run",
        "eks": "not-run",
        "warehouse": "not-run",
    }
