"""Об'єктна модель ремонтної майстерні (ЛР7): класи, фабрика, протокол і підсумки.

Модуль не читає файлів. Тексти помилок setter-ів збігаються з повідомленнями ЛР6,
тому loader лише додає номер рядка.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol, runtime_checkable

#: Типи пристроїв, які обслуговуються як побутова техніка (порівняння без регістру).
APPLIANCES = frozenset(
    {
        "пральна машина",
        "холодильник",
        "посудомийна машина",
        "бойлер",
        "плита",
        "кондиціонер",
        "мікрохвильова піч",
    }
)


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


class Repair:
    """Ремонт за квитанцією: базова сутність зі спільною перевіркою полів.

    Змінювані поля (ticket, client, device, price) перевіряються setter-ами властивостей,
    дати прийому й завершення — лише для читання. Ціну з надбавками рахує ``total_price()``
    у підтипах.
    """

    __slots__ = ("_ticket", "_client", "_device", "_received", "_completed", "_price")

    #: Назва рівня обслуговування; перевизначається в підтипах.
    TIER = "Ремонт"

    def __init__(
        self,
        ticket: int,
        client: str,
        device: str,
        received: date,
        completed: date,
        price: float,
    ) -> None:
        # Присвоєння через властивості: конструктор і пізніші зміни перевіряє один код.
        self.ticket = ticket
        self.client = client
        self.device = device
        # Порядок перевірок як у ЛР6: ціна перевіряється раніше за співвідношення дат.
        self.price = price
        if not isinstance(received, date) or not isinstance(completed, date):
            raise TypeError("поля received і completed мають бути датами")
        if completed <= received:
            raise ValueError("поле completed має бути пізніше за received")
        self._received = received
        self._completed = completed

    # --- змінювані властивості з перевіркою ---
    @property
    def ticket(self) -> int:
        """Номер квитанції (int, не bool, більше нуля)."""
        return self._ticket

    @ticket.setter
    def ticket(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("поле ticket має бути цілим числом")
        if value <= 0:
            raise ValueError("поле ticket має бути більшим за нуль")
        self._ticket = value

    @property
    def client(self) -> str:
        """Клієнт (непорожній, зайві пробіли прибрано)."""
        return self._client

    @client.setter
    def client(self, value: str) -> None:
        self._client = _text(value, "client")

    @property
    def device(self) -> str:
        """Тип пристрою (непорожній)."""
        return self._device

    @device.setter
    def device(self, value: str) -> None:
        self._device = _text(value, "device")

    @property
    def price(self) -> float:
        """Вартість ремонту (скінченне невід'ємне число; нуль — гарантійний ремонт)."""
        return self._price

    @price.setter
    def price(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("поле price має бути числом")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("поле price має бути скінченним числом")
        if number < 0:
            raise ValueError("поле price не може бути від'ємним")
        # Запис у внутрішнє поле: self.price = ... викликав би цей самий setter.
        self._price = number

    # --- властивості лише для читання ---
    @property
    def received(self) -> date:
        """Дата прийому."""
        return self._received

    @property
    def completed(self) -> date:
        """Дата завершення."""
        return self._completed

    @property
    def days(self) -> int:
        """Тривалість ремонту в днях."""
        return (self._completed - self._received).days

    @property
    def tier(self) -> str:
        """Рівень обслуговування (назва для звіту)."""
        return self.TIER

    @property
    def sort_key(self) -> tuple[int, date, str]:
        """Ключ впорядкування у звіті: квитанція, дата прийому, клієнт."""
        return (self._ticket, self._received, self._client)

    def total_price(self) -> float:
        """Ціна з надбавками; формула залежить від підтипу."""
        raise NotImplementedError("total_price() визначається в підтипі")

    # --- спеціальні методи ---
    def __str__(self) -> str:
        return (
            f"{self._ticket} | {self._client} | {self._device} | "
            f"{self._received.isoformat()}..{self._completed.isoformat()}"
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(ticket={self._ticket!r}, client={self._client!r}, "
            f"device={self._device!r}, received={self._received!r}, "
            f"completed={self._completed!r}, price={self._price!r})"
        )

    def _fields(self) -> tuple[object, ...]:
        return (
            self._ticket,
            self._client,
            self._device,
            self._received,
            self._completed,
            self._price,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Repair):
            return NotImplemented
        return type(self) is type(other) and self._fields() == other._fields()

    #: Змінюваний об'єкт не використовується як ключ словника.
    __hash__ = None  # type: ignore[assignment]


class GadgetRepair(Repair):
    """Ремонт гаджета в майстерні: вартість + гарантійний збір 5 %."""

    __slots__ = ()
    TIER = "Гаджети"
    WARRANTY_RATE = Decimal("0.05")

    def total_price(self) -> float:
        price = Decimal(str(self.price))
        return _money(price * (1 + self.WARRANTY_RATE))


class ApplianceRepair(Repair):
    """Ремонт побутової техніки: вартість + виклик майстра 200 грн + 20 грн за кожен день."""

    __slots__ = ()
    TIER = "Побутова техніка"
    CALL_OUT_FEE = Decimal("200")
    PER_DAY_FEE = Decimal("20")

    def total_price(self) -> float:
        price = Decimal(str(self.price))
        return _money(price + self.CALL_OUT_FEE + self.PER_DAY_FEE * self.days)


def create_repair(
    ticket: int, client: str, device: str, received: date, completed: date, price: float
) -> Repair:
    """Фабрика: єдине місце, де вибирається підтип (за типом пристрою)."""
    kind = (
        ApplianceRepair if " ".join(str(device).split()).casefold() in APPLIANCES else GadgetRepair
    )
    return kind(ticket, client, device, received, completed, price)


@runtime_checkable
class Priced(Protocol):
    """Контракт для обчислення виторгу: тривалість, рівень і ціна з надбавками."""

    @property
    def days(self) -> int: ...

    @property
    def tier(self) -> str: ...

    def total_price(self) -> float: ...


@dataclass(frozen=True)
class Workload:
    """Завантаження майстерні: ремонти в роботі серед усіх квитанцій."""

    in_work: int
    total: int

    @property
    def percent(self) -> float:
        """Частка у відсотках (0.0 для порожнього набору)."""
        return 100.0 * self.in_work / self.total if self.total else 0.0


@dataclass(frozen=True)
class ReportSummary:
    """Незмінний підсумок звіту; будує analysis.build_report, читає reporting."""

    reference_date: date
    count: int
    in_work: tuple[Repair, ...]
    workload: Workload
    count_by_device: tuple[tuple[str, int], ...]
    clients: tuple[str, ...]
    longest: Repair | None
    total_days: int
    total_price: float
