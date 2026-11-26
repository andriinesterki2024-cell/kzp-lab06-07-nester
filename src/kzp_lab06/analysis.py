"""Обчислення над заявками (таблиця варіантів ЛР6, варіант 16).

Відбір — ``status != "done"``; словник — сума вартості за несправністю (fault);
множина — пристрої; звіт — відкриті заявки й найдорожчий ремонт.
Модуль не відкриває файлів і не форматує текст.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import islice
from typing import Any

from kzp_lab06.loader import STATUSES, Record

#: Український алфавіт для впорядкування назв (str.__lt__ порівнює коди Unicode,
#: тому «Іваненко» опинився б після «Шевчука»).
UKRAINIAN_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
_ORDER = {letter: index for index, letter in enumerate(UKRAINIAN_ALPHABET)}

#: Стан завершеної заявки.
DONE = "done"


def uk_key(text: str) -> tuple[tuple[int, int | str], ...]:
    """Ключ сортування за українським алфавітом (без урахування регістру й апострофа)."""
    letters = text.casefold().replace("'", "").replace("’", "")
    return tuple((0, _ORDER[ch]) if ch in _ORDER else (1, ch) for ch in letters)


def is_open(record: Record) -> bool:
    """Заявка відкрита (незавершена), якщо її стан не ``done``."""
    return record["status"] != DONE


def open_orders(records: list[Record]) -> list[Record]:
    """Відбір (list comprehension): відкриті заявки за датою, потім за клієнтом."""
    selected = [record for record in records if is_open(record)]
    return sorted(selected, key=lambda record: (record["date"], uk_key(record["customer"])))


def cost_by_fault(records: list[Record]) -> dict[str, float]:
    """Словник «несправність → сума вартості» з ключами за українським алфавітом."""
    totals: dict[str, float] = {}
    # Звичайний цикл проходить записи один раз; comprehension із sum() для кожної
    # несправності проходив би їх повторно.
    for record in records:
        totals[record["fault"]] = totals.get(record["fault"], 0.0) + record["cost"]
    # dict comprehension: стабільний порядок ключів.
    return {fault: totals[fault] for fault in sorted(totals, key=uk_key)}


def unique_devices(records: list[Record]) -> set[str]:
    """Множина пристроїв без повторів (set comprehension)."""
    return {record["device"] for record in records}


def most_expensive(records: list[Record]) -> Record | None:
    """Найдорожчий ремонт; за рівної вартості — раніша дата."""
    if not records:
        return None
    return min(records, key=lambda record: (-record["cost"], record["date"]))


def make_summary(
    records: list[Record],
    *statuses: str,
    minimum_cost: float = 0.0,
    **labels: str,
) -> dict[str, Any]:
    """Підсумок вартості за станами заявок.

    Args:
        records: записи.
        *statuses: стани, для яких рахується сума вартості
            (``"new"``, ``"in_progress"``, ``"done"``).
        minimum_cost: враховуються лише заявки з вартістю від цього значення (типово 0.0).
        **labels: підписи станів у результаті, наприклад ``new="Нові"``.

    Returns:
        Словник ``{"count": n, <підпис або стан>: сума, ...}`` у порядку *statuses;
        count — кількість врахованих заявок вибраних станів.

    Raises:
        ValueError: невідомий стан або підпис для стану, якого немає в *statuses.
    """
    unknown = [name for name in statuses if name not in STATUSES]
    if unknown:
        raise ValueError(f"Невідомі стани: {', '.join(unknown)}")
    extra = [name for name in labels if name not in statuses]
    if extra:
        raise ValueError(f"Підписи для невибраних станів: {', '.join(extra)}")
    kept = [r for r in records if r["status"] in statuses and r["cost"] >= minimum_cost]
    summary: dict[str, Any] = {"count": len(kept)}
    for status in statuses:
        summary[labels.get(status, status)] = sum(r["cost"] for r in kept if r["status"] == status)
    return summary


def build_report(records: list[Record]) -> dict[str, Any]:
    """Збирає всі показники звіту у словник (вхідний список не змінюється)."""
    opened = open_orders(records)
    return {
        "count": len(records),
        "open_orders": opened,
        "open_cost": sum(record["cost"] for record in opened),
        "cost_by_fault": cost_by_fault(records),
        "devices": sorted(unique_devices(records), key=uk_key),
        "most_expensive": most_expensive(records),
        "total_cost": sum(record["cost"] for record in records),
    }


def preview(records: Iterable[Record], limit: int = 3) -> list[Record]:
    """Перші ``limit`` записів через itertools.islice (генератор далі не читається)."""
    return list(islice(records, limit))


def stream_summary(records: Iterable[Record]) -> dict[str, Any]:
    """Потоковий підсумок за один прохід (завдання із зірочкою).

    Зберігає лише лічильники, словник сум за несправністю, множину пристроїв і один
    найдорожчий запис, тому придатний для генератора ``iter_records`` на великому файлі.
    """
    count = 0
    opened = 0
    open_cost = 0.0
    total_cost = 0.0
    faults: dict[str, float] = {}
    devices: set[str] = set()
    best: Record | None = None
    for record in records:
        count += 1
        total_cost += record["cost"]
        faults[record["fault"]] = faults.get(record["fault"], 0.0) + record["cost"]
        devices.add(record["device"])
        if is_open(record):
            opened += 1
            open_cost += record["cost"]
        if best is None or (-record["cost"], record["date"]) < (-best["cost"], best["date"]):
            best = record
    return {
        "count": count,
        "open_orders": opened,
        "open_cost": open_cost,
        "devices": len(devices),
        "cost_by_fault": {f: faults[f] for f in sorted(faults, key=uk_key)},
        "most_expensive_cost": best["cost"] if best else None,
        "total_cost": total_cost,
    }
