"""Детермінований текст звіту та безпечний запис файла через контекстний менеджер."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import TracebackType
from typing import IO

from kzp_lab06.analysis import fault_summaries, final_cost_by_tier, total_final_cost
from kzp_lab06.models import RepairOrder, ReportSummary


def format_report(summary: ReportSummary) -> str:
    """Повертає текст звіту — побайтово той самий, що й у ЛР6."""
    lines = [
        "Звіт ремонтної майстерні",
        f"Заявок у файлі: {summary.count}",
        "",
        f"Відкриті заявки (status != done): {len(summary.open_orders)}",
    ]
    lines += [f"  {order}" for order in summary.open_orders] or ["  немає"]
    lines.append(f"Вартість відкритих заявок: {summary.open_cost:.2f} грн")
    lines += ["", "Вартість за несправністю:"]
    lines += [f"  {fault}: {cost:.2f} грн" for fault, cost in summary.cost_by_fault] or ["  немає"]
    lines += ["", f"Пристрої ({len(summary.devices)}):"]
    lines += [f"  {device}" for device in summary.devices] or ["  немає"]
    lines.append("")
    best = summary.most_expensive
    lines.append(f"Найдорожчий ремонт: {best}" if best is not None else "Найдорожчий ремонт: немає")
    lines.append(f"Загальна вартість заявок: {summary.total_cost:.2f} грн")
    return "\n".join(lines) + "\n"


def format_details(orders: list[RepairOrder]) -> str:
    """Додатковий блок (--details): підсумок за несправностями й остаточна вартість за видом."""
    lines = ["Підсумок за несправностями (кількість, вартість, остаточна вартість):"]
    lines += [
        f"  {s.fault}: {s.count}, {s.cost:.2f} грн, {s.final_cost:.2f} грн"
        for s in fault_summaries(orders)
    ] or ["  немає"]
    lines.append("Остаточна вартість за видом:")
    lines += [f"  {tier}: {amount:.2f} грн" for tier, amount in final_cost_by_tier(orders).items()]
    lines.append(f"  Разом: {total_final_cost(orders):.2f} грн")
    return "\n".join(lines) + "\n"


class ReportWriter:
    """Контекстний менеджер безпечного запису звіту (завдання із зірочкою).

    Пише в тимчасовий файл у тому самому каталозі; за успіху атомарно замінює звіт
    (``os.replace``), за винятку закриває й видаляє тимчасовий файл. Виняток не маскується,
    а попередній звіт лишається цілим.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._temporary: Path | None = None
        self._stream: IO[str] | None = None

    def __enter__(self) -> IO[str]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(prefix=".report-", suffix=".tmp", dir=self.path.parent)
        self._temporary = Path(name)
        self._stream = os.fdopen(handle, "w", encoding="utf-8", newline="\n")
        return self._stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        assert self._stream is not None and self._temporary is not None
        self._stream.close()
        if exc_type is None:
            try:
                os.chmod(self._temporary, 0o644)  # mkstemp створює файл лише для власника
                os.replace(self._temporary, self.path)
            except OSError:
                self._temporary.unlink(missing_ok=True)
                raise
        else:
            self._temporary.unlink(missing_ok=True)
        return False

    @property
    def closed(self) -> bool:
        """Чи закрито потік (для тестів)."""
        return self._stream is None or self._stream.closed


def write_report(path: Path, text: str) -> None:
    """Записує звіт у UTF-8 з роздільником LF через ReportWriter.

    Raises:
        OSError: файл неможливо записати (обробляє CLI).
    """
    with ReportWriter(path) as target:
        target.write(text)
