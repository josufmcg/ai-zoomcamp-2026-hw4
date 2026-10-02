import pytest
from fastapi.testclient import TestClient

from app import main
from app.telemetry import meter_provider


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "orders.db")
    with TestClient(main.app) as test_client:
        yield test_client


def test_health_and_seeded_orders(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    orders = client.get("/api/orders").json()
    assert len(orders) == 3
    assert {order["priority"] for order in orders} == {"standard", "express"}


def test_create_and_update_order(client):
    response = client.post(
        "/api/orders",
        json={"customer": "Taylor", "item": "Mug", "priority": "standard"},
    )
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert client.get(f"/api/orders/{order_id}").json()["status"] == "received"
    updated = client.patch(f"/api/orders/{order_id}", json={"status": "shipped"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "shipped"


def test_order_lookup_emits_log_and_trace(client, capsys):
    assert client.get("/api/orders/standard-1001").status_code == 200
    assert client.get("/api/orders/missing").status_code == 404
    assert meter_provider.force_flush()

    output = capsys.readouterr().out
    assert "order.lookup" in output
    assert "Order lookup completed" in output
    assert "order.lookup.result" in output
    assert "not_found" in output
    assert "http.server.request.count" in output
    assert '"http.route": "/api/orders/{order_id}"' in output
    assert '"http.response.status_code": 404' in output
