"""Server-side KAMIS adapter. Never return credentials or upstream exception URLs."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import math
import os
import re
import time

import httpx

ENDPOINT = "https://www.kamis.or.kr/service/price/xml.do"
DOCUMENTATION = "https://www.kamis.or.kr/customer/reference/openapi_list.do?action=detail&boardno=2"
KST = timezone(timedelta(hours=9))


class SchemaError(ValueError):
    def __init__(self, message, kind="schema"):
        super().__init__(message)
        self.kind = kind


def configured():
    return all(os.getenv(k, "").strip() and not os.getenv(k, "").strip().startswith("EXAMPLE_")
               for k in ("KAMIS_CERT_ID", "KAMIS_CERT_KEY"))


def stats(prices):
    if not prices:
        return None
    last = prices[-1]
    window = [p["price_per_kg"] for p in prices if date.fromisoformat(p["date"]) > date.fromisoformat(last["date"]) - timedelta(days=7)]
    reference = [p for p in prices if date.fromisoformat(p["date"]) <= date.fromisoformat(last["date"]) - timedelta(days=7)]
    previous = reference[-1] if reference else None
    change = (last["price_per_kg"] / previous["price_per_kg"] - 1) * 100 if previous else None
    mean = sum(window) / len(window)
    cv = math.sqrt(sum((p - mean)**2 for p in window) / len(window)) / mean * 100 if len(window) > 1 else None
    return {"latest": last["price_per_kg"], "latest_date": last["date"],
            "calendar_7d_mean": round(mean, 2), "window_observations": len(window),
            "change_pct": round(change, 2) if change is not None else None,
            "reference_date": previous["date"] if previous else None,
            "reference_gap_days": (date.fromisoformat(last["date"]) - date.fromisoformat(previous["date"])).days if previous else None,
            "observations": len(prices), "first_date": prices[0]["date"],
            "window_cv_pct": round(cv, 2) if cv is not None else None,
            "signal": "비교 자료 부족" if change is None else "상승" if change > 0 else "하락" if change < 0 else "보합"}


def normalize(payload, start: date, end: date):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise SchemaError("응답 구조를 확인할 수 없습니다.")
    data = payload["data"]
    code = str(data.get("error_code", ""))
    if code == "001":
        return [], {"missing_rows": 0, "duplicate_rows": 0, "aggregate_rows": 0}
    if code == "900":
        raise SchemaError("KAMIS 자체 API의 인증 ID·KEY와 이용 승인을 확인하세요.", "authentication")
    if code == "200":
        raise SchemaError("품종·등급·지역 코드와 조회 기간을 공식 코드표에서 확인하세요.", "parameters")
    if code != "000":
        raise SchemaError("KAMIS가 정상 응답 코드를 반환하지 않았습니다.")
    items = data.get("item")
    if not isinstance(items, list):
        raise SchemaError("가격 목록을 확인할 수 없습니다.")
    groups = defaultdict(dict)
    quality = {"missing_rows": 0, "duplicate_rows": 0, "aggregate_rows": 0}
    for row in items:
        if not isinstance(row, dict):
            raise SchemaError("가격 레코드 형식이 다릅니다.")
        raw_date = str(row.get("regday", "")).strip()
        if raw_date in ("평균", "평년", "", "합계"):
            quality["aggregate_rows"] += 1
            continue
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
                day = date.fromisoformat(raw_date)
            else:
                year = int(str(row.get("yyyy", "")))
                month, daynum = map(int, raw_date.replace(".", "/").split("/"))
                day = date(year, month, daynum)
        except (ValueError, TypeError):
            raise SchemaError("조사일 형식을 확인할 수 없습니다.") from None
        if not start <= day <= end:
            continue
        raw_price = str(row.get("price", "")).replace(",", "").strip()
        if raw_price in ("-", "", "None", "null"):
            quality["missing_rows"] += 1
            continue
        try:
            price = Decimal(raw_price)
        except InvalidOperation:
            raise SchemaError("가격 형식을 확인할 수 없습니다.") from None
        if not price.is_finite() or price <= 0 or price > 1_000_000_000:
            raise SchemaError("유효 가격 범위를 벗어났습니다.")
        # No conversion from heads/boxes, and no inferred weight.
        unit = str(row.get("unit", "")).strip().lower().replace(" ", "")
        if unit not in ("1kg", "kg", "1㎏", "㎏"):
            raise SchemaError("응답의 kg 단위가 확인되지 않아 분석을 중단했습니다.")
        identity = tuple(str(row.get(k, "")).strip() for k in ("itemname", "kindname", "countyname", "marketname"))
        if not all(identity[:3]) or identity[0] != "배추":
            raise SchemaError("배추·품종·지역의 응답 식별자를 확인할 수 없습니다.")
        key = day.isoformat()
        if key in groups[identity]:
            if groups[identity][key] != float(price):
                raise SchemaError("같은 조사일·시장에 상충하는 가격이 있습니다.")
            quality["duplicate_rows"] += 1
        groups[identity][key] = float(price)
    series = []
    for identity, days in sorted(groups.items()):
        prices = [{"date": day, "price_per_kg": price} for day, price in sorted(days.items())]
        series.append({"item": identity[0], "variety": identity[1], "region": identity[2],
                       "market": identity[3] or "지역 조사 평균", "prices": prices, "analysis": stats(prices)})
    return series, quality


class KamisClient:
    def __init__(self):
        self.cache = {}

    async def prices(self, start, end, region, kind, rank):
        meta = {"source": "unavailable", "status": "not_configured", "unit": "원/kg",
                "requested_unit": "kg", "source_name": "KAMIS 중도매인 판매가격", "documentation": DOCUMENTATION,
                "retrieved_at": None, "as_of": None, "series": [], "quality": None,
                "query": {"start": str(start), "end": str(end), "item_code": "211", "region_code": region,
                          "kind_code": kind, "rank_code": rank, "price_class": "02"},
                "message": "KAMIS 서버 인증이 설정되지 않았습니다. 실제 가격을 불러오지 않았습니다."}
        if not configured():
            return meta
        key = (start, end, region, kind, rank)
        if key in self.cache and time.monotonic() - self.cache[key][0] < 300:
            return {**self.cache[key][1], "cached": True}
        params = {"action": "periodProductList", "p_cert_id": os.environ["KAMIS_CERT_ID"].strip(),
                  "p_cert_key": os.environ["KAMIS_CERT_KEY"].strip(), "p_returntype": "json",
                  "p_startday": start.isoformat(), "p_endday": end.isoformat(), "p_productclscode": "02",
                  "p_itemcategorycode": "200", "p_itemcode": "211", "p_kindcode": kind,
                  "p_productrankcode": rank, "p_countrycode": region, "p_convert_kg_yn": "Y"}
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
                # Fixed HTTPS endpoint; no browser keys, user URLs, redirects or raw payload logs.
                response = await client.get(ENDPOINT, params=params)
                response.raise_for_status()
                series, quality = normalize(response.json(), start, end)
        except SchemaError as error:
            return {**meta, "status": "upstream_error", "error_kind": error.kind,
                    "message": f"{error} 실제 가격을 표시하지 않았습니다."}
        except httpx.HTTPError:
            return {**meta, "status": "upstream_error", "error_kind": "connection",
                    "message": "KAMIS 서버 연결에 실패했습니다. 잠시 후 다시 조회하세요. 실제 가격을 표시하지 않았습니다."}
        except ValueError:
            return {**meta, "status": "upstream_error", "error_kind": "format",
                    "message": "KAMIS 응답의 JSON 형식을 확인할 수 없습니다. 실제 가격을 표시하지 않았습니다."}
        result = {**meta, "source": "kamis", "status": "live" if series else "empty", "series": series,
                  "quality": quality, "retrieved_at": datetime.now(KST).isoformat(),
                  "as_of": max((s["analysis"]["latest_date"] for s in series), default=None),
                  "cached": False, "message": "실제 KAMIS API 조회 자료입니다." if series else "요청 조건에 유효한 조사 가격이 없습니다."}
        # Bound the in-memory cache. Auth changes are picked up on process restart.
        if len(self.cache) >= 100:
            self.cache.clear()
        self.cache[key] = (time.monotonic(), result)
        return result
