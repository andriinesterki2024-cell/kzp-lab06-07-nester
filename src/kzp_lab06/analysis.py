"""Обчислення над об'єктами заявок (варіант 16).

Функції працюють через властивості й спільний метод ``final_cost()``; перевірок конкретного
підтипу та назв підтипів у модулі немає. Модуль не відкриває файлів і не форматує текст.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import islice
from typing import Any

from kzp_lab06.models import STATUSES, FaultSummary, Priced, RepairOrder, ReportSummary, uk_key

__all__ = [
    "build_report",
    "cost_by_fault",
    "fault_summaries",
    "final_cost_by_tier",
    "make_summary",
    "most_expensive",
    "open_orders",
    "preview",
    "stream_summary",
    "total_final_cost",
    "uk_key",
    "unique_devices",
]


def open_orders(orders: list[RepairOrder]) -> list[RepairOrder]:
    """Відбір (list comprehension): відкриті заявки за ключем sort_key (дата, клієнт)."""
    selected = [order for order in orders if order.is_open]
    return sorted(selected, key=lambda order: order.sort_key)


def cost_by_fault(orders: list[RepairOrder]) -> dict[str, float]:
    """Словник «несправність → сума вартості» за українським алфавітом."""
    totals: dict[str, float] = {}
    for order in orders:
        totals[order.fault] = totals.get(order.fault, 0.0) + order.cost
    return {fault: totals[fault] for fault in sorted(totals, key=uk_key)}


def unique_devices(orders: list[RepairOrder]) -> set[str]:
    """Множина пристроїв без повторів (set comprehension)."""
    return {order.device for order in orders}


def most_expensive(orders: list[RepairOrder]) -> RepairOrder | None:
    """Найдорожчий ремонт; за рівної вартості — раніша дата."""
    if not orders:
        return None
    return min(orders, key=lambda order: (-order.cost, order.date))


def make_summary(
    orders: list[RepairOrder],
    *statuses: str,
    minimum_cost: float = 0.0,
    **labels: str,
) -> dict[str, Any]:
    """Підсумок вартості за станами заявок (як у ЛР6, але через атрибути)."""
    unknown = [name for name in statuses if name not in STATUSES]
    if unknown:
        raise ValueError(f"Невідомі стани: {', '.join(unknown)}")
    extra = [name for name in labels if name not in statuses]
    if extra:
        raise ValueError(f"Підписи для невибраних станів: {', '.join(extra)}")
    kept = [o for o in orders if o.status in statuses and o.cost >= minimum_cost]
    summary: dict[str, Any] = {"count": len(kept)}
    for status in statuses:
        summary[labels.get(status, status)] = sum(o.cost for o in kept if o.status == status)
    return summary


def build_report(orders: list[RepairOrder]) -> ReportSummary:
    """Збирає незмінний підсумок звіту (вхідний список не змінюється)."""
    opened = open_orders(orders)
    return ReportSummary(
        count=len(orders),
        open_orders=tuple(opened),
        open_cost=sum(order.cost for order in opened),
        cost_by_fault=tuple(cost_by_fault(orders).items()),
        devices=tuple(sorted(unique_devices(orders), key=uk_key)),
        most_expensive=most_expensive(orders),
        total_cost=sum(order.cost for order in orders),
    )


# --- функції протоколу Priced: лише спільний метод, без перевірки класу ---
def total_final_cost(items: Iterable[Priced]) -> float:
    """Сума остаточних вартостей."""
    return round(sum(item.final_cost() for item in items), 2)


def final_cost_by_tier(items: Iterable[Priced]) -> dict[str, float]:
    """Остаточна вартість за видом заявки (за українським алфавітом)."""
    totals: dict[str, float] = {}
    for item in items:
        totals[item.tier] = totals.get(item.tier, 0.0) + item.final_cost()
    return {tier: round(totals[tier], 2) for tier in sorted(totals, key=uk_key)}


def fault_summaries(items: Iterable[Priced]) -> tuple[FaultSummary, ...]:
    """Підсумок за несправностями: кількість, вартість робіт і остаточна вартість."""
    groups: dict[str, list[Priced]] = {}
    for item in items:
        groups.setdefault(item.fault, []).append(item)
    return tuple(
        FaultSummary(
            fault=fault,
            count=len(groups[fault]),
            cost=round(sum(i.cost for i in groups[fault]), 2),
            final_cost=round(sum(i.final_cost() for i in groups[fault]), 2),
        )
        for fault in sorted(groups, key=uk_key)
    )


def preview(orders: Iterable[RepairOrder], limit: int = 3) -> list[RepairOrder]:
    """Перші ``limit`` записів через itertools.islice."""
    return list(islice(orders, limit))


def stream_summary(orders: Iterable[RepairOrder]) -> dict[str, Any]:
    """Потоковий підсумок за один прохід (з ЛР6)."""
    count = opened = 0
    open_cost = total_cost = 0.0
    faults: dict[str, float] = {}
    devices: set[str] = set()
    best: RepairOrder | None = None
    for order in orders:
        count += 1
        total_cost += order.cost
        faults[order.fault] = faults.get(order.fault, 0.0) + order.cost
        devices.add(order.device)
        if order.is_open:
            opened += 1
            open_cost += order.cost
        if best is None or (-order.cost, order.date) < (-best.cost, best.date):
            best = order
    return {
        "count": count,
        "open_orders": opened,
        "open_cost": open_cost,
        "devices": len(devices),
        "cost_by_fault": {f: faults[f] for f in sorted(faults, key=uk_key)},
        "most_expensive_cost": best.cost if best else None,
        "total_cost": total_cost,
    }
