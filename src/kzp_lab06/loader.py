"""Читання CSV ремонтної майстерні та створення об'єктів моделі.

Формат: UTF-8, заголовок ``ticket,client,device,received,completed,price``,
порядок стовпців довільний. Текст перетворюється на int, date і float тут,
а інваріанти перевіряють setter-и моделі; їхні помилки отримують номер рядка.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from kzp_lab06.errors import DataError
from kzp_lab06.models import Repair, create_repair

#: Обов'язкові стовпці CSV.
FIELDS: tuple[str, ...] = ("ticket", "client", "device", "received", "completed", "price")


def _value(row: dict[str, str | None], field: str, row_number: int) -> str:
    """Повертає значення поля без зайвих пробілів або кидає DataError, якщо його немає."""
    raw = row.get(field)
    if raw is None or not raw.strip():
        raise DataError(f"Рядок {row_number}: немає значення поля {field}")
    return raw.strip()


def _parse_int(row: dict[str, str | None], field: str, row_number: int) -> int:
    """Перетворює текст на ціле."""
    # _value поза try: DataError успадковує ValueError і не має перехоплюватися нижче.
    text = _value(row, field, row_number)
    try:
        return int(text)
    except ValueError as error:
        raise DataError(f"Рядок {row_number}: поле {field} має бути цілим числом") from error


def _parse_float(row: dict[str, str | None], field: str, row_number: int) -> float:
    """Перетворює текст на число."""
    # _value поза try: DataError успадковує ValueError і не має перехоплюватися нижче.
    text = _value(row, field, row_number)
    try:
        return float(text)
    except ValueError as error:
        raise DataError(f"Рядок {row_number}: поле {field} має бути числом") from error


def _parse_date(row: dict[str, str | None], field: str, row_number: int) -> date:
    """Перетворює текст на дату ISO YYYY-MM-DD."""
    # _value поза try: DataError успадковує ValueError і не має перехоплюватися нижче.
    text = _value(row, field, row_number)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise DataError(
            f"Рядок {row_number}: поле {field} має бути датою у форматі YYYY-MM-DD"
        ) from error


def parse_row(row: dict[str, str | None], row_number: int) -> Repair:
    """Перетворює рядок DictReader на об'єкт підтипу Repair.

    Raises:
        DataError: значення немає, воно хибне, рядок має зайві значення або порушено інваріант.
    """
    if None in row:
        raise DataError(f"Рядок {row_number}: забагато значень")
    ticket = _parse_int(row, "ticket", row_number)
    client = _value(row, "client", row_number)
    device = _value(row, "device", row_number)
    received = _parse_date(row, "received", row_number)
    completed = _parse_date(row, "completed", row_number)
    price = _parse_float(row, "price", row_number)
    try:
        return create_repair(ticket, client, device, received, completed, price)
    except (TypeError, ValueError) as error:
        # Повідомлення моделі збігаються з ЛР6; додається лише номер рядка.
        raise DataError(f"Рядок {row_number}: {error}") from error


def _check_header(fieldnames: list[str] | None) -> None:
    """Перевіряє, що заголовок є і містить усі обов'язкові стовпці."""
    if fieldnames is None:
        raise DataError("Файл порожній: немає рядка заголовка")
    present = {name.strip() for name in fieldnames}
    missing = [field for field in FIELDS if field not in present]
    if missing:
        raise DataError(f"У заголовку немає стовпців: {', '.join(missing)}")


def iter_records(path: Path) -> Iterator[Repair]:
    """Генератор об'єктів: читає CSV по одному запису.

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


def load_records(path: Path) -> list[Repair]:
    """Читає всі записи файла у список об'єктів (порядок файла зберігається)."""
    return list(iter_records(path))
