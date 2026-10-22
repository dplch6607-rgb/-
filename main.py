"""Точка входа: «Мастерская электроники» — учёт инвентаря, выдач и очереди заявок.

Запуск:  python main.py [--import data/items.csv] [--state data/state.json]
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence

from workshop.exceptions import StorageError
from workshop.models import Workshop
from workshop.storage import import_items, load_state, save_state
from workshop.ui import ConsoleUI

BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger("workshop.main")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Мастерская электроники: учёт инвентаря, выдач и заявок")
    parser.add_argument("--state", type=Path, default=BASE_DIR / "data" / "state.json",
                        help="файл состояния (JSON); создаётся при первой правке")
    parser.add_argument("--report", type=Path, default=BASE_DIR / "data" / "report.json",
                        help="куда сохранять отчёт (JSON)")
    parser.add_argument("--csv", type=Path, default=BASE_DIR / "data" / "items.csv",
                        help="каталог по умолчанию для импорта")
    parser.add_argument("--import", dest="import_csv", type=Path, metavar="CSV",
                        help="импортировать каталог из CSV перед запуском меню")
    parser.add_argument("--log", type=Path, default=BASE_DIR / "logs" / "workshop.log",
                        help="файл журнала")
    return parser.parse_args(argv)


def setup_logging(log_path: Path) -> None:
    """Журнал событий и ошибок — в файл (консоль занята меню)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    setup_logging(args.log)
    logger.info("Запуск приложения")

    try:
        workshop = load_state(args.state) if args.state.exists() else Workshop()
    except StorageError as exc:
        logger.error("Состояние не загружено: %s", exc)
        print(f"Не удалось загрузить состояние: {exc}", file=sys.stderr)
        print("Исправьте файл или удалите его, чтобы начать с чистого склада.", file=sys.stderr)
        return 1

    if args.import_csv:
        try:
            result = import_items(workshop, args.import_csv)
            save_state(workshop, args.state)
        except StorageError as exc:
            logger.error("Импорт не выполнен: %s", exc)
            print(f"Импорт не выполнен: {exc}", file=sys.stderr)
            return 1
        print(f"Импортировано: {result.imported}, отклонено строк: {len(result.rejected)}")

    ui = ConsoleUI(workshop, args.state, args.report, args.csv)
    try:
        ui.run()
    except Exception:
        logger.exception("Непредвиденная ошибка")  # записываем и пробрасываем дальше, не скрывая
        raise
    logger.info("Приложение завершено")
    return 0


if __name__ == "__main__":
    sys.exit(main())
