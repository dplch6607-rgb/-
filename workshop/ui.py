"""Консольный интерфейс: меню, ввод с проверкой, вывод таблиц и отчёта.

Ввод и вывод передаются в конструктор (``input_fn``/``output_fn``), поэтому тесты могут
«проиграть» сеанс по списку строк, не трогая настоящую клавиатуру.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from .exceptions import DuplicateItemError, ValidationError, WorkshopError
from .models import (
    Consumable,
    Item,
    Loan,
    LoanRequest,
    ReusableTool,
    Workshop,
    normalize_category,
    normalize_name,
    normalize_sku,
    normalize_unit,
)
from .storage import import_items, save_report, save_state

logger = logging.getLogger(__name__)

MENU = """
=== Мастерская электроники ===
 1. Показать склад (с сортировкой)
 2. Поиск
 3. Добавить предмет
 4. Изменить название или категорию
 5. Удалить предмет
 6. Выдать предмет (или встать в очередь)
 7. Принять возврат
 8. Пополнить запас
 9. Выдачи и очередь
10. Отчёт (на экран и в JSON)
11. Импорт каталога из CSV
 0. Выход
"""

SEARCH_MODES = {
    "1": ("sku", "по артикулу — словарь, O(1)"),
    "2": ("prefix", "по началу названия — бинарный поиск, O(log n + k)"),
    "3": ("contains", "по части названия — линейный поиск, O(n)"),
    "4": ("category", "по категории — линейный поиск, O(n)"),
}
SORT_CHOICES = {"1": "sku", "2": "name", "3": "category", "4": "on_hand"}
YES = {"д", "да", "y", "yes"}
NO = {"н", "нет", "n", "no"}


class ConsoleUI:
    """Меню поверх Workshop. После каждой успешной правки состояние сохраняется в JSON."""

    def __init__(
        self,
        workshop: Workshop,
        state_path: Path,
        report_path: Path,
        default_csv: Path,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> None:
        self._workshop = workshop
        self._state_path = state_path
        self._report_path = report_path
        self._default_csv = default_csv
        self._input = input_fn
        self._out = output_fn
        # пункт меню → (обработчик, меняет ли он данные и нужно ли сохранение)
        self._commands: dict[str, tuple[Callable[[], None], bool]] = {
            "1": (self._show_items, False),
            "2": (self._search, False),
            "3": (self._add_item, True),
            "4": (self._update_item, True),
            "5": (self._remove_item, True),
            "6": (self._issue, True),
            "7": (self._return, True),
            "8": (self._restock, True),
            "9": (self._loans_and_queue, False),
            "10": (self._report, False),
            "11": (self._import, True),
        }

    # ----- главный цикл

    def run(self) -> None:
        if len(self._workshop.inventory) == 0:
            self._out(f"Склад пуст. Пункт 11 загрузит каталог из {self._default_csv}.")
        while True:
            try:
                self._out(MENU)
                choice = self._input("Ваш выбор: ").strip()
                if choice == "0":
                    self._out("До свидания! Данные сохраняются автоматически после каждой правки.")
                    return
                self._run_command(choice)
            except (EOFError, KeyboardInterrupt):
                self._out("\nВвод прерван, завершаю работу.")
                return

    def _run_command(self, choice: str) -> None:
        entry = self._commands.get(choice)
        if entry is None:
            self._out(f"Нет пункта меню {choice!r}. Введите число от 0 до 11.")
            return
        handler, changes_data = entry
        try:
            handler()
            if changes_data:
                save_state(self._workshop, self._state_path)
        except WorkshopError as exc:  # ожидаемые ошибки предметной области и хранения
            logger.warning("Пункт меню %s: %s", choice, exc)
            self._out(f"Ошибка: {exc}")

    # ----- ввод с проверкой на границе приложения

    def _ask_text(self, prompt: str) -> str:
        while True:
            value = self._input(prompt).strip()
            if value:
                return value
            self._out("Значение не может быть пустым, повторите ввод.")

    def _ask_int(self, prompt: str, minimum: int = 1) -> int:
        while True:
            raw = self._input(prompt).strip()
            try:
                value = int(raw)
            except ValueError:
                self._out(f"Нужно целое число, а введено {raw!r}. Повторите.")
                continue
            if value < minimum:
                self._out(f"Число не может быть меньше {minimum}. Повторите.")
                continue
            return value

    def _ask_validated(self, prompt: str, validator: Callable[[Any], str]) -> str:
        """Спрашивать, пока validator (normalize_*) не примет значение."""
        while True:
            try:
                return validator(self._input(prompt))
            except ValidationError as exc:
                self._out(f"Ошибка: {exc}")

    def _ask_optional(self, prompt: str, validator: Callable[[Any], str]) -> Optional[str]:
        """Пустой ввод = «не менять»."""
        while True:
            raw = self._input(prompt)
            if not raw.strip():
                return None
            try:
                return validator(raw)
            except ValidationError as exc:
                self._out(f"Ошибка: {exc}")

    def _ask_choice(self, prompt: str, options: Sequence[str]) -> str:
        while True:
            choice = self._input(prompt).strip()
            if choice in options:
                return choice
            self._out(f"Выберите один из вариантов: {', '.join(options)}.")

    def _confirm(self, prompt: str) -> bool:
        while True:
            answer = self._input(prompt).strip().lower()
            if answer in YES:
                return True
            if answer in NO:
                return False
            self._out("Ответьте «д» или «н».")

    # ----- вывод

    def _print_items(self, items: Sequence[Item]) -> None:
        if not items:
            self._out("Ничего нет.")
            return
        for item in items:
            self._out(item.describe())
        self._out(f"Позиций: {len(items)}")

    @staticmethod
    def _loan_line(loan: Loan, item_name: str) -> str:
        return f"№{loan.loan_id:<3} {loan.sku}  {item_name} ×{loan.quantity} — {loan.borrower}, с {loan.issued_on.isoformat()}"

    def _print_served(self, served: Sequence[Loan]) -> None:
        for loan in served:
            name = self._workshop.inventory.get(loan.sku).name
            self._out(f"  → из очереди выдано: {loan.borrower} получил «{name}» ×{loan.quantity} (выдача №{loan.loan_id})")

    # ----- команды меню

    def _show_items(self) -> None:
        self._out("Сортировать по: 1 — артикул, 2 — название, 3 — категория, 4 — остаток")
        field = SORT_CHOICES[self._ask_choice("Номер: ", list(SORT_CHOICES))]
        descending = self._confirm("По убыванию? (д/н): ")
        self._print_items(self._workshop.inventory.sorted_by(field, reverse=descending))

    def _search(self) -> None:
        for key, (_, label) in SEARCH_MODES.items():
            self._out(f"  {key} — {label}")
        mode, label = SEARCH_MODES[self._ask_choice("Способ поиска: ", list(SEARCH_MODES))]
        query = self._ask_text("Запрос: ")
        self._out(f"[{label}]")
        self._print_items(self._workshop.inventory.search(mode, query))

    def _add_item(self) -> None:
        self._out("Тип предмета: 1 — инструмент (возвращают), 2 — расходник (списывается)")
        kind = self._ask_choice("Номер: ", ["1", "2"])
        sku = self._ask_validated("Артикул (например SLD-005): ", normalize_sku)
        if sku in self._workshop.inventory:
            raise DuplicateItemError(f"Артикул {sku} уже есть на складе")
        name = self._ask_validated("Название: ", normalize_name)
        category = self._ask_validated("Категория: ", normalize_category)
        item: Item
        if kind == "1":
            total = self._ask_int("Сколько всего штук: ", minimum=1)
            item = ReusableTool(sku, name, category, total)
        else:
            quantity = self._ask_int("Количество на складе: ", minimum=0)
            min_stock = self._ask_int("Минимальный запас: ", minimum=0)
            unit = self._ask_validated("Единица измерения (шт, г, м…): ", normalize_unit)
            item = Consumable(sku, name, category, quantity, min_stock, unit)
        self._workshop.add_item(item)
        self._out(f"Добавлено: {item.describe()}")

    def _update_item(self) -> None:
        item = self._workshop.inventory.get(self._ask_text("Артикул: "))
        self._out(f"Сейчас: {item.describe()}")
        name = self._ask_optional("Новое название (пусто — оставить): ", normalize_name)
        category = self._ask_optional("Новая категория (пусто — оставить): ", normalize_category)
        if name is None and category is None:
            self._out("Ничего не изменено.")
            return
        updated = self._workshop.update_item(item.sku, name, category)
        self._out(f"Теперь: {updated.describe()}")

    def _remove_item(self) -> None:
        item = self._workshop.inventory.get(self._ask_text("Артикул: "))
        if not self._confirm(f"Удалить «{item.name}»? (д/н): "):
            self._out("Отменено.")
            return
        self._workshop.remove_item(item.sku)
        self._out("Удалено.")

    def _issue(self) -> None:
        sku = self._ask_text("Артикул: ")
        borrower = self._ask_text("Кому выдать: ")
        quantity = self._ask_int("Сколько: ", minimum=1)
        result = self._workshop.request_item(sku, borrower, quantity)
        if isinstance(result, Loan):
            self._out(f"Выдано (выдача №{result.loan_id}).")
        else:
            position = len(self._workshop.waitlist_for(result.sku))
            self._out(f"Сейчас нет в нужном количестве — заявка поставлена в очередь, позиция {position}.")

    def _return(self) -> None:
        active = self._workshop.active_loans()
        if not active:
            self._out("Невозвращённых выдач нет.")
            return
        for loan in active:
            self._out(self._loan_line(loan, self._workshop.inventory.get(loan.sku).name))
        loan_id = self._ask_int("Номер выдачи для возврата: ", minimum=1)
        loan, served = self._workshop.return_loan(loan_id)
        self._out(f"Возврат принят: выдача №{loan.loan_id}.")
        self._print_served(served)

    def _restock(self) -> None:
        sku = self._ask_text("Артикул: ")
        amount = self._ask_int("На сколько пополнить: ", minimum=1)
        served = self._workshop.restock(sku, amount)
        self._out(f"Запас пополнен на {amount}.")
        self._print_served(served)
        self._out(f"Сейчас: {self._workshop.inventory.get(sku).describe()}")

    def _loans_and_queue(self) -> None:
        self._out("Сейчас на руках:")
        active = self._workshop.active_loans()
        if not active:
            self._out("  (ничего)")
        for loan in active:
            self._out("  " + self._loan_line(loan, self._workshop.inventory.get(loan.sku).name))
        self._out("Очередь заявок (по порядку):")
        queue: list[LoanRequest] = self._workshop.waitlist()
        if not queue:
            self._out("  (пусто)")
        for number, request in enumerate(queue, start=1):
            name = self._workshop.inventory.get(request.sku).name
            self._out(f"  {number}. {request.borrower} ждёт «{name}» ×{request.quantity} с {request.created_on.isoformat()}")

    def _report(self) -> None:
        report = self._workshop.build_report()
        totals = report["totals"]
        self._out(f"Отчёт на {report['generated_on']}")
        self._out(
            f"Позиций: {totals['positions']} (инструментов {totals['tools']}, расходников {totals['consumables']}); "
            f"на руках выдач: {totals['active_loans']}; заявок в очереди: {totals['waiting_requests']}"
        )
        self._out("Требует внимания:")
        if not report["needs_attention"]:
            self._out("  всё в порядке")
        for row in report["needs_attention"]:
            self._out(f"  {row['sku']} {row['name']}: {row['problem']}")
        self._out("По категориям:")
        for category, summary in report["by_category"].items():
            self._out(f"  {category}: позиций {summary['positions']}, единиц на месте {summary['units_on_hand']}")
        self._out("У кого что на руках:")
        if not report["active_loans_by_borrower"]:
            self._out("  ни у кого")
        for borrower, rows in report["active_loans_by_borrower"].items():
            things = ", ".join(f"{row['name']} ×{row['quantity']}" for row in rows)
            self._out(f"  {borrower}: {things}")
        save_report(report, self._report_path)
        self._out(f"Отчёт сохранён: {self._report_path}")

    def _import(self) -> None:
        raw = self._input(f"Путь к CSV [{self._default_csv}]: ").strip()
        result = import_items(self._workshop, raw or self._default_csv)
        self._out(f"Импортировано предметов: {result.imported}")
        if result.rejected:
            self._out(f"Отклонено строк: {len(result.rejected)} (подробности в logs/workshop.log)")
            for message in result.rejected[:10]:
                self._out(f"  - {message}")
            if len(result.rejected) > 10:
                self._out(f"  … и ещё {len(result.rejected) - 10}")
