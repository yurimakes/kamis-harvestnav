"""Synthetic prices with the packaging label observed in the KAMIS response."""
import asyncio
from datetime import date
from decimal import Decimal
import json

import httpx
import pytest

from backend.app.services import portal


@pytest.mark.parametrize("unit", ["kg(그물망 3포기)", "kg(그물망3포기)",
                                  "KG(그물망 3포기)", "㎏(그물망 3포기)",
                                  "10kg(그물망 3포기)"])
def test_packaging_label_uses_explicit_mass(unit):
    assert portal.weight_kg(unit, "10") == Decimal("10")


@pytest.mark.parametrize("size", [None, "", "0", "-1", "NaN"])
def test_packaging_label_without_valid_mass_is_rejected(size):
    with pytest.raises(portal.SchemaError):
        portal.weight_kg("kg(그물망 3포기)", size)


def test_packaging_label_does_not_hide_conflicting_or_unknown_weight():
    with pytest.raises(portal.SchemaError):
        portal.weight_kg("10kg(그물망 3포기)", "5")
    assert portal.weight_kg("kg(그물망 3포기/5kg)", "10") is None
    assert portal.weight_kg("그물망 3포기", "10") is None
    assert portal.weight_kg("kg(알 수 없는 포장)", "10") is None


def test_packaged_kg_response_reaches_live_result_and_preserves_evidence(monkeypatch):
    # Dates, price and envelope are synthetic; this is not a captured live record.
    rows = [{"se_cd": "02", "ctgry_cd": "200", "item_cd": "211", "item_nm": "배추",
             "vrty_cd": "03", "vrty_nm": "가을", "grd_cd": "04", "sgg_cd": "1101",
             "sgg_nm": "서울", "exmn_ymd": "20261027", "unit": "kg(그물망 3포기)",
             "unit_sz": "10", "exmn_dd_avg_prc": "15,000"}]
    payload = {"header": {"resultCode": "00"}, "body": {
        "pageNo": 1, "totalCount": 1, "items": {"item": rows}}}

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, params):
            return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(portal.httpx, "AsyncClient", Client)
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "TEST_ONLY_PACKAGING")
    result = asyncio.run(portal.PortalClient().prices(
        date(2026, 10, 1), date(2026, 10, 27), "1101", "03", "04"))
    assert result["status"] == "live"
    point = result["series"][0]["prices"][0]
    assert point["price_per_kg"] == 1500
    assert point["weight_kg"] == 10
    assert point["original_price"] == 15000
    assert point["original_unit"] == "kg(그물망 3포기)"
    assert point["original_unit_size"] == "10"
    assert result["quality"]["unsupported_unit_rows"] == 0
    assert result["quality"]["received_rows"] == 1
    assert "TEST_ONLY" not in json.dumps(result)
