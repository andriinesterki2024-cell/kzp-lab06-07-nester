"""Формування детермінованого тексту звіту та запис файла."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from legacy_v6.loader import Record

#: Підписи станів для звіту.
STATUS_LABELS = {"new": "нова", "in_progress": "у роботі", "done": "виконана"}


def format_record(record: Record) -> str:
    """Рядок звіту для однієї заявки."""
    return (
        f"{record['date'].isoformat()} | {record['customer']} | {record['device']} | "
        f"{record['fault']} | {record['cost']:.2f} грн | {STATUS_LABELS[record['status']]}"
    )


def format_report(report: dict[str, Any]) -> str:
    """Повертає текст звіту; однакові дані завжди дають однаковий текст.

    Порядок: відкриті заявки — за датою, потім клієнтом; несправності й пристрої — за
    українським алфавітом; числа мають два знаки після крапки.
    """
    lines = [
        "Звіт ремонтної майстерні",
        f"Заявок у файлі: {report['count']}",
        "",
        f"Відкриті заявки (status != done): {len(report['open_orders'])}",
    ]
    lines += [f"  {format_record(record)}" for record in report["open_orders"]] or ["  немає"]
    lines.append(f"Вартість відкритих заявок: {report['open_cost']:.2f} грн")
    lines += ["", "Вартість за несправністю:"]
    lines += [f"  {fault}: {cost:.2f} грн" for fault, cost in report["cost_by_fault"].items()] or [
        "  немає"
    ]
    lines += ["", f"Пристрої ({len(report['devices'])}):"]
    lines += [f"  {device}" for device in report["devices"]] or ["  немає"]
    lines.append("")
    best = report["most_expensive"]
    if best is None:
        lines.append("Найдорожчий ремонт: немає")
    else:
        lines.append(f"Найдорожчий ремонт: {format_record(best)}")
    lines.append(f"Загальна вартість заявок: {report['total_cost']:.2f} грн")
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
