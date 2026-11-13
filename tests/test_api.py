from fastapi.testclient import TestClient

from eng_workbench.identity import NOTICE, ORG


def test_health_reports_gates_without_device_calls(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["organization"] == ORG
    assert body["notice"] == NOTICE
    assert body["device_calls"] == 0
    assert body["adapters"]["hosted_model"] == "not-run"
    assert body["adapters"]["database"] == "sqlite-default"


def test_missing_token_is_unauthorized(client: TestClient) -> None:
    response = client.post(
        "/api/v1/investigations",
        json={"build_id": "SYN-FW-417", "failure_code": "SYN-CODE-THERM"},
    )
    assert response.status_code == 401


def test_extra_field_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/investigations",
        headers={"Authorization": "Bearer lab-ida"},
        json={"build_id": "SYN-FW-417", "failure_code": "SYN-CODE-THERM", "approved": True},
    )
    assert response.status_code == 422


def test_investigation_compare_and_review(client: TestClient) -> None:
    headers = {"Authorization": "Bearer lab-ida"}
    started = client.post(
        "/api/v1/investigations",
        headers=headers,
        json={"build_id": "SYN-FW-417", "failure_code": "SYN-CODE-THERM"},
    )
    assert started.status_code == 200
    body = started.json()
    assert body["classification"] == "regression"
    assert body["status"] == "DRAFT"
    assert body["notice"] == NOTICE
    assert body["citations"]
    assert all(item.startswith("SYN-LOG-417-") for item in body["citations"])
    assert "marshline" not in str(body).lower()
    fetched = client.get(f"/api/v1/investigations/{body['investigation_id']}", headers=headers)
    assert fetched.status_code == 200
    outsider = client.get(
        f"/api/v1/investigations/{body['investigation_id']}",
        headers={"Authorization": "Bearer lab-bex"},
    )
    assert outsider.status_code == 404
    compared = client.get(
        "/api/v1/builds/compare",
        headers=headers,
        params={"left": "SYN-FW-416", "right": "SYN-FW-417"},
    )
    assert compared.status_code == 200
    therm = next(row for row in compared.json()["rows"] if row["code"] == "SYN-CODE-THERM")
    assert therm["right_failures"] == 12
    assert therm["left_failures"] == 1
    own = client.post(
        f"/api/v1/investigations/{body['investigation_id']}/review",
        headers=headers,
        json={"action": "approve"},
    )
    assert own.status_code == 403
    reviewed = client.post(
        f"/api/v1/investigations/{body['investigation_id']}/review",
        headers={"Authorization": "Bearer lab-otto"},
        json={"action": "approve", "note": "draft accepted"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "APPROVED"
    again = client.post(
        f"/api/v1/investigations/{body['investigation_id']}/review",
        headers={"Authorization": "Bearer lab-otto"},
        json={"action": "approve"},
    )
    assert again.status_code == 409


def test_dashboard_and_metrics(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard", headers={"Authorization": "Bearer lab-ida"})
    assert response.status_code == 200
    body = response.json()
    assert body["dq_failures"] == 9
    assert body["device_calls"] == 0
    assert body["pass_rates"]
    metrics = client.get("/metrics")
    assert "eng_dq_failures_total 9" in metrics.text
    assert "eng_device_calls_total 0" in metrics.text


def test_cross_tenant_tool_and_flash(client: TestClient) -> None:
    denied = client.post(
        "/api/v1/tools",
        headers={"Authorization": "Bearer lab-ida"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_logs",
                "arguments": {
                    "tenant_id": "SYN-TENANT-MARSHLINE",
                    "build_id": "SYN-FW-M01",
                    "code": "SYN-CODE-MARSH",
                },
            },
        },
    )
    assert denied.status_code == 200
    assert denied.json()["error"]["message"] == "tenant_boundary"
    flash = client.post(
        "/api/v1/tools",
        headers={"Authorization": "Bearer lab-ida"},
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "flash_firmware", "arguments": {"build_id": "SYN-FW-417"}},
        },
    )
    assert flash.json()["error"]["message"] == "protected_tool"
    listed = client.post(
        "/api/v1/tools",
        headers={"Authorization": "Bearer lab-ida"},
        json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
    )
    names = [item["name"] for item in listed.json()["result"]["tools"]]
    assert "flash_firmware" in names
    assert "search_logs" in names
