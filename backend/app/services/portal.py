"""data.go.kr perRegion adapter; bounded requests and no credential logging."""
import asyncio
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import re
import time
from urllib.parse import unquote

import httpx

from .kamis import KST, SchemaError, stats
from .settings import service_key

ENDPOINT = "https://apis.data.go.kr/B552845/perRegion/price"
DOCUMENTATION = "https://www.data.go.kr/data/15156062/openapi.do"
KINDS = {"01": "봄", "02": "여름(고랭지)", "03": "가을", "06": "월동"}
REGIONS = {"1101": "서울", "2100": "부산", "2200": "대구", "2401": "광주", "2501": "대전"}


def configured():
    return bool(service_key())


def positive(value):
    try:
        n = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise SchemaError("가격·중량의 숫자 형식이 다릅니다.") from None
    if not n.is_finite() or n <= 0 or n > 1_000_000_000:
        raise SchemaError("가격·중량이 유효 범위를 벗어났습니다.")
    return n


def weight_kg(unit, size):
    unit = str(unit).strip().lower().replace(" ", "").replace("㎏", "kg")
    size = str(size if size is not None else "").strip()
    # Observed KAMIS cabbage packaging label; the mass still comes from unit_sz.
    # Do not strip arbitrary parentheses: they could contain conflicting weights.
    if unit in ("kg", "kg(그물망3포기)"):
        return positive(size)
    if unit.endswith("(그물망3포기)"):
        unit = unit.removesuffix("(그물망3포기)")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)kg", unit)
    if match:
        weight = positive(match[1])
        if size and positive(size) != weight:
            raise SchemaError("단위와 단위크기의 중량이 일치하지 않습니다.")
        return weight
    return None  # Never infer the weight of heads, boxes or bunches.


def unpack(payload, page):
    if not isinstance(payload, dict):
        raise SchemaError("포털 응답 구조가 다릅니다.")
    data = payload.get("response", payload)
    if not isinstance(data, dict) or not isinstance(data.get("header"), dict):
        raise SchemaError("포털 결과 헤더를 확인할 수 없습니다.")
    code = str(data["header"].get("resultCode", ""))
    if code not in ("00", "000", "0"):
        kind = "authentication" if code in ("20", "30", "31") else "upstream"
        raise SchemaError("포털 이용 승인·인증키·요청 조건을 확인하세요.", kind)
    body = data.get("body")
    if not isinstance(body, dict):
        raise SchemaError("포털 응답 본문이 다릅니다.")
    try:
        total = int(str(body["totalCount"]))
        returned_page = int(str(body["pageNo"]))
    except (KeyError, TypeError, ValueError):
        raise SchemaError("페이지·전체 건수를 확인할 수 없습니다.") from None
    if total < 0 or total > 5000 or returned_page != page:
        raise SchemaError("조회량 한도 또는 페이지 순서가 맞지 않습니다. 기간을 줄여 조회하세요.")
    items = body.get("items")
    if total == 0 and items in (None, "", [], {}):
        return [], total
    if isinstance(items, dict):
        items = items.get("item")
        if isinstance(items, dict):
            items = [items]
    if isinstance(items, list):
        items = [x["item"] if isinstance(x, dict) and set(x) == {"item"} else x for x in items]
    if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
        raise SchemaError("포털 가격 목록을 확인할 수 없습니다.")
    return items, total


def normalize(rows, start, end, region, kind, rank):
    groups = defaultdict(dict)
    quality = dict(missing_rows=0, duplicate_rows=0, aggregate_rows=0,
                   unsupported_unit_rows=0, converted_rows=0, outside_rows=0,
                   unit_samples=[])
    for row in rows:
        expected = {"se_cd": "02", "ctgry_cd": "200", "item_cd": "211",
                    "vrty_cd": kind, "grd_cd": rank, "sgg_cd": region}
        if any(str(row.get(k, "")).strip() != v for k, v in expected.items()):
            raise SchemaError("요청한 구분·품목·품종·등급·지역과 응답 코드가 다릅니다.")
        if str(row.get("item_nm", "")).strip() != "배추" or not row.get("vrty_nm") or not row.get("sgg_nm"):
            raise SchemaError("응답 품목·품종·지역명을 확인할 수 없습니다.")
        try:
            raw_day = str(row["exmn_ymd"])
            day = datetime.strptime(raw_day, "%Y%m%d").date() if re.fullmatch(r"\d{8}", raw_day) else date.fromisoformat(raw_day)
        except (KeyError, ValueError, TypeError):
            raise SchemaError("조사일 형식을 확인할 수 없습니다.") from None
        if not start <= day <= end:
            quality["outside_rows"] += 1
            continue
        raw_price = row.get("exmn_dd_avg_prc")
        if str(raw_price).strip() in ("", "-", "None", "null"):
            quality["missing_rows"] += 1
            continue
        weight = weight_kg(row.get("unit", ""), row.get("unit_sz"))
        if weight is None:
            quality["unsupported_unit_rows"] += 1
            sample = {"unit": unit_label(row.get("unit")),
                      "unit_size": unit_label(row.get("unit_sz"))}
            if sample not in quality["unit_samples"] and len(quality["unit_samples"]) < 8:
                quality["unit_samples"].append(sample)
            continue
        original = positive(raw_price)
        price = original / weight
        if price > 1_000_000_000:
            raise SchemaError("환산 가격이 유효 범위를 벗어났습니다.")
        identity = (str(row["item_nm"]), str(row["vrty_nm"]), str(row["sgg_nm"]))
        point = {"date": day.isoformat(), "price_per_kg": float(price),
                 "original_price": float(original), "original_unit": str(row["unit"]),
                 "original_unit_size": str(row.get("unit_sz", "")), "weight_kg": float(weight),
                 "conversion_method": "조사단위 가격 ÷ 명시된 kg 중량"}
        old = groups[identity].get(point["date"])
        if old:
            if old != point:
                raise SchemaError("동일 조사일·지역·품종에 상충하는 조사값이 있습니다.")
            quality["duplicate_rows"] += 1
            continue
        groups[identity][point["date"]] = point
        quality["converted_rows"] += 1
    series = []
    for (item, variety, region_name), days in sorted(groups.items()):
        points = [days[d] for d in sorted(days)]
        series.append({"item": item, "variety": variety, "region": region_name,
                       "market": "지역 조사 평균 · 개별 경매시장 아님", "prices": points, "analysis": stats(points)})
    return series, quality


def unit_label(value):
    """Expose only short unit descriptions, never raw upstream records or keys."""
    if value is None or value == "":
        return "(없음)"
    if not isinstance(value, (str, int, float)):
        return "(단위 형식 확인 필요)"
    text = str(value).strip()
    if not text:
        return "(없음)"
    if len(text) > 40 or not re.fullmatch(r"[가-힣A-Za-z0-9\s.()/㎏_+\-]+", text):
        return "(단위 표기 확인 필요)"
    return " ".join(text.split())


def empty_message(quality):
    if quality["unsupported_unit_rows"]:
        labels = "; ".join(f"단위={s['unit']} / 단위크기={s['unit_size']}" for s in quality["unit_samples"][:3])
        return f"가격 응답 중 {quality['unsupported_unit_rows']}건의 kg 중량을 확인하지 못했습니다. {labels}. 중량을 추정하지 않고 제외했습니다."
    return "유효한 kg 조사값이 없습니다. 결측·조회 기간을 확인하세요."


class PortalClient:
    def __init__(self):
        self.cache = {}

    async def prices(self, start, end, region, kind, rank):
        meta = {"source": "unavailable", "status": "not_configured", "unit": "원/kg",
                "source_name": "KAMIS 지역별 중도매인 판매가격 · 공공데이터포털",
                "documentation": DOCUMENTATION, "adapter": "perRegion/price",
                "retrieved_at": None, "as_of": None, "series": [], "quality": None,
                "query": {"start": str(start), "end": str(end), "item_code": "211", "region_code": region,
                          "kind_code": kind, "rank_code": rank, "price_class": "02"},
                "message": "공공데이터포털 서버 인증이 설정되지 않았습니다. 실제 가격을 불러오지 않았습니다."}
        if region not in REGIONS or kind not in KINDS or rank not in ("04", "05"):
            return {**meta, "status": "upstream_error", "error_kind": "parameters", "message": "지원하는 중도매 지역·배추 품종·등급 코드를 확인하세요."}
        credential = service_key()
        if not credential:
            return meta
        secret = unquote(credential)
        cache_key = (sha256(secret.encode()).digest(), start, end, region, kind, rank)
        if cache_key in self.cache and time.monotonic() - self.cache[cache_key][0] < 300:
            return {**self.cache[cache_key][1], "cached": True}
        params = {"serviceKey": secret, "returnType": "JSON", "numOfRows": 1000,
                  "cond[exmn_ymd::GTE]": start.strftime("%Y%m%d"), "cond[exmn_ymd::LTE]": end.strftime("%Y%m%d"),
                  "cond[se_cd::EQ]": "02", "cond[ctgry_cd::EQ]": "200", "cond[item_cd::EQ]": "211",
                  "cond[vrty_cd::EQ]": kind, "cond[grd_cd::EQ]": rank, "cond[sgg_cd::EQ]": region}
        try:
            async with asyncio.timeout(25), httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
                rows, total = [], None
                for page in range(1, 6):
                    response = await client.get(ENDPOINT, params={**params, "pageNo": page})
                    response.raise_for_status()
                    batch, count = unpack(response.json(), page)
                    if total is not None and count != total:
                        raise SchemaError("페이지 조회 중 전체 건수가 변경됐습니다. 다시 조회하세요.")
                    total = count
                    rows.extend(batch)
                    if len(rows) == total:
                        break
                    if not batch or len(rows) > total:
                        raise SchemaError("페이지 누락 또는 전체 건수 불일치로 조회를 중단했습니다.")
                if len(rows) != total:
                    raise SchemaError("전체 자료를 받지 못해 분석을 중단했습니다.")
                series, quality = normalize(rows, start, end, region, kind, rank)
                quality["received_rows"] = len(rows)
        except SchemaError as error:
            return {**meta, "status": "upstream_error", "error_kind": error.kind, "message": str(error)}
        except (httpx.HTTPError, TimeoutError):
            return {**meta, "status": "upstream_error", "error_kind": "connection", "message": "공공데이터포털 연결·응답 시간을 확인하세요. 실제 가격을 표시하지 않았습니다."}
        except (ValueError, TypeError):
            return {**meta, "status": "upstream_error", "error_kind": "format", "message": "포털 응답 형식을 확인할 수 없습니다. 실제 가격을 표시하지 않았습니다."}
        result = {**meta, "source": "kamis", "status": "live" if series else "empty", "series": series,
                  "quality": quality, "retrieved_at": datetime.now(KST).isoformat(), "cached": False,
                  "as_of": max((s["analysis"]["latest_date"] for s in series), default=None),
                  "message": "실제 포털 조회 자료입니다. 조사 중량으로 kg 환산했습니다." if series else empty_message(quality)}
        if len(self.cache) >= 100:
            self.cache.clear()
        self.cache[cache_key] = (time.monotonic(), result)
        return result
