"""All calculation inputs are explicit; prices are KRW per kg, quantities kg."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Nonnegative = Annotated[Decimal, Field(ge=0, le=1_000_000_000, allow_inf_nan=False)]
Percent = Annotated[Decimal, Field(ge=0, le=100, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Market(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,29}$")
    name: str = Field(min_length=1, max_length=40)
    price_per_kg: Nonnegative
    commission_pct: Percent = Decimal("6")
    handling_pct: Percent = Decimal("1")
    market_fee_pct: Percent = Decimal("0.5")
    handling_per_kg: Nonnegative = Decimal("0")
    vehicle_cost: Nonnegative = Decimal("180000")
    vehicle_capacity_kg: int = Field(default=5000, ge=1, le=100000)
    transport_per_kg: Nonnegative = Decimal("10")
    min_kg: int = Field(default=0, ge=0, le=100000)
    max_kg: int = Field(default=100000, ge=0, le=100000)

    @model_validator(mode="after")
    def consistent(self):
        if self.min_kg > self.max_kg:
            raise ValueError("최소 출하량이 시장 수용량보다 큽니다.")
        if self.commission_pct + self.handling_pct + self.market_fee_pct > 100:
            raise ValueError("매출에 적용되는 비용률 합은 100% 이하여야 합니다.")
        return self


class Scenario(StrictModel):
    commodity: Literal["배추"] = "배추"
    origin: str = Field(default="강원 평창 · 가상 산지", min_length=1, max_length=60)
    planned_date: date | None = None
    source: Literal["synthetic", "user_input"] = "synthetic"
    quantity_kg: int = Field(default=5000, ge=0, le=100000)
    marketable_pct: Percent = Decimal("95")
    other_cost: Nonnegative = Decimal("0")
    markets: list[Market] = Field(min_length=2, max_length=3)
    allocation_pct: list[Percent]
    grid_step_pct: Literal[5, 10, 20, 25, 50] = 5
    price_drop_pct: Percent = Decimal("10")
    transport_increase_pct: Percent = Decimal("10")

    @model_validator(mode="after")
    def allocation(self):
        if len(set(m.id for m in self.markets)) != len(self.markets):
            raise ValueError("시장 ID가 중복됩니다.")
        if len(self.allocation_pct) != len(self.markets) or sum(self.allocation_pct) != 100:
            raise ValueError("시장별 배분비율의 합은 정확히 100%여야 합니다.")
        return self
