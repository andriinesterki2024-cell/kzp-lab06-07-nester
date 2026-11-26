"""Об'єктна модель ремонтної майстерні (ЛР7, таблиця варіантів: варіант 16).

Базовий клас ``RepairOrder``, підтипи ``WarrantyRepair`` і ``PaidRepair``, спільна операція —
``final_cost()`` з різною знижкою, підсумок — несправності (``FaultSummary``). Модуль не читає
файлів. Тексти помилок setter-ів збігаються з повідомленнями ЛР6, тому loader лише додає
номер рядка.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol, runtime_checkable

#: Допустимі стани заявки.
STATUSES = frozenset({"new", "in_progress", "done"})

#: Підписи станів для рядка звіту.
STATUS_LABELS = {"new": "нова", "in_progress": "у роботі", "done": "виконана"}

#: Префікс несправності, яким у CSV позначено гарантійний випадок (окремої колонки виду
#: таблиця варіантів ЛР6 не передбачає).
WARRANTY_PREFIX = "гарантія"


#: Український алфавіт для впорядкування імен і назв.
UKRAINIAN_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
_ORDER = {letter: index for index, letter in enumerate(UKRAINIAN_ALPHABET)}


def uk_key(text: str) -> tuple[tuple[int, int | str], ...]:
    """Ключ сортування за українським алфавітом (без урахування регістру й апострофа)."""
    letters = text.casefold().replace("'", "").replace("’", "")
    return tuple((0, _ORDER[ch]) if ch in _ORDER else (1, ch) for ch in letters)


def _money(value: Decimal) -> float:
    """Округлює суму до копійки за правилом ROUND_HALF_UP."""
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _text(value: object, field: str) -> str:
    """Нормалізує текстове поле або кидає виняток із повідомленням ЛР6."""
    if not isinstance(value, str):
        raise TypeError(f"поле {field} має бути рядком")
    text = " ".join(value.split())
    if not text:
        raise ValueError(f"немає значення поля {field}")
    return text


class RepairOrder:
    """Заявка на ремонт: базова сутність зі спільною перевіркою полів.

    Змінювані поля (customer, device, fault, cost, status) перевіряються setter-ами властивостей,
    дата — лише для читання. Остаточну вартість для клієнта рахує ``final_cost()`` у підтипах.
    """

    __slots__ = ("_customer", "_device", "_fault", "_date", "_cost", "_status")

    #: Назва рівня (виду заявки) для звіту; перевизначається в підтипах.
    TIER = "Заявка"

    def __init__(
        self, customer: str, device: str, fault: str, order_date: date, cost: float, status: str
    ) -> None:
        # Присвоєння через властивості: конструктор і пізніші зміни перевіряє один код.
        # Порядок перевірок як у ЛР6: текстові поля, дата, вартість, стан.
        self.customer = customer
        self.device = device
        self.fault = fault
        if not isinstance(order_date, date):
            raise TypeError("поле date має бути датою")
        self._date = order_date
        self.cost = cost
        self.status = status

    # --- змінювані властивості з перевіркою ---
    @property
    def customer(self) -> str:
        """Клієнт (непорожній, зайві пробіли прибрано)."""
        return self._customer

    @customer.setter
    def customer(self, value: str) -> None:
        self._customer = _text(value, "customer")

    @property
    def device(self) -> str:
        """Пристрій (непорожній)."""
        return self._device

    @device.setter
    def device(self, value: str) -> None:
        self._device = _text(value, "device")

    @property
    def fault(self) -> str:
        """Несправність (непорожня)."""
        return self._fault

    @fault.setter
    def fault(self, value: str) -> None:
        self._fault = _text(value, "fault")

    @property
    def cost(self) -> float:
        """Вартість робіт (скінченне невід'ємне число; нуль дозволено)."""
        return self._cost

    @cost.setter
    def cost(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("поле cost має бути числом")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("поле cost має бути скінченним числом")
        if number < 0:
            raise ValueError("поле cost не може бути від'ємним")
        # Запис у внутрішнє поле: self.cost = ... викликав би цей самий setter.
        self._cost = number

    @property
    def status(self) -> str:
        """Стан заявки: new, in_progress або done (регістр нормалізується)."""
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        normalized = _text(value, "status").casefold()
        if normalized not in STATUSES:
            raise ValueError("поле status має бути одним із: done, in_progress, new")
        self._status = normalized

    # --- властивості лише для читання ---
    @property
    def date(self) -> date:
        """Дата заявки."""
        return self._date

    @property
    def is_open(self) -> bool:
        """Заявка відкрита, якщо стан не ``done``."""
        return self._status != "done"

    @property
    def tier(self) -> str:
        """Вид заявки (назва для звіту)."""
        return self.TIER

    @property
    def sort_key(self) -> tuple[date, tuple[tuple[int, int | str], ...]]:
        """Ключ впорядкування відкритих заявок: дата, клієнт за українським алфавітом."""
        return (self._date, uk_key(self._customer))

    def final_cost(self) -> float:
        """Остаточна вартість для клієнта; знижку задає підтип."""
        raise NotImplementedError("final_cost() визначається в підтипі")

    # --- спеціальні методи ---
    def __str__(self) -> str:
        return (
            f"{self._date.isoformat()} | {self._customer} | {self._device} | "
            f"{self._fault} | {self._cost:.2f} грн | {STATUS_LABELS[self._status]}"
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(customer={self._customer!r}, device={self._device!r}, "
            f"fault={self._fault!r}, date={self._date!r}, cost={self._cost!r}, "
            f"status={self._status!r})"
        )

    def _fields(self) -> tuple[object, ...]:
        return (self._customer, self._device, self._fault, self._date, self._cost, self._status)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RepairOrder):
            return NotImplemented
        return type(self) is type(other) and self._fields() == other._fields()

    #: Змінюваний об'єкт не використовується як ключ словника.
    __hash__ = None  # type: ignore[assignment]


class WarrantyRepair(RepairOrder):
    """Гарантійний ремонт: знижка 100 % — роботи покриває гарантія."""

    __slots__ = ()
    TIER = "Гарантійний"
    DISCOUNT = Decimal("1.00")

    def final_cost(self) -> float:
        return _money(Decimal(str(self.cost)) * (1 - self.DISCOUNT))


class PaidRepair(RepairOrder):
    """Платний ремонт: знижка 5 % для ремонтів від 3000 грн, інакше без знижки."""

    __slots__ = ()
    TIER = "Платний"
    DISCOUNT = Decimal("0.05")
    THRESHOLD = Decimal("3000")

    def final_cost(self) -> float:
        cost = Decimal(str(self.cost))
        rate = self.DISCOUNT if cost >= self.THRESHOLD else Decimal("0")
        return _money(cost * (1 - rate))


def create_order(
    customer: str, device: str, fault: str, order_date: date, cost: float, status: str
) -> RepairOrder:
    """Фабрика: єдине місце вибору підтипу (гарантія — за префіксом несправності)."""
    is_warranty = isinstance(fault, str) and fault.strip().casefold().startswith(WARRANTY_PREFIX)
    kind = WarrantyRepair if is_warranty else PaidRepair
    return kind(customer, device, fault, order_date, cost, status)


@runtime_checkable
class Priced(Protocol):
    """Контракт підсумку: несправність, вартість, вид і остаточна вартість."""

    @property
    def fault(self) -> str: ...

    @property
    def cost(self) -> float: ...

    @property
    def tier(self) -> str: ...

    def final_cost(self) -> float: ...


@dataclass(frozen=True)
class FaultSummary:
    """Підсумок за несправністю (таблиця варіантів ЛР7: «підсумок — несправності»)."""

    fault: str
    count: int
    cost: float
    final_cost: float


@dataclass(frozen=True)
class ReportSummary:
    """Незмінний підсумок звіту; будує analysis.build_report, читає reporting."""

    count: int
    open_orders: tuple[RepairOrder, ...]
    open_cost: float
    cost_by_fault: tuple[tuple[str, float], ...]
    devices: tuple[str, ...]
    most_expensive: RepairOrder | None
    total_cost: float
