"""Тести об'єктної моделі: властивості, спеціальні методи, dataclass, підтипи, протокол."""

from __future__ import annotations

import ast
import dataclasses
from datetime import date

import pytest

from conftest import ROOT
from kzp_lab06.analysis import fault_summaries, final_cost_by_tier, total_final_cost
from kzp_lab06.models import (
    FaultSummary,
    PaidRepair,
    Priced,
    RepairOrder,
    ReportSummary,
    WarrantyRepair,
    create_order,
)

D = date(2026, 1, 5)


def paid(cost: float = 650.0, customer: str = "Іваненко, Петро") -> PaidRepair:
    return PaidRepair(customer, "Ноутбук", "Заміна термопасти", D, cost, "done")


def warranty(cost: float = 2750.0) -> WarrantyRepair:
    return WarrantyRepair("Бондар Марія", "Пральна машина", "Гарантія: підшипник", D, cost, "new")


# --- setter-и ---
@pytest.mark.parametrize("value", [650, 0, 0.01, 1e9])
def test_cost_setter_accepts_valid(value):
    order = paid()
    order.cost = value
    assert order.cost == float(value)


@pytest.mark.parametrize(
    ("value", "error", "message"),
    [
        (-0.01, ValueError, "не може бути від'ємним"),
        (float("nan"), ValueError, "скінченним"),
        (float("inf"), ValueError, "скінченним"),
        ("100", TypeError, "має бути числом"),
        (True, TypeError, "має бути числом"),
        (None, TypeError, "має бути числом"),
    ],
)
def test_cost_setter_rejects_invalid_and_keeps_state(value, error, message):
    order = paid()
    with pytest.raises(error, match=message):
        order.cost = value
    assert order.cost == 650.0


@pytest.mark.parametrize("value", ["NEW", " in_progress ", "Done"])
def test_status_setter_normalizes(value):
    order = paid()
    order.status = value
    assert order.status == value.strip().casefold()


@pytest.mark.parametrize("value", ["closed", "", "  "])
def test_status_setter_rejects_unknown(value):
    order = paid()
    with pytest.raises(ValueError):
        order.status = value
    assert order.status == "done"


def test_text_setters_normalize_and_reject_empty():
    order = paid()
    order.customer = "  Коваль   Оксана "
    assert order.customer == "Коваль Оксана"
    with pytest.raises(ValueError, match="немає значення поля customer"):
        order.customer = "   "
    with pytest.raises(TypeError):
        order.device = 5
    assert order.customer == "Коваль Оксана"


def test_date_is_read_only():
    order = paid()
    with pytest.raises(AttributeError):
        order.date = D  # type: ignore[misc]
    with pytest.raises(TypeError):
        PaidRepair("К", "П", "Н", "2026-01-05", 1, "new")  # type: ignore[arg-type]


def test_slots_prevent_new_attributes():
    with pytest.raises(AttributeError):
        paid().colour = "red"  # type: ignore[attr-defined]


# --- спеціальні методи ---
def test_str_and_repr():
    order = paid()
    assert (
        str(order)
        == "2026-01-05 | Іваненко, Петро | Ноутбук | Заміна термопасти | 650.00 грн | виконана"
    )
    assert repr(order) == (
        "PaidRepair(customer='Іваненко, Петро', device='Ноутбук', fault='Заміна термопасти', "
        "date=datetime.date(2026, 1, 5), cost=650.0, status='done')"
    )


def test_equality():
    assert paid() == paid()
    assert paid() != paid(cost=1)
    same_fields = WarrantyRepair(
        "Іваненко, Петро", "Ноутбук", "Заміна термопасти", D, 650.0, "done"
    )
    assert paid() != same_fields
    assert paid().__eq__("рядок") is NotImplemented
    assert paid() != "рядок"


def test_mutable_order_is_unhashable():
    with pytest.raises(TypeError):
        hash(paid())


def test_sort_key_orders_by_date_then_customer():
    later = PaidRepair("Андрієнко Ірина", "П", "Н", date(2026, 1, 6), 1, "new")
    same_day = PaidRepair("Іваненко, Петро", "П", "Н", D, 1, "new")
    first = PaidRepair("Андрієнко Ірина", "П", "Н", D, 1, "new")
    items = [later, same_day, first]
    assert sorted(items, key=lambda o: o.sort_key) == [first, same_day, later]


# --- dataclass ---
def test_fault_summary_dataclass():
    s = FaultSummary("Заміна екрана", 2, 6400.0, 6080.0)
    assert s == FaultSummary("Заміна екрана", 2, 6400.0, 6080.0)
    assert hash(s) == hash(FaultSummary("Заміна екрана", 2, 6400.0, 6080.0))
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.count = 3  # type: ignore[misc]


def test_report_summary_is_frozen():
    summary = ReportSummary(0, (), 0.0, (), (), None, 0.0)
    assert "ReportSummary(count=0" in repr(summary)
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.count = 1  # type: ignore[misc]


# --- підтипи ---
def test_final_cost_discounts_differ():
    assert warranty(3200).final_cost() == 0.0  # гарантія: знижка 100 %
    assert paid(3200).final_cost() == 3040.0  # платний: знижка 5 % від 3000 грн
    assert paid(650).final_cost() == 650.0


def test_paid_discount_boundary():
    assert paid(2999.99).final_cost() == 2999.99
    assert paid(3000).final_cost() == 2850.0
    assert paid(0).final_cost() == 0.0


def test_final_cost_rounding_half_up():
    assert paid(3000.01).final_cost() == 2850.01  # 2850.0095 → 2850.01


def test_base_class_final_cost_is_abstract():
    with pytest.raises(NotImplementedError):
        RepairOrder("К", "П", "Н", D, 1, "new").final_cost()


def test_tiers():
    assert paid().tier == "Платний"
    assert warranty().tier == "Гарантійний"


@pytest.mark.parametrize(
    ("fault", "kind"),
    [
        ("Заміна екрана", PaidRepair),
        ("Гарантія: заміна екрана", WarrantyRepair),
        ("  ГАРАНТІЯ: підшипник", WarrantyRepair),
        ("Діагностика (без гарантії)", PaidRepair),
    ],
)
def test_factory_chooses_subtype(fault, kind):
    assert type(create_order("К", "П", fault, D, 1, "new")) is kind


# --- протокол і duck typing ---
class GiftCertificate:
    """Не наслідує RepairOrder, але виконує контракт Priced."""

    def __init__(self, amount: float) -> None:
        self.amount = amount

    @property
    def fault(self) -> str:
        return "Сертифікат"

    @property
    def cost(self) -> float:
        return self.amount

    @property
    def tier(self) -> str:
        return "Сертифікати"

    def final_cost(self) -> float:
        return self.amount


def test_protocol_and_duck_typing():
    items: list[Priced] = [paid(3200), warranty(2750), GiftCertificate(500)]
    assert isinstance(GiftCertificate(1), Priced)
    assert not isinstance("рядок", Priced)
    assert total_final_cost(items) == 3540.0
    assert final_cost_by_tier(items) == {
        "Гарантійний": 0.0,
        "Платний": 3040.0,
        "Сертифікати": 500.0,
    }
    faults = fault_summaries(items)
    assert [f.fault for f in faults] == ["Гарантія: підшипник", "Заміна термопасти", "Сертифікат"]
    assert faults[1] == FaultSummary("Заміна термопасти", 1, 3200.0, 3040.0)


def test_analysis_has_no_subtype_checks():
    source = (ROOT / "src" / "kzp_lab06" / "analysis.py").read_text(encoding="utf-8")
    names = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    assert "isinstance" not in names
    assert "WarrantyRepair" not in source and "PaidRepair" not in source


def test_models_module_reads_no_files():
    source = (ROOT / "src" / "kzp_lab06" / "models.py").read_text(encoding="utf-8")
    calls = {
        node.func.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "open" not in calls
    assert "import csv" not in source and "pathlib" not in source
