"""Читання CSV ремонтної майстерні та створення об'єктів моделі.

Формат (таблиця варіантів ЛР6, варіант 16): UTF-8, заголовок
``customer,device,fault,date,cost,status``, порядок стовпців довільний. Текст перетворюється
на date і float тут, а інваріанти перевіряють setter-и моделі; їхні помилки отримують номер рядка.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from kzp_lab06.errors import DataError
from kzp_lab06.models import RepairOrder, create_order

#: Обов'язкові стовпці CSV.
FIELDS: tuple[str, ...] = ("customer", "device", "fault", "date", "cost", "status")


def _value(row: dict[str, str | None], field: str, row_number: int) -> str:
    """Повертає значення поля без зайвих пробілів або кидає DataError, якщо його немає."""
    raw = row.get(field)
    if raw is None or not raw.strip():
        raise DataError(f"Рядок {row_number}: немає значення поля {field}")
    return raw.strip()


def _parse_cost(row: dict[str, str | None], row_number: int) -> float:
    """Перетворює текст вартості на число (діапазон перевіряє модель)."""
    # _value поза try: DataError успадковує ValueError і не має перехоплюватися нижче.
    text = _value(row, "cost", row_number)
    try:
        return float(text)
    except ValueError as error:
        raise DataError(f"Рядок {row_number}: поле cost має бути числом") from error


def _parse_date(row: dict[str, str | None], row_number: int) -> date:
    """Перетворює текст на дату ISO YYYY-MM-DD."""
    text = _value(row, "date", row_number)
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise DataError(
            f"Рядок {row_number}: поле date має бути датою у форматі YYYY-MM-DD"
        ) from error


def parse_row(row: dict[str, str | None], row_number: int) -> RepairOrder:
    """Перетворює рядок DictReader на об'єкт підтипу RepairOrder.

    Raises:
        DataError: значення немає, воно хибне, рядок має зайві значення або порушено інваріант.
    """
    if None in row:
        raise DataError(f"Рядок {row_number}: забагато значень")
    customer = _value(row, "customer", row_number)
    device = _value(row, "device", row_number)
    fault = _value(row, "fault", row_number)
    order_date = _parse_date(row, row_number)
    cost = _parse_cost(row, row_number)
    status = row.get("status") or ""
    try:
        return create_order(customer, device, fault, order_date, cost, status)
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


def iter_records(path: Path) -> Iterator[RepairOrder]:
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


def load_records(path: Path) -> list[RepairOrder]:
    """Читає всі записи файла у список об'єктів (порядок файла зберігається)."""
    return list(iter_records(path))
