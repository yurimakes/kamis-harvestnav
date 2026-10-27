from datetime import date
import asyncio
import copy
import json

import httpx
import pytest

from backend.app.services import kamis

START, END = date(2026, 10, 1), date(2026, 10, 27)


@pytest.fixture
def payload():
    # Purpose-built schema fixture, NOT a real KAMIS observation or saved response.
    common = {"itemname": "배추", "kindname": "가상 품종", "countyname": "서울", "marketname": "가상 조사시장", "yyyy": "2026", "unit": "1kg"}
    return {"data": {"error_code": "000", "item": [
        {**common, "regday": "10/27", "price": "1,100"},
        {**common, "regday": "10/20", "price": "1,000"},
        {**common, "regday": "10/21", "price": "-"},
        {**common, "regday": "평균", "price": "1,050"},
        {**common, "regday": "10/27", "price": "1,100"}]}}


def test_normalize_dates_missing_duplicates_and_week_reference(payload):
    series, quality = kamis.normalize(payload, START, END)
    assert len(series) == 1
    assert [p["date"] for p in series[0]["prices"]] == ["2026-10-20", "2026-10-27"]
    assert quality == {"missing_rows": 1, "duplicate_rows": 1, "aggregate_rows": 1}
    stats = series[0]["analysis"]
    assert stats["change_pct"] == 10
    assert stats["reference_date"] == "2026-10-20"
    assert stats["window_observations"] == 1
    assert stats["window_cv_pct"] is None


@pytest.mark.parametrize("unit", ["1포기", "10kg", "상자", ""])
def test_no_implicit_unit_conversion(payload, unit):
    payload["data"]["item"][0]["unit"] = unit
    with pytest.raises(kamis.SchemaError):
        kamis.normalize(payload, START, END)


def test_conflicting_duplicate_fails(payload):
    payload["data"]["item"][-1]["price"] = "1,200"
    with pytest.raises(kamis.SchemaError):
        kamis.normalize(payload, START, END)


def test_series_not_averaged_across_markets(payload):
    other = copy.deepcopy(payload["data"]["item"][0])
    other.update(marketname="다른 가상시장", price="3000")
    payload["data"]["item"].append(other)
    series, _ = kamis.normalize(payload, START, END)
    assert len(series) == 2
    assert sorted(x["analysis"]["latest"] for x in series) == [1100, 3000]


def test_missing_auth_does_not_use_synthetic(monkeypatch):
    monkeypatch.delenv("KAMIS_CERT_KEY", raising=False)
    response = asyncio.run(kamis.KamisClient().prices(START, END, "1101", "03", "04"))
    assert response["source"] == "unavailable"
    assert response["status"] == "not_configured"
    assert response["series"] == []
    assert response["retrieved_at"] is None


def test_transport_error_redacts_credentials(monkeypatch):
    monkeypatch.setenv("KAMIS_CERT_KEY", "TEST_ONLY_SENTINEL")
    monkeypatch.setenv("KAMIS_CERT_ID", "TEST_ONLY_ID")
    class FailingClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, *args, **kwargs):
            raise httpx.ConnectError("query contains TEST_ONLY_SENTINEL")
    monkeypatch.setattr(kamis.httpx, "AsyncClient", FailingClient)
    r = asyncio.run(kamis.KamisClient().prices(START, END, "1101", "03", "04"))
    assert r["status"] == "upstream_error"
    assert r["source"] == "unavailable"
    assert "TEST_ONLY" not in json.dumps(r)


def test_empty_no_data_code(payload):
    payload["data"]["error_code"] = "001"
    assert kamis.normalize(payload, START, END)[0] == []


def test_response_success_cache_and_derived_stats(monkeypatch, payload):
    monkeypatch.setenv("KAMIS_CERT_KEY", "TEST_ONLY_SENTINEL")
    monkeypatch.setenv("KAMIS_CERT_ID", "TEST_ONLY_ID")
    calls = []
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            calls.append(kwargs)
            return httpx.Response(200, json=payload, request=httpx.Request("GET", url))
    monkeypatch.setattr(kamis.httpx, "AsyncClient", FakeClient)
    c = kamis.KamisClient()
    r = asyncio.run(c.prices(START, END, "1101", "03", "04"))
    assert r["source"] == "kamis" and r["status"] == "live"
    assert r["as_of"] == "2026-10-27"
    assert "TEST_ONLY" not in json.dumps(r)
    assert asyncio.run(c.prices(START, END, "1101", "03", "04"))["cached"] is True
    assert len(calls) == 1


@pytest.mark.parametrize("code,kind", [("900", "authentication"), ("200", "parameters"), ("999", "schema")])
def test_upstream_error_categories_without_echoing_raw_content(monkeypatch, code, kind):
    monkeypatch.setenv("KAMIS_CERT_KEY", "TEST_ONLY_SENTINEL")
    monkeypatch.setenv("KAMIS_CERT_ID", "TEST_ONLY_ID")
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            return httpx.Response(200, json={"data": {"error_code": code, "message": "TEST_ONLY_SENTINEL"}}, request=httpx.Request("GET", url))
    monkeypatch.setattr(kamis.httpx, "AsyncClient", Client)
    result = asyncio.run(kamis.KamisClient().prices(START, END, "1101", "03", "04"))
    assert result["error_kind"] == kind
    assert result["status"] == "upstream_error" and result["series"] == []
    assert result["retrieved_at"] is None
    assert "TEST_ONLY" not in json.dumps(result)


@pytest.mark.parametrize("value", ["", "   ", " EXAMPLE_KEY_NOT_REAL "])
def test_blank_or_example_auth_is_not_configured(monkeypatch, value):
    monkeypatch.setenv("KAMIS_CERT_KEY", value)
    monkeypatch.setenv("KAMIS_CERT_ID", "TEST_ONLY_ID")
    assert kamis.configured() is False


def test_reference_gap_is_actual_calendar_days():
    result = kamis.stats([{"date": "2026-10-16", "price_per_kg": 1000},
                          {"date": "2026-10-19", "price_per_kg": 1100},
                          {"date": "2026-10-27", "price_per_kg": 1320}])
    assert result["reference_date"] == "2026-10-19"
    assert result["reference_gap_days"] == 8
    assert result["change_pct"] == 20
    assert result["observations"] == 3
    assert result["first_date"] == "2026-10-16"
    assert result["window_observations"] == 1
