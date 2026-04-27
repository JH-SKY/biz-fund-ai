from __future__ import annotations

from typing import Any


class NormalizedTargetLogic:
    """Normalized view of policy target_logic JSON."""

    def __init__(self) -> None:
        self.sectors: list[str] | None = None
        self.min_revenue: int | None = None
        self.max_revenue: int | None = None
        self.max_debt_ratio: float | None = None
        self.min_employees: int | None = None
        self.max_employees: int | None = None
        self.min_business_age_months: int | None = None
        self.region_restricted: bool = False
        self.allowed_regions: list[str] = []
        self.require_patent: bool | None = None
        self.require_ventured: bool | None = None


def parse_target_logic(raw: Any) -> NormalizedTargetLogic | None:
    """Parse free-form target_logic JSON into a predictable object."""

    if not isinstance(raw, dict):
        return None

    logic = NormalizedTargetLogic()
    logic.sectors = _parse_str_list(raw.get("sectors"))
    logic.min_revenue = _parse_amount(raw.get("min_revenue"))
    logic.max_revenue = _parse_amount(raw.get("max_revenue"))
    logic.max_debt_ratio = _parse_ratio(raw.get("max_debt_ratio"))
    logic.min_employees = _parse_int_safe(raw.get("min_employees"))
    logic.max_employees = _parse_int_safe(raw.get("max_employees"))

    min_age_raw = raw.get("min_business_age_months") or raw.get("min_business_age_years")
    if raw.get("min_business_age_years") is not None:
        years = _parse_int_safe(raw.get("min_business_age_years"))
        logic.min_business_age_months = years * 12 if years is not None else None
    else:
        logic.min_business_age_months = _parse_int_safe(min_age_raw)

    logic.region_restricted = _parse_bool_safe(raw.get("region_restricted")) or False
    region_list = raw.get("allowed_regions") or raw.get("regions") or []
    logic.allowed_regions = _parse_str_list(region_list) or []
    logic.require_patent = _parse_bool_safe(raw.get("require_patent"))
    logic.require_ventured = _parse_bool_safe(raw.get("require_ventured"))
    return logic


_AMOUNT_UNITS = {
    "억원": 100_000_000,
    "천만원": 10_000_000,
    "백만원": 1_000_000,
    "만원": 10_000,
}


def _parse_amount(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        cleaned = (
            val.replace(",", "")
            .replace(" ", "")
            .replace("원", "")
            .replace("약", "")
        )
        for unit, multiplier in _AMOUNT_UNITS.items():
            if unit in cleaned:
                number = cleaned.replace(unit, "").strip()
                try:
                    return int(float(number) * multiplier)
                except (TypeError, ValueError):
                    return None
        try:
            return int(float(cleaned))
        except (TypeError, ValueError):
            return None
    return None


def _parse_ratio(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace("%", "").strip())
        except (TypeError, ValueError):
            return None
    return None


def _parse_int_safe(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _parse_bool_safe(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return bool(val)
    if isinstance(val, str):
        return val.lower() in {"true", "yes", "1", "y"}
    return None


def _parse_str_list(val: Any) -> list[str] | None:
    if val is None:
        return None
    if isinstance(val, list):
        return [str(item).strip() for item in val if str(item).strip()]
    if isinstance(val, str):
        if "," in val:
            return [item.strip() for item in val.split(",") if item.strip()]
        return [val.strip()] if val.strip() else None
    return None
