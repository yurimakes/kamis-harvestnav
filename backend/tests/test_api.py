import json
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
sample = json.loads((Path(__file__).parents[2] / "examples" / "cabbage.synthetic.json").read_text(encoding="utf-8"))


def test_compare_api_result():
    r = client.post("/api/strategies/compare", json=sample)
    assert r.status_code == 200
    assert r.json()["current"]["net"] == 6272375
    assert r.headers["cache-control"] == "no-store"


def test_invalid_and_infeasible_inputs():
    r = client.post("/api/simulation", json={**sample, "quantity_kg": -1})
    assert r.status_code == 422
    invalid = {**sample, "markets": [{**m, "max_kg": 1} for m in sample["markets"]]}
    assert client.post("/api/strategies/compare", json=invalid).status_code == 422


def test_kamis_invalid_window_and_future():
    assert client.get("/api/kamis/prices?start=2026-10-27&end=2026-10-01").status_code == 422
    assert client.get("/api/kamis/prices?start=2026-01-01&end=2026-10-27").status_code == 422
    assert client.get("/api/kamis/prices?start=2099-01-01&end=2099-01-02").status_code == 422


def test_health_and_synthetic_example():
    assert client.get("/api/health").json()["prediction_model"] == "not_loaded"
    assert client.get("/api/examples/scenario").json()["source"] == "synthetic"


def test_errors_do_not_echo_arbitrary_input():
    r = client.post("/api/simulation", json={"unknown": "TEST_ONLY_PRIVATE_MARKER"})
    assert r.status_code == 422
    assert "TEST_ONLY_PRIVATE_MARKER" not in r.text
