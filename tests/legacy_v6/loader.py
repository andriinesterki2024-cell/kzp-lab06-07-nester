"""Читання CSV ремонтної майстерні та перетворення полів на типізовані значення.

Формат (таблиця варіантів ЛР6, варіант 16): UTF-8, заголовок
``customer,device,fault,date,cost,status``, порядок стовпців довільний.
Запис — словник із перетвореними полями.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from legacy_v6.errors import DataError

#: Обов'язкові стовпці CSV.
FIELDS: tuple[str, ...] = ("customer", "device", "fault", "date", "cost", "status")

#: Допустимі стани заявки (нормалізовані до нижнього регістру).
STATUSES: frozenset[str] = frozenset({"new", "in_progress", "done"})

#: Запис після перетворення.
Record = dict[str, Any]


def _value(row: dict[str, str | None], field: str, row_number: int) -> str:
    """Повертає значення поля без зайвих пробілів або кидає DataError, якщо його немає."""
    raw = row.get(field)
    if raw is None or not raw.strip():
        raise DataError(f"Рядок {row_number}: немає значення поля {field}")
    return raw.strip()


def _parse_cost(row: dict[str, str | None], row_number: int) -> float:
    """Перетворює вартість на скінченне невід'ємне число (нуль дозволено)."""
    text = _value(row, "cost", row_number)
    try:
        number = float(text)
    except ValueError as error:
        raise DataError(f"Рядок {row_number}: поле cost має бути числом") from error
    if not math.isfinite(number):
        raise DataError(f"Рядок {row_number}: поле cost має бути скінченним числом")
    if number < 0:
        raise DataError(f"Рядок {row_number}: поле cost не може бути від'ємним")
    return number


def _parse_date(row: dict[str, str | None], row_number: int) -> date:
    """Перетворює дату ISO YYYY-MM-DD."""
    text = _value(row, "date", row_number)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise DataError(
            f"Рядок {row_number}: поле date має бути датою у форматі YYYY-MM-DD"
        ) from error


def _parse_status(row: dict[str, str | None], row_number: int) -> str:
    """Нормалізує стан (нижній регістр) і перевіряє, що він допустимий."""
    status = _value(row, "status", row_number).casefold()
    if status not in STATUSES:
        raise DataError(
            f"Рядок {row_number}: поле status має бути одним із: done, in_progress, new"
        )
    return status


def _parse_text(row: dict[str, str | None], field: str, row_number: int) -> str:
    """Нормалізує текст: прибирає зайві пробіли всередині й по краях."""
    return " ".join(_value(row, field, row_number).split())


def parse_row(row: dict[str, str | None], row_number: int) -> Record:
    """Перетворює рядок DictReader на запис.

    Args:
        row: словник рядків від ``csv.DictReader``.
        row_number: номер рядка у файлі (заголовок — рядок 1).

    Returns:
        Запис із полями customer, device, fault (str), date (date), cost (float), status (str).

    Raises:
        DataError: якщо значення немає, воно хибне або рядок має зайві значення.
    """
    if None in row:
        raise DataError(f"Рядок {row_number}: забагато значень")
    return {
        "customer": _parse_text(row, "customer", row_number),
        "device": _parse_text(row, "device", row_number),
        "fault": _parse_text(row, "fault", row_number),
        "date": _parse_date(row, row_number),
        "cost": _parse_cost(row, row_number),
        "status": _parse_status(row, row_number),
    }


def _check_header(fieldnames: list[str] | None) -> None:
    """Перевіряє, що заголовок є і містить усі обов'язкові стовпці."""
    if fieldnames is None:
        raise DataError("Файл порожній: немає рядка заголовка")
    present = {name.strip() for name in fieldnames}
    missing = [field for field in FIELDS if field not in present]
    if missing:
        raise DataError(f"У заголовку немає стовпців: {', '.join(missing)}")


def iter_records(path: Path) -> Iterator[Record]:
    """Генератор: читає CSV і повертає записи по одному, не зберігаючи весь файл.

    Raises:
        DataError: файл не прочитано, CSV пошкоджений або значення хибне.
    """
    try:
        # newline="" передає керування роздільниками рядків модулю csv.
        with path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            _check_header(reader.fieldnames)
            reader.fieldnames = [name.strip() for name in reader.fieldnames or []]
            for row in reader:
                yield parse_row(row, reader.line_num)
    except (OSError, UnicodeDecodeError) as error:
        raise DataError(f"Не вдалося прочитати файл: {path}") from error
    except csv.Error as error:
        raise DataError(f"Пошкоджений CSV: {error}") from error


def load_records(path: Path) -> list[Record]:
    """Читає всі записи файла у список (порядок файла зберігається)."""
    return list(iter_records(path))
