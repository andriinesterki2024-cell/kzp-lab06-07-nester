"""Детермінований текст звіту та безпечний запис файла через контекстний менеджер."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import TracebackType
from typing import IO

from kzp_lab06.analysis import revenue_by_tier, total_revenue
from kzp_lab06.models import Repair, ReportSummary


def format_report(summary: ReportSummary) -> str:
    """Повертає текст звіту — побайтово той самий, що й у ЛР6."""
    load = summary.workload
    lines = [
        "Звіт ремонтної майстерні",
        f"Дата відбору: {summary.reference_date.isoformat()}",
        f"Записів у файлі: {summary.count}",
        "",
        f"В роботі на дату ({len(summary.in_work)}):",
    ]
    lines += [f"  {repair}" for repair in summary.in_work] or ["  немає"]
    lines.append(f"Завантаження майстерні: {load.in_work} з {load.total} ({load.percent:.2f}%)")
    lines += ["", "Ремонти за типом пристрою:"]
    lines += [f"  {device}: {n}" for device, n in summary.count_by_device] or ["  немає"]
    lines += ["", f"Клієнти без повторів ({len(summary.clients)}):"]
    lines += [f"  {client}" for client in summary.clients] or ["  немає"]
    lines.append("")
    longest = summary.longest
    if longest is None:
        lines.append("Найдовший ремонт: немає")
    else:
        lines.append(
            f"Найдовший ремонт: квитанція {longest.ticket}, {longest.client}, "
            f"{longest.device}, {longest.days} дн."
        )
    lines.append(f"Сумарна тривалість ремонтів: {summary.total_days} дн.")
    lines.append(f"Загальний виторг: {summary.total_price:.2f} грн")
    return "\n".join(lines) + "\n"


def format_details(repairs: list[Repair]) -> str:
    """Додатковий блок (--details): ціни з надбавками за рівнями обслуговування."""
    lines = ["Ціни з надбавками за рівнями:"]
    lines += [f"  {tier}: {amount:.2f} грн" for tier, amount in revenue_by_tier(repairs).items()]
    lines.append(f"  Разом: {total_revenue(repairs):.2f} грн")
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
