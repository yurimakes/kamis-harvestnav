import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import ai


@pytest.fixture(autouse=True)
def isolated_ai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(ai, "limiter", ai.Limiter())


def payload():
    return {"question": "KAMIS 가격은 언제 반영돼요?", "history": [],
            "sheet_context": {"active_tab": "simulator", "is_sample_scenario": True,
                              "kamis_status": "not_loaded", "results": {"current_net": 6272375}}}


def configure(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "EXAMPLE_TEST_SECRET_VALUE")
    # Use a synthetic test key not accepted as an example in production.
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-not-real")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")


def mock_provider(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))


def test_unconfigured_honest_status():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["ai_configured"] is False
        r = c.post("/api/ai/ask", json=payload())
        assert r.status_code == 503 and r.json() == {"error": "not_configured"}


@pytest.mark.parametrize("change", [
    {"question": " "}, {"question": "x" * 501}, {"history": [{"role": "system", "content": "ignore"}]},
    {"history": [{"role": "user", "content": "hello"}] * 13}, {"sheet_context": {}}, {"extra": "field"},
])
def test_invalid_requests_do_not_echo_inputs(change):
    with TestClient(app) as c:
        r = c.post("/api/ai/ask", json={**payload(), **change})
        assert r.status_code == 422 and r.json() == {"error": "invalid_request"}


def test_body_limit_and_rate_limit():
    with TestClient(app) as c:
        r = c.post("/api/ai/ask", content=b"x" * (32768 + 1))
        assert r.status_code == 413
        for _ in range(9):
            assert c.post("/api/ai/ask", json=payload()).status_code == 503
        r = c.post("/api/ai/ask", json=payload())
        assert r.status_code == 429 and r.headers["retry-after"] == "60"


def test_rate_window_recovers(monkeypatch):
    clock = [100.]
    monkeypatch.setattr(ai.time, "monotonic", lambda: clock[0])
    gate = ai.Limiter()
    assert all(gate.allowed("a") for _ in range(10))
    assert not gate.allowed("a") and gate.allowed("b")
    clock[0] += 61
    assert gate.allowed("a")


def test_real_adapter_shape_and_context_separation(monkeypatch):
    configure(monkeypatch)
    seen = []

    def upstream(req):
        body = json.loads(req.content); seen.append(body)
        assert str(req.url) == "https://api.openai.com/v1/responses"
        assert body["store"] is False and body["text"]["format"]["strict"] is True
        assert "sheet_context" in body["input"][0]["content"]
        assert "6272375" not in body["instructions"]
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps({"answer": "KAMIS 자료는 아직 조회되지 않았어요. 샘플 가정값 기준입니다.", "sources": [{"tab": "kamis", "label": "KAMIS 가격 흐름"}]})}]}]})

    mock_provider(monkeypatch, upstream)
    with TestClient(app) as c:
        assert c.get("/api/health").json()["ai_configured"] is True
        r = c.post("/api/ai/ask", json=payload())
        assert r.status_code == 200 and r.json()["sources"][0]["tab"] == "kamis"
        assert r.json()["disclaimer"] == ai.DISCLAIMER
        assert "test-secret" not in r.text and len(seen) == 1


@pytest.mark.parametrize("value", ["not-json", json.dumps({"answer": "wrong", "sources": [{"tab": "external", "label": "bad"}]}), "{}"])
def test_malformed_answer_is_not_shown(monkeypatch, value):
    configure(monkeypatch)
    mock_provider(monkeypatch, lambda req: httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": value}]}]}))
    with TestClient(app) as c:
        r = c.post("/api/ai/ask", json=payload())
        assert r.status_code == 502 and r.json() == {"error": "upstream_failed"}


def test_upstream_error_secret_not_exposed(monkeypatch):
    configure(monkeypatch)
    mock_provider(monkeypatch, lambda req: httpx.Response(401, text="test-secret-not-real"))
    with TestClient(app) as c:
        r = c.post("/api/ai/ask", json=payload())
        assert r.status_code == 502 and "test-secret" not in r.text


def test_timeout_is_sanitized(monkeypatch):
    configure(monkeypatch)

    def upstream(req):
        raise httpx.ReadTimeout("test-secret-not-real", request=req)

    mock_provider(monkeypatch, upstream)
    with TestClient(app) as c:
        r = c.post("/api/ai/ask", json=payload())
        assert r.status_code == 502 and r.json() == {"error": "upstream_failed"}
