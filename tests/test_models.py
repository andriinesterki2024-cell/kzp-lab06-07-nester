"""Тести об'єктної моделі: властивості, спеціальні методи, dataclass, підтипи, протокол."""

from __future__ import annotations

import ast
import dataclasses
from datetime import date
from pathlib import Path

import pytest

from conftest import ROOT
from kzp_lab06.analysis import most_expensive, revenue_by_tier, total_revenue
from kzp_lab06.models import (
    ApplianceRepair,
    GadgetRepair,
    Priced,
    Repair,
    ReportSummary,
    Workload,
    create_repair,
)

D1, D4 = date(2026, 1, 1), date(2026, 1, 4)


def gadget(price: float = 650.0, ticket: int = 1) -> GadgetRepair:
    return GadgetRepair(ticket, "Іваненко, Петро", "Ноутбук", D1, D4, price)


def appliance(price: float = 1000.0) -> ApplianceRepair:
    return ApplianceRepair(4, "Шевчук Андрій", "Холодильник", D1, D4, price)


# --- setter-и ---
@pytest.mark.parametrize("value", [650, 0, 0.01, 1e9])
def test_price_setter_accepts_valid(value):
    repair = gadget()
    repair.price = value
    assert repair.price == float(value)


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
def test_price_setter_rejects_invalid_and_keeps_state(value, error, message):
    repair = gadget()
    with pytest.raises(error, match=message):
        repair.price = value
    assert repair.price == 650.0


@pytest.mark.parametrize(
    ("value", "error"), [(0, ValueError), (-1, ValueError), (1.0, TypeError), (True, TypeError)]
)
def test_ticket_setter(value, error):
    repair = gadget()
    with pytest.raises(error):
        repair.ticket = value
    assert repair.ticket == 1


def test_text_setters_normalize_and_reject_empty():
    repair = gadget()
    repair.client = "  Коваль   Оксана "
    assert repair.client == "Коваль Оксана"
    with pytest.raises(ValueError, match="немає значення поля client"):
        repair.client = "   "
    with pytest.raises(TypeError):
        repair.device = 5
    assert repair.client == "Коваль Оксана"


def test_dates_are_read_only_and_ordered():
    repair = gadget()
    with pytest.raises(AttributeError):
        repair.received = D4  # type: ignore[misc]
    with pytest.raises(AttributeError):
        repair.days = 5  # type: ignore[misc]
    with pytest.raises(ValueError, match="completed має бути пізніше за received"):
        GadgetRepair(1, "К", "П", D4, D1, 1)
    with pytest.raises(TypeError):
        GadgetRepair(1, "К", "П", "2026-01-01", D4, 1)  # type: ignore[arg-type]


def test_slots_prevent_new_attributes():
    with pytest.raises(AttributeError):
        gadget().colour = "red"  # type: ignore[attr-defined]


# --- спеціальні методи ---
def test_str_and_repr():
    repair = gadget()
    assert str(repair) == "1 | Іваненко, Петро | Ноутбук | 2026-01-01..2026-01-04"
    assert repr(repair) == (
        "GadgetRepair(ticket=1, client='Іваненко, Петро', device='Ноутбук', "
        "received=datetime.date(2026, 1, 1), completed=datetime.date(2026, 1, 4), price=650.0)"
    )


def test_equality():
    assert gadget() == gadget()
    assert gadget() != gadget(price=1)
    # однакові поля, але різні класи — не рівні
    same_fields = ApplianceRepair(1, "Іваненко, Петро", "Ноутбук", D1, D4, 650.0)
    assert gadget() != same_fields
    assert gadget().__eq__("рядок") is NotImplemented
    assert gadget() != "рядок"


def test_mutable_repair_is_unhashable():
    with pytest.raises(TypeError):
        hash(gadget())


def test_sort_key():
    items = [gadget(ticket=3), gadget(ticket=1), gadget(ticket=2)]
    assert [r.ticket for r in sorted(items, key=lambda r: r.sort_key)] == [1, 2, 3]


# --- dataclass ---
def test_workload_dataclass():
    load = Workload(in_work=4, total=7)
    assert load == Workload(4, 7)
    assert round(load.percent, 2) == 57.14
    assert Workload(0, 0).percent == 0.0
    assert hash(load) == hash(Workload(4, 7))
    with pytest.raises(dataclasses.FrozenInstanceError):
        load.total = 8  # type: ignore[misc]


def test_report_summary_is_frozen():
    summary = ReportSummary(D1, 0, (), Workload(0, 0), (), (), None, 0, 0.0)
    assert "ReportSummary(reference_date=datetime.date(2026, 1, 1)" in repr(summary)
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.count = 1  # type: ignore[misc]


# --- підтипи ---
def test_total_price_formulas_differ():
    assert gadget(1000).total_price() == 1050.0  # 1000 × 1.05
    assert appliance(1000).total_price() == 1260.0  # 1000 + 200 + 20 × 3 дні
    assert gadget(0).total_price() == 0.0
    assert appliance(0).total_price() == 260.0


def test_total_price_rounding_half_up():
    assert gadget(0.1).total_price() == 0.11  # 0.105 → 0.11
    assert gadget(999.99).total_price() == 1049.99  # 1049.9895 → 1049.99


def test_base_class_total_price_is_abstract():
    with pytest.raises(NotImplementedError):
        Repair(1, "К", "П", D1, D4, 1).total_price()


def test_tiers():
    assert gadget().tier == "Гаджети"
    assert appliance().tier == "Побутова техніка"


@pytest.mark.parametrize(
    ("device", "kind"),
    [
        ("Ноутбук", GadgetRepair),
        ("Електросамокат", GadgetRepair),
        ("Пральна машина", ApplianceRepair),
        ("  ХОЛОДИЛЬНИК ", ApplianceRepair),
        ("Посудомийна   машина", ApplianceRepair),
    ],
)
def test_factory_chooses_subtype(device, kind):
    assert type(create_repair(1, "К", device, D1, D4, 1)) is kind


# --- протокол і duck typing ---
class GiftCertificate:
    """Не наслідує Repair, але виконує контракт Priced."""

    def __init__(self, amount: float) -> None:
        self.amount = amount

    @property
    def days(self) -> int:
        return 0

    @property
    def tier(self) -> str:
        return "Сертифікати"

    def total_price(self) -> float:
        return self.amount


def test_protocol_and_duck_typing():
    items: list[Priced] = [gadget(1000), appliance(1000), GiftCertificate(500)]
    assert isinstance(GiftCertificate(1), Priced)
    assert not isinstance("рядок", Priced)
    assert total_revenue(items) == 2810.0
    assert revenue_by_tier(items) == {
        "Гаджети": 1050.0,
        "Побутова техніка": 1260.0,
        "Сертифікати": 500.0,
    }
    assert most_expensive(items) is items[1]
    assert most_expensive([]) is None


def test_analysis_has_no_subtype_checks():
    source = (ROOT / "src" / "kzp_lab06" / "analysis.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "isinstance" not in names
    assert "GadgetRepair" not in source and "ApplianceRepair" not in source


def test_models_module_reads_no_files():
    source = Path(ROOT / "src" / "kzp_lab06" / "models.py").read_text(encoding="utf-8")
    assert "open(" not in source
