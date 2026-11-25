"""Обчислення над записами ремонтів: відбір, словник, множина, завантаження, підсумок.

Модуль не відкриває файлів і не форматує текст.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from itertools import islice
from typing import Any

from kzp_lab06.loader import Record

#: Український алфавіт для впорядкування імен і назв (str.__lt__ порівнює коди Unicode,
#: тому «Іваненко» опинився б після «Яковенка», а «Є» — перед «А»).
UKRAINIAN_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
_ORDER = {letter: index for index, letter in enumerate(UKRAINIAN_ALPHABET)}


def uk_key(text: str) -> tuple[tuple[int, int | str], ...]:
    """Ключ сортування за українським алфавітом (без урахування регістру й апострофа).

    Кирилиця йде за алфавітом, інші символи — після неї за кодом.
    """
    letters = text.casefold().replace("'", "").replace("’", "")
    return tuple((0, _ORDER[ch]) if ch in _ORDER else (1, ch) for ch in letters)


def in_work(record: Record, reference_date: date) -> bool:
    """Ремонт у роботі на дату: прийнято не пізніше дати й ще не завершено.

    День прийому вже в роботі, день завершення — ні.
    """
    return record["received"] <= reference_date < record["completed"]


def select_in_work(records: list[Record], reference_date: date) -> list[Record]:
    """Відбір (list comprehension): ремонти в роботі, за номером квитанції."""
    selected = [record for record in records if in_work(record, reference_date)]
    return sorted(selected, key=lambda record: (record["ticket"], record["received"]))


def count_by_device(records: list[Record]) -> dict[str, int]:
    """Словник «тип пристрою → кількість ремонтів» за українським алфавітом."""
    counts: dict[str, int] = {}
    # Звичайний цикл проходить записи один раз; comprehension з count() проходив би
    # їх для кожного типу пристрою.
    for record in records:
        counts[record["device"]] = counts.get(record["device"], 0) + 1
    # dict comprehension: стабільний порядок ключів.
    return {device: counts[device] for device in sorted(counts, key=uk_key)}


def unique_clients(records: list[Record]) -> set[str]:
    """Множина клієнтів без повторів (set comprehension)."""
    return {record["client"] for record in records}


def workload(records: list[Record], reference_date: date) -> dict[str, float | int]:
    """Завантаження майстерні: частка ремонтів у роботі на дату серед усіх квитанцій файла."""
    tickets = {record["ticket"] for record in records}
    busy = {record["ticket"] for record in records if in_work(record, reference_date)}
    percent = 100.0 * len(busy) / len(tickets) if tickets else 0.0
    return {"in_work": len(busy), "total": len(tickets), "percent": percent}


def longest_repair(records: list[Record]) -> Record | None:
    """Найдовший ремонт за кількістю днів; за рівності — менший номер квитанції."""
    if not records:
        return None
    return min(records, key=lambda record: (-record["days"], record["ticket"]))


def make_summary(
    records: list[Record],
    *metrics: str,
    minimum_days: int = 1,
    **labels: str,
) -> dict[str, Any]:
    """Підсумок за довільними числовими полями.

    Args:
        records: записи.
        *metrics: назви числових полів для підсумовування (``"days"``, ``"price"``).
        minimum_days: враховуються лише ремонти з тривалістю від цього значення (типово 1).
        **labels: підписи метрик у результаті, наприклад ``price="Виторг"``.

    Returns:
        Словник ``{"count": n, <підпис або назва>: сума, ...}`` у порядку *metrics.

    Raises:
        ValueError: невідома метрика або підпис для метрики, якої немає в *metrics.
    """
    allowed = {"days", "price"}
    unknown = [name for name in metrics if name not in allowed]
    if unknown:
        raise ValueError(f"Невідомі метрики: {', '.join(unknown)}")
    extra = [name for name in labels if name not in metrics]
    if extra:
        raise ValueError(f"Підписи для невибраних метрик: {', '.join(extra)}")
    kept = [record for record in records if record["days"] >= minimum_days]
    summary: dict[str, Any] = {"count": len(kept)}
    for name in metrics:
        summary[labels.get(name, name)] = float(sum(record[name] for record in kept))
    return summary


def build_report(records: list[Record], reference_date: date) -> dict[str, Any]:
    """Збирає всі показники звіту у словник (вхідний список не змінюється)."""
    totals = make_summary(records, "days", "price")
    return {
        "reference_date": reference_date,
        "count": len(records),
        "in_work": select_in_work(records, reference_date),
        "workload": workload(records, reference_date),
        "count_by_device": count_by_device(records),
        "clients": sorted(unique_clients(records), key=uk_key),
        "longest": longest_repair(records),
        "total_days": int(totals["days"]),
        "total_price": totals["price"],
    }


def preview(records: Iterable[Record], limit: int = 3) -> list[Record]:
    """Перші ``limit`` записів через itertools.islice (генератор далі не читається)."""
    return list(islice(records, limit))


def stream_summary(records: Iterable[Record], reference_date: date) -> dict[str, Any]:
    """Потоковий підсумок за один прохід (завдання із зірочкою).

    Зберігає лише лічильники, множини квитанцій і клієнтів та один найдовший запис,
    тому придатний для генератора ``iter_records`` на великому файлі.
    """
    count = 0
    busy = 0
    tickets: set[int] = set()
    clients: set[str] = set()
    devices: dict[str, int] = {}
    longest: Record | None = None
    total_days = 0
    total_price = 0.0
    for record in records:
        count += 1
        tickets.add(record["ticket"])
        clients.add(record["client"])
        devices[record["device"]] = devices.get(record["device"], 0) + 1
        if in_work(record, reference_date):
            busy += 1
        if longest is None or (-record["days"], record["ticket"]) < (
            -longest["days"],
            longest["ticket"],
        ):
            longest = record
        total_days += record["days"]
        total_price += record["price"]
    return {
        "count": count,
        "in_work": busy,
        "tickets": len(tickets),
        "clients": len(clients),
        "count_by_device": {d: devices[d] for d in sorted(devices, key=uk_key)},
        "longest_ticket": longest["ticket"] if longest else None,
        "total_days": total_days,
        "total_price": total_price,
    }
