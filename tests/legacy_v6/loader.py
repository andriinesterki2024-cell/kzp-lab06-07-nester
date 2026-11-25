"""Читання CSV ремонтної майстерні та перетворення полів на типізовані значення.

Формат: UTF-8, заголовок ``ticket,client,device,received,completed,price``,
порядок стовпців довільний. Запис — словник із перетвореними полями
та похідними полями ``days`` (тривалість ремонту в днях).
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
FIELDS: tuple[str, ...] = ("ticket", "client", "device", "received", "completed", "price")

#: Запис після перетворення.
Record = dict[str, Any]


def _value(row: dict[str, str | None], field: str, row_number: int) -> str:
    """Повертає значення поля без зайвих пробілів або кидає DataError, якщо його немає."""
    raw = row.get(field)
    if raw is None or not raw.strip():
        raise DataError(f"Рядок {row_number}: немає значення поля {field}")
    return raw.strip()


def _parse_int(row: dict[str, str | None], field: str, row_number: int) -> int:
    """Перетворює поле на додатне ціле."""
    text = _value(row, field, row_number)
    try:
        number = int(text)
    except ValueError as error:
        raise DataError(f"Рядок {row_number}: поле {field} має бути цілим числом") from error
    if number <= 0:
        raise DataError(f"Рядок {row_number}: поле {field} має бути більшим за нуль")
    return number


def _parse_float(row: dict[str, str | None], field: str, row_number: int) -> float:
    """Перетворює поле на скінченне невід'ємне число (нуль дозволено)."""
    text = _value(row, field, row_number)
    try:
        number = float(text)
    except ValueError as error:
        raise DataError(f"Рядок {row_number}: поле {field} має бути числом") from error
    if not math.isfinite(number):
        raise DataError(f"Рядок {row_number}: поле {field} має бути скінченним числом")
    if number < 0:
        raise DataError(f"Рядок {row_number}: поле {field} не може бути від'ємним")
    return number


def _parse_date(row: dict[str, str | None], field: str, row_number: int) -> date:
    """Перетворює поле на дату у форматі ISO YYYY-MM-DD."""
    text = _value(row, field, row_number)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise DataError(
            f"Рядок {row_number}: поле {field} має бути датою у форматі YYYY-MM-DD"
        ) from error


def _parse_text(row: dict[str, str | None], field: str, row_number: int) -> str:
    """Нормалізує текст: прибирає зайві пробіли всередині й по краях."""
    return " ".join(_value(row, field, row_number).split())


def parse_row(row: dict[str, str | None], row_number: int) -> Record:
    """Перетворює рядок DictReader на запис.

    Args:
        row: словник рядків від ``csv.DictReader``.
        row_number: номер рядка у файлі (заголовок — рядок 1).

    Returns:
        Запис із полями ticket (int), client, device (str), received, completed (date),
        price (float) і похідним days (int).

    Raises:
        DataError: якщо значення немає, воно хибне або рядок має зайві значення.
    """
    if None in row:
        raise DataError(f"Рядок {row_number}: забагато значень")
    ticket = _parse_int(row, "ticket", row_number)
    client = _parse_text(row, "client", row_number)
    device = _parse_text(row, "device", row_number)
    received = _parse_date(row, "received", row_number)
    completed = _parse_date(row, "completed", row_number)
    price = _parse_float(row, "price", row_number)
    if completed <= received:
        raise DataError(f"Рядок {row_number}: поле completed має бути пізніше за received")
    return {
        "ticket": ticket,
        "client": client,
        "device": device,
        "received": received,
        "completed": completed,
        "price": price,
        "days": (completed - received).days,
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
            reader = csv.DictReader(source, skipinitialspace=False)
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
