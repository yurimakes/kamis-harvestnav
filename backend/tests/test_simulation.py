from decimal import Decimal as D
from pathlib import Path
import json
import random

import pytest
from pydantic import ValidationError

from backend.app.schemas import Scenario
from backend.app.services.simulation import Infeasible, compare, evaluate


@pytest.fixture
def sample():
    return json.loads((Path(__file__).parents[2] / "examples" / "cabbage.synthetic.json").read_text(encoding="utf-8"))


def scenario(sample):
    return Scenario.model_validate(sample)


def test_reference_receipt_hand_calculation(sample):
    # 3000*.95*1500 + 2000*.95*1600 = 7,315,000.
    # 7.5% revenue charges = 548,625. Trucks 440,000 + variable 54,000.
    r = evaluate(scenario(sample))
    assert r["gross"] == 7_315_000
    assert r["transport"] == 494_000
    assert r["cost"] == 1_042_625
    assert r["net"] == 6_272_375


def test_grid_result_and_difference(sample):
    r = compare(scenario(sample))
    assert r["best"]["allocation_pct"] == [0, 100]
    assert r["best"]["net"] == 6_710_000
    assert r["best"]["delta_vs_current"] == 437_625
    assert r["search"]["valid_count"] == 21


def test_unused_market_no_fixed_vehicle_cost(sample):
    sample["allocation_pct"] = [100, 0]
    r = evaluate(scenario(sample))
    assert r["routes"][1]["vehicles"] == r["routes"][1]["transport"] == 0
    assert r["transport"] == 230_000


def test_vehicle_capacity_step(sample):
    sample["allocation_pct"] = [100, 0]
    sample["quantity_kg"] = 5001
    r = evaluate(scenario(sample))
    assert r["routes"][0]["vehicles"] == 2
    assert r["transport"] == 410_010


def test_equal_prices_split_is_worse_due_to_additional_vehicle(sample):
    sample["markets"][1]["price_per_kg"] = 1500
    r = compare(scenario(sample))
    assert r["best"]["allocation_pct"] == [100, 0]
    assert r["best"]["net"] > r["current"]["net"]


def test_capacity_excludes_single_market_and_finds_valid_split(sample):
    for m in sample["markets"]:
        m["max_kg"] = 3500
    r = compare(scenario(sample))
    assert not any(100 in x["allocation_pct"] for x in r["strategies"])
    assert r["best"]["allocation_pct"] == [30, 70]
    assert r["search"]["rejected_count"] > 0


def test_minimum_only_for_used_markets(sample):
    sample["markets"][1]["min_kg"] = 2500
    with pytest.raises(Infeasible):
        evaluate(scenario(sample))
    sample["allocation_pct"] = [100, 0]
    evaluate(scenario(sample))


def test_zero_quantity_zero_charges(sample):
    sample["quantity_kg"] = 0
    sample["other_cost"] = 50000
    r = compare(scenario(sample))
    assert r["current"]["net"] == 0
    assert r["current"]["cost"] == 0
    assert all(x["vehicles"] == 0 for x in r["current"]["routes"])


def test_price_stress_and_transport_increase(sample):
    r = compare(scenario(sample))
    # 7,315,000*.9*.925 - 494,000*1.1 = 5,546,337.5
    assert r["current_stressed"]["net"] == 5_546_337.5
    assert r["current_stressed"]["net"] < r["current"]["net"]


def test_handling_on_shipped_quantity_and_other_once(sample):
    sample["markets"][0]["handling_per_kg"] = 5
    sample["other_cost"] = 40000
    r = evaluate(scenario(sample))
    assert r["net"] == 6_272_375 - 15000 - 40000


def test_negative_net_is_retained(sample):
    for m in sample["markets"]:
        m["price_per_kg"] = 0
    assert compare(scenario(sample))["current"]["net"] == -494000


def test_non_grid_current_is_included(sample):
    sample["allocation_pct"] = [33, 67]
    r = compare(scenario(sample))
    assert any(x["allocation_pct"] == [33, 67] for x in r["strategies"])
    assert r["search"]["valid_count"] == 22


def test_third_market_and_total_preservation(sample):
    sample["markets"].append({**sample["markets"][0], "id": "third", "name": "가상 C"})
    sample["allocation_pct"] = [30, 30, 40]
    r = compare(scenario(sample))
    assert r["search"]["valid_count"] == 231
    for x in r["strategies"]:
        assert sum(p["quantity_kg"] for p in x["routes"]) == sample["quantity_kg"]


def test_seeded_quantity_invariants(sample):
    rng = random.Random(17)
    for _ in range(70):
        sample["quantity_kg"] = rng.randint(0, 100000)
        pct = rng.randint(0, 100)
        sample["allocation_pct"] = [pct, 100-pct]
        r = evaluate(scenario(sample))
        assert sum(D(str(p["quantity_kg"])) for p in r["routes"]) == sample["quantity_kg"]
        assert abs(r["gross"] - r["cost"] - r["net"]) <= .011


@pytest.mark.parametrize("key,value", [("quantity_kg", -1), ("quantity_kg", 100001), ("quantity_kg", 1.5),
    ("marketable_pct", 101), ("marketable_pct", float("nan")), ("other_cost", -1),
    ("allocation_pct", [50, 40]), ("allocation_pct", [100]), ("allocation_pct", [110, -10])])
def test_invalid_scenario_is_rejected(sample, key, value):
    sample[key] = value
    with pytest.raises(ValidationError):
        scenario(sample)


def test_fee_sum_and_duplicate_market_rejected(sample):
    sample["markets"][0]["commission_pct"] = 99
    with pytest.raises(ValidationError):
        scenario(sample)
    sample["markets"][0]["commission_pct"] = 6
    sample["markets"][1]["id"] = sample["markets"][0]["id"]
    with pytest.raises(ValidationError):
        scenario(sample)
