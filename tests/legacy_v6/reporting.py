"""Формування детермінованого тексту звіту та запис файла."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from legacy_v6.loader import Record


def format_record(record: Record) -> str:
    """Рядок звіту для одного ремонту."""
    return (
        f"{record['ticket']} | {record['client']} | {record['device']} | "
        f"{record['received'].isoformat()}..{record['completed'].isoformat()}"
    )


def format_report(report: dict[str, Any]) -> str:
    """Повертає текст звіту; однакові дані завжди дають однаковий текст.

    Порядок: ремонти в роботі — за квитанцією, типи пристроїв і клієнти — за українським
    алфавітом; числа мають два знаки після крапки.
    """
    load = report["workload"]
    lines = [
        "Звіт ремонтної майстерні",
        f"Дата відбору: {report['reference_date'].isoformat()}",
        f"Записів у файлі: {report['count']}",
        "",
        f"В роботі на дату ({len(report['in_work'])}):",
    ]
    lines += [f"  {format_record(record)}" for record in report["in_work"]] or ["  немає"]
    lines.append(
        f"Завантаження майстерні: {load['in_work']} з {load['total']} ({load['percent']:.2f}%)"
    )
    lines += ["", "Ремонти за типом пристрою:"]
    lines += [f"  {device}: {n}" for device, n in report["count_by_device"].items()] or ["  немає"]
    lines += ["", f"Клієнти без повторів ({len(report['clients'])}):"]
    lines += [f"  {client}" for client in report["clients"]] or ["  немає"]
    lines.append("")
    longest = report["longest"]
    if longest is None:
        lines.append("Найдовший ремонт: немає")
    else:
        lines.append(
            f"Найдовший ремонт: квитанція {longest['ticket']}, {longest['client']}, "
            f"{longest['device']}, {longest['days']} дн."
        )
    lines.append(f"Сумарна тривалість ремонтів: {report['total_days']} дн.")
    lines.append(f"Загальний виторг: {report['total_price']:.2f} грн")
    return "\n".join(lines) + "\n"


def write_report(path: Path, text: str) -> None:
    """Записує звіт у UTF-8 з роздільником LF (побайтово однаково на всіх ОС).

    Raises:
        OSError: файл неможливо записати (обробляє CLI).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # with гарантує закриття файла навіть у разі помилки запису.
    with path.open("w", encoding="utf-8", newline="\n") as target:
        target.write(text)
