"""Хранение данных: импорт каталога из CSV и сохранение/загрузка состояния и отчёта в JSON.

Импорт устроен как конвейер из генераторов:

    чтение строк → проверка → преобразование типов → создание предмета → добавление на склад

Каждая стадия берёт по одной записи у предыдущей, поэтому файл никогда не лежит в памяти
целиком: можно импортировать каталог на миллион строк с тем же расходом памяти, что и на десять.
"""
from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Union

from .exceptions import StorageError, WorkshopError
from .models import Workshop, item_from_dict

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("sku", "name", "category", "kind", "quantity", "min_stock", "unit")
PathLike = Union[str, Path]


@dataclass
class ImportResult:
    """Итог импорта: сколько предметов добавлено и какие строки отклонены (с причинами)."""

    imported: int = 0
    rejected: list[str] = field(default_factory=list)

    def reject(self, line_no: int, reason: str) -> None:
        """Записать отклонённую строку в итог и в журнал — молча проглатывать ошибки нельзя."""
        message = f"строка {line_no}: {reason}"
        self.rejected.append(message)
        logger.warning("Импорт CSV: %s", message)


# --------------------------------------------------------------------------- CSV

def read_csv_rows(path: PathLike) -> Iterator[tuple[int, dict[str, Optional[str]]]]:
    """Генератор: отдаёт пары (номер строки в файле, словарь полей) по одной.

    Ошибки файла (нет файла, нет нужных столбцов, нечитаемая кодировка) превращаются в
    StorageError. Так как это генератор, они возникают при первом обращении к нему.
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
            if missing:
                raise StorageError(
                    f"В {path} нет обязательных столбцов: {', '.join(missing)} "
                    f"(файл пустой или без строки заголовков)"
                )
            for row in reader:
                yield reader.line_num, row
    except FileNotFoundError as exc:
        raise StorageError(f"Файл не найден: {path}") from exc
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise StorageError(f"Не удалось прочитать {path}: {exc}") from exc


def _check_row(row: dict[str, Optional[str]]) -> Optional[str]:
    """Проверить структуру строки. Вернуть описание проблемы или None, если строка годится."""
    if None in row:
        return "в строке больше значений, чем столбцов"
    missing = [column for column in REQUIRED_COLUMNS if row.get(column) is None]
    if missing:
        return f"не хватает значений: {', '.join(missing)}"
    kind = row["kind"].strip().lower()  # type: ignore[union-attr]
    if kind not in ("tool", "consumable"):
        return f"неизвестный тип предмета {row['kind']!r} (ожидается tool или consumable)"
    to_check = ["quantity"] + (["min_stock"] if kind == "consumable" else [])
    for column in to_check:
        raw = row[column].strip()  # type: ignore[union-attr]
        if column == "min_stock" and raw == "":
            continue  # пустой минимум = 0
        try:
            int(raw)
        except ValueError:
            return f"столбец {column}: {raw!r} — не целое число"
    return None


def _validate_rows(
    rows: Iterator[tuple[int, dict[str, Optional[str]]]], result: ImportResult
) -> Iterator[tuple[int, dict[str, Optional[str]]]]:
    """Стадия «проверка»: пропускает дальше только структурно корректные строки."""
    for line_no, row in rows:
        problem = _check_row(row)
        if problem:
            result.reject(line_no, problem)
        else:
            yield line_no, row


def _transform_rows(
    rows: Iterator[tuple[int, dict[str, Optional[str]]]]
) -> Iterator[tuple[int, dict[str, Any]]]:
    """Стадия «преобразование»: строки CSV → словари с числами в формате item_from_dict."""
    for line_no, row in rows:
        kind = row["kind"].strip().lower()  # type: ignore[union-attr]
        data: dict[str, Any] = {
            "kind": kind,
            "sku": row["sku"],
            "name": row["name"],
            "category": row["category"],
        }
        quantity = int(row["quantity"])  # type: ignore[arg-type]
        if kind == "tool":
            data["total"] = quantity
        else:
            min_stock = (row["min_stock"] or "").strip()
            data["quantity"] = quantity
            data["min_stock"] = int(min_stock) if min_stock else 0
            data["unit"] = (row["unit"] or "").strip() or "шт"
        yield line_no, data


def import_items(workshop: Workshop, path: PathLike) -> ImportResult:
    """Импортировать каталог из CSV на склад.

    Плохие строки отклоняются поодиночке: причина попадает в ImportResult и в журнал.
    Если файл не читается посреди импорта (StorageError), уже добавленные предметы
    откатываются, чтобы склад не остался в «половинчатом» состоянии.
    """
    result = ImportResult()
    added: list[str] = []
    try:
        rows = read_csv_rows(path)
        for line_no, data in _transform_rows(_validate_rows(rows, result)):
            try:
                item = item_from_dict(data)  # property-проверки: артикул, количества, длины
                workshop.add_item(item)  # DuplicateItemError — повтор артикула
            except WorkshopError as exc:
                result.reject(line_no, str(exc))
            else:
                added.append(item.sku)
                result.imported += 1
    except StorageError:
        for sku in added:
            workshop.remove_item(sku)
        logger.error("Импорт %s прерван, добавленные предметы (%d) откатаны", path, len(added))
        raise
    logger.info("Импорт %s: добавлено %d, отклонено %d", path, result.imported, len(result.rejected))
    return result


# --------------------------------------------------------------------------- JSON

def _write_json_atomically(path: PathLike, data: Any) -> None:
    """Записать JSON во временный файл и переименовать: при сбое старый файл останется целым."""
    target = Path(path)
    temp = target.with_name(target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp, target)
    except (OSError, TypeError) as exc:
        logger.error("Не удалось записать %s: %s", target, exc)
        raise StorageError(f"Не удалось записать {target}: {exc}") from exc


def save_state(workshop: Workshop, path: PathLike) -> None:
    """Сохранить полное состояние мастерской (предметы, выдачи, очередь)."""
    _write_json_atomically(path, workshop.to_dict())
    logger.info("Состояние сохранено: %s", path)


def load_state(path: PathLike, today: Callable[[], date] = date.today) -> Workshop:
    """Загрузить состояние. Повреждённый файл → StorageError (без «тихого» продолжения)."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise StorageError(f"Файл состояния не найден: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StorageError(f"Файл {path} повреждён (это не корректный JSON): {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise StorageError(f"Не удалось прочитать {path}: {exc}") from exc
    try:
        workshop = Workshop.from_dict(data, today)
    except WorkshopError as exc:
        raise StorageError(f"Файл {path} содержит некорректные данные: {exc}") from exc
    logger.info("Состояние загружено: %s (предметов: %d)", path, len(workshop.inventory))
    return workshop


def save_report(report: dict[str, Any], path: PathLike) -> None:
    """Сохранить итоговый отчёт в JSON."""
    _write_json_atomically(path, report)
    logger.info("Отчёт сохранён: %s", path)
