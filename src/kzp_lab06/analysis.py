"""Обчислення над об'єктами ремонтів: відбір, словник, множина, завантаження, підсумок.

Функції працюють через властивості й спільні методи моделі; перевірок конкретного
підтипу та назв підтипів у модулі немає. Модуль не відкриває файлів і не форматує текст.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from itertools import islice
from typing import Any

from kzp_lab06.models import Priced, Repair, ReportSummary, Workload

#: Український алфавіт для впорядкування імен і назв.
UKRAINIAN_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
_ORDER = {letter: index for index, letter in enumerate(UKRAINIAN_ALPHABET)}


def uk_key(text: str) -> tuple[tuple[int, int | str], ...]:
    """Ключ сортування за українським алфавітом (без урахування регістру й апострофа)."""
    letters = text.casefold().replace("'", "").replace("’", "")
    return tuple((0, _ORDER[ch]) if ch in _ORDER else (1, ch) for ch in letters)


def in_work(repair: Repair, reference_date: date) -> bool:
    """Ремонт у роботі на дату: день прийому — так, день завершення — ні."""
    return repair.received <= reference_date < repair.completed


def select_in_work(repairs: list[Repair], reference_date: date) -> list[Repair]:
    """Відбір (list comprehension): ремонти в роботі, за ключем sort_key."""
    selected = [repair for repair in repairs if in_work(repair, reference_date)]
    return sorted(selected, key=lambda repair: repair.sort_key)


def count_by_device(repairs: list[Repair]) -> dict[str, int]:
    """Словник «тип пристрою → кількість ремонтів» за українським алфавітом."""
    counts: dict[str, int] = {}
    for repair in repairs:
        counts[repair.device] = counts.get(repair.device, 0) + 1
    return {device: counts[device] for device in sorted(counts, key=uk_key)}


def unique_clients(repairs: list[Repair]) -> set[str]:
    """Множина клієнтів без повторів (set comprehension)."""
    return {repair.client for repair in repairs}


def workload(repairs: list[Repair], reference_date: date) -> Workload:
    """Завантаження майстерні як незмінне значення Workload."""
    tickets = {repair.ticket for repair in repairs}
    busy = {repair.ticket for repair in repairs if in_work(repair, reference_date)}
    return Workload(in_work=len(busy), total=len(tickets))


def longest_repair(repairs: list[Repair]) -> Repair | None:
    """Найдовший ремонт; за рівності — менший номер квитанції."""
    if not repairs:
        return None
    return min(repairs, key=lambda repair: (-repair.days, repair.ticket))


def make_summary(
    repairs: list[Repair],
    *metrics: str,
    minimum_days: int = 1,
    **labels: str,
) -> dict[str, Any]:
    """Підсумок за числовими властивостями (``"days"``, ``"price"``), як у ЛР6."""
    allowed = {"days", "price"}
    unknown = [name for name in metrics if name not in allowed]
    if unknown:
        raise ValueError(f"Невідомі метрики: {', '.join(unknown)}")
    extra = [name for name in labels if name not in metrics]
    if extra:
        raise ValueError(f"Підписи для невибраних метрик: {', '.join(extra)}")
    kept = [repair for repair in repairs if repair.days >= minimum_days]
    summary: dict[str, Any] = {"count": len(kept)}
    for name in metrics:
        summary[labels.get(name, name)] = float(sum(getattr(repair, name) for repair in kept))
    return summary


def build_report(repairs: list[Repair], reference_date: date) -> ReportSummary:
    """Збирає незмінний підсумок звіту (вхідний список не змінюється)."""
    totals = make_summary(repairs, "days", "price")
    return ReportSummary(
        reference_date=reference_date,
        count=len(repairs),
        in_work=tuple(select_in_work(repairs, reference_date)),
        workload=workload(repairs, reference_date),
        count_by_device=tuple(count_by_device(repairs).items()),
        clients=tuple(sorted(unique_clients(repairs), key=uk_key)),
        longest=longest_repair(repairs),
        total_days=int(totals["days"]),
        total_price=totals["price"],
    )


# --- функції протоколу Priced: лише спільний метод, без перевірки класу ---
def total_revenue(items: Iterable[Priced]) -> float:
    """Сума цін із надбавками."""
    return round(sum(item.total_price() for item in items), 2)


def revenue_by_tier(items: Iterable[Priced]) -> dict[str, float]:
    """Виторг із надбавками за рівнями обслуговування (за українським алфавітом)."""
    totals: dict[str, float] = {}
    for item in items:
        totals[item.tier] = totals.get(item.tier, 0.0) + item.total_price()
    return {tier: round(totals[tier], 2) for tier in sorted(totals, key=uk_key)}


def most_expensive(items: Iterable[Priced]) -> Priced | None:
    """Позиція з найбільшою ціною з надбавками (перша за рівності)."""
    best: Priced | None = None
    for item in items:
        if best is None or item.total_price() > best.total_price():
            best = item
    return best


def preview(repairs: Iterable[Repair], limit: int = 3) -> list[Repair]:
    """Перші ``limit`` записів через itertools.islice."""
    return list(islice(repairs, limit))


def stream_summary(repairs: Iterable[Repair], reference_date: date) -> dict[str, Any]:
    """Потоковий підсумок за один прохід (з ЛР6)."""
    count = busy = total_days = 0
    total_price = 0.0
    tickets: set[int] = set()
    clients: set[str] = set()
    devices: dict[str, int] = {}
    longest: Repair | None = None
    for repair in repairs:
        count += 1
        tickets.add(repair.ticket)
        clients.add(repair.client)
        devices[repair.device] = devices.get(repair.device, 0) + 1
        if in_work(repair, reference_date):
            busy += 1
        if longest is None or (-repair.days, repair.ticket) < (-longest.days, longest.ticket):
            longest = repair
        total_days += repair.days
        total_price += repair.price
    return {
        "count": count,
        "in_work": busy,
        "tickets": len(tickets),
        "clients": len(clients),
        "count_by_device": {d: devices[d] for d in sorted(devices, key=uk_key)},
        "longest_ticket": longest.ticket if longest else None,
        "total_days": total_days,
        "total_price": total_price,
    }
