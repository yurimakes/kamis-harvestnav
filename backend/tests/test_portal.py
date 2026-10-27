"""Synthetic fixtures matching supplied specification; never real observations."""
import asyncio
from datetime import date
import json

import httpx
import pytest

from backend.app.services import portal

START, END = date(2026, 10, 1), date(2026, 10, 27)


def row(**patch):
    return {"exmn_ymd": "20261027", "se_cd": "02", "ctgry_cd": "200", "item_cd": "211",
            "item_nm": "배추", "vrty_cd": "03", "vrty_nm": "가을", "grd_cd": "04",
            "sgg_cd": "1101", "sgg_nm": "서울", "unit": "kg", "unit_sz": "10",
            "exmn_dd_avg_prc": "15,000", **patch}


def envelope(rows, total=None, page=1):
    return {"response": {"header": {"resultCode": "00"}, "body": {
        "pageNo": page, "totalCount": len(rows) if total is None else total, "items": {"item": rows}}}}


def normalize(rows):
    return portal.normalize(rows, START, END, "1101", "03", "04")


def test_original_weight_conversion_and_evidence():
    series, quality = normalize([row(), row()])
    point = series[0]["prices"][0]
    assert point["price_per_kg"] == 1500
    assert point["original_price"] == 15000 and point["weight_kg"] == 10
    assert quality["duplicate_rows"] == 1
    assert quality["converted_rows"] == 1
    assert series[0]["market"].startswith("지역 조사 평균")


@pytest.mark.parametrize("unit", ["포기", "상자", "망", ""])
def test_unknown_weight_excluded_even_if_converted_field_present(unit):
    series, quality = normalize([row(unit=unit, exmn_dd_cnvs_avg_prc="999")])
    assert series == [] and quality["unsupported_unit_rows"] == 1


@pytest.mark.parametrize("patch", [{"unit": "10kg", "unit_sz": "5"}, {"exmn_dd_avg_prc": "NaN"},
                                    {"item_cd": "212"}, {"sgg_cd": "2100"}, {"grd_cd": "05"}])
def test_bad_unit_numeric_or_identity_fails(patch):
    with pytest.raises(portal.SchemaError):
        normalize([row(**patch)])


def test_duplicate_conflict_and_missing_price():
    with pytest.raises(portal.SchemaError):
        normalize([row(), row(exmn_dd_avg_prc="16000")])
    series, quality = normalize([row(exmn_dd_avg_prc="-")])
    assert series == [] and quality["missing_rows"] == 1


def test_page_envelopes_and_cap():
    assert portal.unpack(envelope([row()]), 1)[1] == 1
    assert portal.unpack({"header": {"resultCode": "00"}, "body": {"pageNo": 1, "totalCount": 0}}, 1) == ([], 0)
    for data in [envelope([], 5001), envelope([], 1, 2)]:
        with pytest.raises(portal.SchemaError):
            portal.unpack(data, 1)


def fake_client(monkeypatch, pages):
    calls = []
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, params):
            calls.append(params)
            return httpx.Response(200, json=pages[len(calls)-1], request=httpx.Request("GET", url))
    monkeypatch.setattr(portal.httpx, "AsyncClient", Client)
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "TEST_ONLY%2BKEY%3D")
    return calls


def test_pagination_decoding_cache_and_redaction(monkeypatch):
    calls = fake_client(monkeypatch, [envelope([row(exmn_ymd="20261020")], 2), envelope([row()], 2, 2)])
    client = portal.PortalClient()
    result = asyncio.run(client.prices(START, END, "1101", "03", "04"))
    assert result["status"] == "live" and len(result["series"][0]["prices"]) == 2
    assert calls[0]["serviceKey"] == "TEST_ONLY+KEY="
    assert calls[0]["cond[exmn_ymd::GTE]"] == "20261001"
    assert "TEST_ONLY" not in json.dumps(result)
    assert asyncio.run(client.prices(START, END, "1101", "03", "04"))["cached"]
    assert len(calls) == 2


def test_incomplete_pages_are_not_success(monkeypatch):
    fake_client(monkeypatch, [envelope([row()], 2), envelope([], 2, 2)])
    result = asyncio.run(portal.PortalClient().prices(START, END, "1101", "03", "04"))
    assert result["status"] == "upstream_error" and result["series"] == []


def test_upstream_auth_error_redacts_message(monkeypatch):
    fake_client(monkeypatch, [{"header": {"resultCode": "30", "resultMsg": "TEST_ONLY_PRIVATE"}}])
    result = asyncio.run(portal.PortalClient().prices(START, END, "1101", "03", "04"))
    assert result["error_kind"] == "authentication"
    assert "TEST_ONLY" not in json.dumps(result)


def test_portal_key_is_required_not_legacy_credentials(monkeypatch):
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    monkeypatch.setenv("KAMIS_CERT_KEY", "TEST_ONLY")
    monkeypatch.setenv("KAMIS_CERT_ID", "TEST_ONLY")
    result = asyncio.run(portal.PortalClient().prices(START, END, "1101", "03", "04"))
    assert result["status"] == "not_configured" and result["series"] == []
