"""Deterministic grid search, no ML or probabilistic risk claim."""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from itertools import product

from ..schemas import Scenario

D = Decimal
CENT = D("0.01")


class Infeasible(ValueError):
    pass


def money(value: Decimal) -> float:
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def evaluate(s: Scenario, percentages=None, *, stress=False):
    percentages = percentages if percentages is not None else s.allocation_pct
    if len(percentages) != len(s.markets) or sum(percentages) != 100:
        raise Infeasible("배분비율의 합은 100%여야 합니다.")
    price_factor = 1 - s.price_drop_pct / 100 if stress else D(1)
    transport_factor = 1 + s.transport_increase_pct / 100 if stress else D(1)
    rows, gross_total, cost_total, transport_total = [], D(0), D(0), D(0)
    for m, pct in zip(s.markets, percentages):
        quantity = D(s.quantity_kg) * pct / 100
        if quantity > 0 and (quantity < m.min_kg or quantity > m.max_kg):
            raise Infeasible(f"{m.name}: 최소 출하량·시장 수용량 조건을 만족하지 않습니다.")
        vehicles = int((quantity / m.vehicle_capacity_kg).to_integral_value(rounding=ROUND_CEILING))
        gross = quantity * s.marketable_pct / 100 * m.price_per_kg * price_factor
        commission = gross * m.commission_pct / 100
        handling = gross * m.handling_pct / 100 + quantity * m.handling_per_kg
        market_fee = gross * m.market_fee_pct / 100
        transport = (vehicles * m.vehicle_cost + quantity * m.transport_per_kg) * transport_factor
        costs = commission + handling + market_fee + transport
        rows.append({"id": m.id, "name": m.name, "allocation_pct": float(pct),
                     "quantity_kg": float(quantity), "marketable_kg": float(quantity * s.marketable_pct / 100),
                     "vehicles": vehicles, "gross": money(gross), "commission": money(commission),
                     "handling": money(handling), "market_fee": money(market_fee),
                     "transport": money(transport), "cost": money(costs), "net": money(gross - costs)})
        gross_total += gross
        cost_total += costs
        transport_total += transport
    other = s.other_cost if s.quantity_kg else D(0)
    net = gross_total - cost_total - other
    return {"allocation_pct": [float(p) for p in percentages], "routes": rows,
            "gross": money(gross_total), "cost": money(cost_total + other),
            "transport": money(transport_total), "other_cost": money(other), "net": money(net),
            "quantity_kg": s.quantity_kg, "source": s.source,
            "price_source": "가상 경매가격" if s.source == "synthetic" else "사용자 입력 경매가격",
            "stress": stress, "_exact_net": net}


def public_result(result):
    return {k: v for k, v in result.items() if not k.startswith("_")}


def compare(s: Scenario):
    # Include current and every single-market allocation even if outside the chosen grid.
    current = evaluate(s)
    n = len(s.markets)
    candidates = [tuple(s.allocation_pct)]
    candidates.extend(tuple(D(100 if j == i else 0) for j in range(n)) for i in range(n))
    step = s.grid_step_pct
    for prefix in product(range(0, 101, step), repeat=n-1):
        remainder = 100 - sum(prefix)
        if remainder >= 0:
            candidates.append(tuple(D(p) for p in (*prefix, remainder)))
    results, seen, rejected = [], set(), 0
    for pct in candidates:
        if pct in seen:
            continue
        seen.add(pct)
        try:
            base = evaluate(s, pct)
            stressed = evaluate(s, pct, stress=True)
        except Infeasible:
            rejected += 1
            continue
        base["stressed_net"] = stressed["net"]
        base["_exact_stressed"] = stressed["_exact_net"]
        base["delta_vs_current"] = money(base["_exact_net"] - current["_exact_net"])
        base["label"] = " + ".join(f"{m.name} {p:g}%" for m, p in zip(s.markets, pct) if p)
        if not s.quantity_kg:
            base["label"] = "출하 물량 없음"
        results.append(base)
    ordered = sorted(results, key=lambda r: (-r["_exact_net"], r["transport"], r["allocation_pct"]))
    best = ordered[0]
    conservative = max(results, key=lambda r: (r["_exact_stressed"], r["_exact_net"]))
    cheapest = min(results, key=lambda r: (r["transport"], -r["_exact_net"]))
    return {"current": public_result(current), "current_stressed": public_result(evaluate(s, stress=True)),
            "strategies": [public_result(r) for r in ordered], "best": public_result(best),
            "conservative": public_result(conservative), "lowest_transport": public_result(cheapest),
            "search": {"method": "배분비율 격자 탐색", "step_pct": step,
                       "valid_count": len(results), "rejected_count": rejected,
                       "scope": "격자·현재 배분·단일시장 후보 중 비교. 연속공간 전역 최적 보장 없음."},
            "assumptions": ["경매 단가는 합성 또는 사용자 입력이며 예측 모델은 실행하지 않았습니다.",
                            "상품화율은 매출에, 물량당 처리비와 운송비는 전체 출하량에 적용합니다.",
                            "시장이 사용될 때 차량 용량에 따른 차량비를 각각 차감합니다.",
                            "스트레스 결과는 모든 시장 가격 하락과 운송비 상승을 함께 적용한 가정입니다.",
                            "생산비·세금·손실 비용이 모두 포함된 실제 순이익이 아닙니다."]}
