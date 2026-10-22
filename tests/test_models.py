"""Тесты модели: проверки полей, полиморфизм, склад, выдачи, очередь, отчёт, сериализация."""
import unittest
from datetime import date

from workshop.exceptions import (
    DuplicateItemError,
    InsufficientStockError,
    ItemInUseError,
    ItemNotFoundError,
    LoanNotFoundError,
    ValidationError,
)
from workshop.models import (
    Consumable,
    Inventory,
    Item,
    Loan,
    LoanRequest,
    ReusableTool,
    Workshop,
    item_from_dict,
    normalize_sku,
)

TODAY = date(2026, 10, 22)


def make_workshop() -> Workshop:
    workshop = Workshop(today=lambda: TODAY)
    workshop.add_item(ReusableTool("SLD-001", "Паяльная станция", "Пайка", 2))
    workshop.add_item(ReusableTool("MTR-001", "Мультиметр цифровой", "Измерения", 3))
    workshop.add_item(Consumable("RES-010", "Резистор 10 кОм", "Компоненты", 100, min_stock=50))
    workshop.add_item(Consumable("SLD-010", "Припой ПОС-61", "Расходники", 20, min_stock=50, unit="г"))
    return workshop


class FieldValidationTests(unittest.TestCase):
    def test_sku_is_normalized(self):
        """Артикул в нижнем регистре с пробелами → 'SLD-001'."""
        self.assertEqual(normalize_sku("  sld-001 "), "SLD-001")

    def test_bad_sku_rejected(self):
        """Неверные артикулы ('', 'abc', 'SLD001', 'S-001', 'SLD-1', число) → ValidationError."""
        for bad in ("", "   ", "abc", "SLD001", "S-001", "SLD-1", "SLD-0001", 123):
            with self.subTest(sku=bad):
                with self.assertRaises(ValidationError):
                    normalize_sku(bad)

    def test_empty_name_rejected(self):
        """Пустое название → ValidationError."""
        with self.assertRaises(ValidationError):
            ReusableTool("SLD-001", "   ", "Пайка", 1)

    def test_category_first_letter_capitalized(self):
        """Категория 'пайка' → 'Пайка'."""
        self.assertEqual(ReusableTool("SLD-001", "Паяльник", "пайка", 1).category, "Пайка")

    def test_tool_total_must_be_positive_int(self):
        """total = 0, -1, 2.5, True, '3' → ValidationError."""
        for bad in (0, -1, 2.5, True, "3"):
            with self.subTest(total=bad):
                with self.assertRaises(ValidationError):
                    ReusableTool("SLD-001", "Паяльник", "Пайка", bad)

    def test_tool_available_cannot_exceed_total(self):
        """available > total → ValidationError; available = total допустимо."""
        with self.assertRaises(ValidationError):
            ReusableTool("SLD-001", "Паяльник", "Пайка", 2, available=3)
        self.assertEqual(ReusableTool("SLD-001", "Паяльник", "Пайка", 2, available=2).available, 2)

    def test_tool_available_setter_validates(self):
        """Прямое присваивание available = -1 → ValidationError, значение не меняется."""
        tool = ReusableTool("SLD-001", "Паяльник", "Пайка", 2)
        with self.assertRaises(ValidationError):
            tool.available = -1
        self.assertEqual(tool.available, 2)

    def test_consumable_negative_values_rejected(self):
        """Отрицательные quantity и min_stock → ValidationError."""
        with self.assertRaises(ValidationError):
            Consumable("RES-010", "Резистор", "Компоненты", -1)
        with self.assertRaises(ValidationError):
            Consumable("RES-010", "Резистор", "Компоненты", 5, min_stock=-1)

    def test_sku_is_read_only(self):
        """Артикул нельзя присвоить напрямую (property без setter) → AttributeError."""
        tool = ReusableTool("SLD-001", "Паяльник", "Пайка", 1)
        with self.assertRaises(AttributeError):
            tool.sku = "NEW-001"


class PolymorphismTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            ReusableTool("SLD-001", "Паяльная станция", "Пайка", 3),
            Consumable("RES-010", "Резистор 10 кОм", "Компоненты", 100, min_stock=20),
        ]

    def test_common_interface_take_and_add_stock(self):
        """Оба типа через один интерфейс: take(2) уменьшает on_hand на 2, add_stock(5) увеличивает на 5."""
        for item in self.items:
            with self.subTest(item=item):
                self.assertIsInstance(item, Item)
                before = item.on_hand
                item.take(2)
                self.assertEqual(item.on_hand, before - 2)
                item.add_stock(5)
                self.assertEqual(item.on_hand, before + 3)

    def test_take_too_much_raises(self):
        """take больше остатка у обоих типов → InsufficientStockError."""
        for item in self.items:
            with self.subTest(item=item):
                with self.assertRaises(InsufficientStockError):
                    item.take(item.on_hand + 1)

    def test_give_back_differs_by_type(self):
        """give_back: инструмент принимается, расходник → ValidationError."""
        tool, consumable = self.items
        tool.take(1)
        tool.give_back(1)
        self.assertEqual(tool.on_hand, 3)
        with self.assertRaises(ValidationError):
            consumable.give_back(1)

    def test_tool_give_back_beyond_total_rejected(self):
        """Вернуть инструмента больше, чем выдавали → ValidationError."""
        tool = self.items[0]
        with self.assertRaises(ValidationError):
            tool.give_back(1)

    def test_needs_attention_differs_by_type(self):
        """Инструмент требует внимания при available = 0, расходник — при остатке ниже минимума."""
        tool, consumable = self.items
        self.assertIsNone(tool.needs_attention())
        self.assertIsNone(consumable.needs_attention())
        tool.take(3)
        consumable.take(81)
        self.assertIn("выданы", tool.needs_attention())
        self.assertIn("осталось 19", consumable.needs_attention())

    def test_describe_contains_sku(self):
        """describe() обоих типов содержит артикул."""
        for item in self.items:
            self.assertIn(item.sku, item.describe())

    def test_roundtrip_through_dict_factory(self):
        """to_dict → item_from_dict возвращает предмет того же типа с теми же данными."""
        for item in self.items:
            with self.subTest(item=item):
                copy = item_from_dict(item.to_dict())
                self.assertIs(type(copy), type(item))
                self.assertEqual(copy.to_dict(), item.to_dict())

    def test_factory_unknown_kind(self):
        """Неизвестный kind или отсутствующее поле → ValidationError."""
        with self.assertRaises(ValidationError):
            item_from_dict({"kind": "gadget", "sku": "ABC-123"})
        with self.assertRaises(ValidationError):
            item_from_dict({"kind": "tool", "sku": "ABC-123", "name": "X", "category": "Y"})


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.inventory = Inventory()
        for item in make_workshop().inventory:
            self.inventory.add(item)

    def test_duplicate_sku_rejected(self):
        """Повторный артикул → DuplicateItemError, склад не изменился."""
        with self.assertRaises(DuplicateItemError):
            self.inventory.add(ReusableTool("SLD-001", "Другой паяльник", "Пайка", 1))
        self.assertEqual(len(self.inventory), 4)

    def test_get_missing(self):
        """Отсутствующий артикул → ItemNotFoundError."""
        with self.assertRaises(ItemNotFoundError):
            self.inventory.get("ZZZ-999")

    def test_get_is_case_insensitive(self):
        """get('sld-001') находит SLD-001."""
        self.assertEqual(self.inventory.get(" sld-001 ").sku, "SLD-001")

    def test_categories_unique_and_sorted(self):
        """Категории: без повторов и по алфавиту."""
        self.inventory.add(ReusableTool("SLD-002", "Паяльник", "пайка", 1))
        self.assertEqual(self.inventory.categories(), ["Измерения", "Компоненты", "Пайка", "Расходники"])

    def test_empty_inventory(self):
        """Пустой склад: сортировка и все виды поиска → пустой список, без ошибок."""
        empty = Inventory()
        self.assertEqual(empty.sorted_by("name"), [])
        for mode in ("sku", "prefix", "contains", "category"):
            with self.subTest(mode=mode):
                self.assertEqual(empty.search(mode, "x"), [])

    def test_sort_each_field(self):
        """Сортировка по sku/name/category/on_hand → порядок как у встроенной сортировки."""
        for field, key in (
            ("sku", lambda i: i.sku),
            ("name", lambda i: i.name.casefold()),
            ("category", lambda i: i.category.casefold()),
            ("on_hand", lambda i: i.on_hand),
        ):
            with self.subTest(field=field):
                self.assertEqual(self.inventory.sorted_by(field), sorted(self.inventory, key=key))

    def test_sort_descending(self):
        """Сортировка по остатку по убыванию → RES-010 (100) первым."""
        self.assertEqual(self.inventory.sorted_by("on_hand", reverse=True)[0].sku, "RES-010")

    def test_sort_unknown_field(self):
        """Неизвестное поле сортировки → ValidationError."""
        with self.assertRaises(ValidationError):
            self.inventory.sorted_by("price")

    def test_search_by_sku(self):
        """Поиск по артикулу: точное совпадение, регистр не важен, нет такого → []."""
        self.assertEqual([i.sku for i in self.inventory.search("sku", "res-010")], ["RES-010"])
        self.assertEqual(self.inventory.search("sku", "nope"), [])

    def test_search_prefix_binary(self):
        """Начало названия 'пая' (любой регистр) → 'Паяльная станция'; 'Р' → резистор; 'яя' → пусто."""
        self.assertEqual([i.sku for i in self.inventory.search("prefix", "ПАЯ")], ["SLD-001"])
        self.assertEqual([i.sku for i in self.inventory.search("prefix", "р")], ["RES-010"])
        self.assertEqual(self.inventory.search("prefix", "яя"), [])

    def test_search_prefix_returns_all_with_prefix(self):
        """Несколько названий с общим началом → найдены все, в алфавитном порядке."""
        self.inventory.add(ReusableTool("MTR-002", "Мультиметр аналоговый", "Измерения", 1))
        found = [i.name for i in self.inventory.search("prefix", "мульти")]
        self.assertEqual(found, ["Мультиметр аналоговый", "Мультиметр цифровой"])

    def test_search_contains(self):
        """Часть названия 'метр' (в любом месте слова) → 'Мультиметр цифровой'."""
        self.assertEqual([i.sku for i in self.inventory.search("contains", "метр")], ["MTR-001"])

    def test_search_category(self):
        """Категория (без учёта регистра) → предметы категории."""
        self.assertEqual([i.sku for i in self.inventory.search("category", "пайка")], ["SLD-001"])

    def test_search_bad_input(self):
        """Пустой запрос и неизвестный режим → ValidationError."""
        with self.assertRaises(ValidationError):
            self.inventory.search("prefix", "   ")
        with self.assertRaises(ValidationError):
            self.inventory.search("fuzzy", "x")

    def test_update_refreshes_name_view(self):
        """После переименования префиксный поиск находит новое имя и не находит старое."""
        self.inventory.search("prefix", "пая")  # прогреваем кэш
        self.inventory.update("SLD-001", name="Термовоздушная станция")
        self.assertEqual(self.inventory.search("prefix", "пая"), [])
        self.assertEqual([i.sku for i in self.inventory.search("prefix", "термо")], ["SLD-001"])

    def test_update_is_atomic(self):
        """Некорректная категория при корректном имени → ничего не изменено."""
        with self.assertRaises(ValidationError):
            self.inventory.update("SLD-001", name="Новое имя", category="   ")
        self.assertEqual(self.inventory.get("SLD-001").name, "Паяльная станция")

    def test_remove_updates_everything(self):
        """Удаление убирает предмет из списка, индекса, поиска и пустую категорию."""
        self.inventory.search("prefix", "пая")
        self.inventory.remove("SLD-001")
        self.assertNotIn("SLD-001", self.inventory)
        self.assertEqual(self.inventory.search("prefix", "пая"), [])
        self.assertNotIn("Пайка", self.inventory.categories())


class WorkshopLoanTests(unittest.TestCase):
    def setUp(self):
        self.workshop = make_workshop()

    def test_issue_tool_reduces_available(self):
        """Выдача инструмента: available уменьшается, выдача активна, дата = сегодня."""
        loan = self.workshop.issue("SLD-001", "Алия", 1)
        self.assertEqual(self.workshop.inventory.get("SLD-001").available, 1)
        self.assertTrue(loan.is_active)
        self.assertEqual(loan.issued_on, TODAY)

    def test_issue_consumable_is_not_returnable(self):
        """Выдача расходника: остаток уменьшается, выдача сразу неактивна."""
        loan = self.workshop.issue("RES-010", "Алия", 30)
        self.assertEqual(self.workshop.inventory.get("RES-010").quantity, 70)
        self.assertFalse(loan.is_active)

    def test_issue_insufficient(self):
        """Выдать больше, чем есть → InsufficientStockError, склад и журнал не изменились."""
        with self.assertRaises(InsufficientStockError):
            self.workshop.issue("SLD-001", "Алия", 3)
        self.assertEqual(self.workshop.inventory.get("SLD-001").available, 2)
        self.assertEqual(self.workshop.active_loans(), [])

    def test_issue_bad_arguments(self):
        """Пустое имя, количество 0 или 'пять', неизвестный артикул → понятные исключения."""
        with self.assertRaises(ValidationError):
            self.workshop.issue("SLD-001", "  ", 1)
        with self.assertRaises(ValidationError):
            self.workshop.issue("SLD-001", "Алия", 0)
        with self.assertRaises(ValidationError):
            self.workshop.issue("SLD-001", "Алия", "пять")
        with self.assertRaises(ItemNotFoundError):
            self.workshop.issue("ZZZ-999", "Алия", 1)

    def test_return_restores_stock(self):
        """Возврат возвращает инструмент на склад и закрывает выдачу."""
        loan = self.workshop.issue("SLD-001", "Алия", 2)
        closed, served = self.workshop.return_loan(loan.loan_id)
        self.assertEqual(self.workshop.inventory.get("SLD-001").available, 2)
        self.assertEqual(closed.returned_on, TODAY)
        self.assertEqual(served, [])

    def test_return_twice(self):
        """Повторный возврат той же выдачи → ValidationError."""
        loan = self.workshop.issue("SLD-001", "Алия", 1)
        self.workshop.return_loan(loan.loan_id)
        with self.assertRaises(ValidationError):
            self.workshop.return_loan(loan.loan_id)

    def test_return_unknown_loan(self):
        """Несуществующий номер выдачи (в т.ч. на пустом журнале) → LoanNotFoundError."""
        with self.assertRaises(LoanNotFoundError):
            self.workshop.return_loan(99)

    def test_return_consumable_rejected(self):
        """Возврат выдачи расходника → ValidationError."""
        loan = self.workshop.issue("RES-010", "Алия", 5)
        with self.assertRaises(ValidationError):
            self.workshop.return_loan(loan.loan_id)

    def test_find_loan_by_binary_search(self):
        """Выдачи №1..5 находятся по номеру бинарным поиском."""
        for _ in range(5):
            self.workshop.issue("RES-010", "Алия", 1)
        for loan_id in range(1, 6):
            self.assertEqual(self.workshop.find_loan(loan_id).loan_id, loan_id)

    def test_remove_item_with_active_loan(self):
        """Удалить предмет с невозвращённой выдачей → ItemInUseError."""
        self.workshop.issue("SLD-001", "Алия", 1)
        with self.assertRaises(ItemInUseError):
            self.workshop.remove_item("SLD-001")

    def test_remove_item_after_return(self):
        """После возврата предмет удаляется."""
        loan = self.workshop.issue("SLD-001", "Алия", 1)
        self.workshop.return_loan(loan.loan_id)
        self.workshop.remove_item("SLD-001")
        self.assertNotIn("SLD-001", self.workshop.inventory)


class WorkshopQueueTests(unittest.TestCase):
    def setUp(self):
        self.workshop = make_workshop()

    def test_request_issues_immediately_when_available(self):
        """Предмет есть → request_item сразу возвращает Loan, очередь пуста."""
        result = self.workshop.request_item("SLD-001", "Алия", 1)
        self.assertIsInstance(result, Loan)
        self.assertEqual(self.workshop.waitlist(), [])

    def test_request_queues_when_unavailable(self):
        """Предмета нет → request_item возвращает LoanRequest, склад не меняется."""
        self.workshop.issue("SLD-001", "Алия", 2)
        result = self.workshop.request_item("SLD-001", "Дамир", 1)
        self.assertIsInstance(result, LoanRequest)
        self.assertEqual(len(self.workshop.waitlist()), 1)

    def test_impossible_request_rejected(self):
        """Заявка на инструментов больше, чем существует (3 при total=2) → ValidationError, в очередь не попадает."""
        with self.assertRaises(ValidationError):
            self.workshop.request_item("SLD-001", "Дамир", 3)
        self.assertEqual(self.workshop.waitlist(), [])

    def test_return_serves_waitlist(self):
        """Возврат инструмента сразу выдаёт его первому в очереди."""
        loan = self.workshop.issue("SLD-001", "Алия", 2)
        self.workshop.request_item("SLD-001", "Дамир", 1)
        _, served = self.workshop.return_loan(loan.loan_id)
        self.assertEqual([(l.borrower, l.quantity) for l in served], [("Дамир", 1)])
        self.assertEqual(self.workshop.waitlist(), [])

    def test_restock_serves_waitlist(self):
        """Пополнение расходника обслуживает ожидающего."""
        self.workshop.request_item("SLD-010", "Дамир", 30)  # на складе 20 г → ждёт
        served = self.workshop.restock("SLD-010", 15)
        self.assertEqual([(l.borrower, l.quantity) for l in served], [("Дамир", 30)])
        self.assertEqual(self.workshop.inventory.get("SLD-010").quantity, 5)

    def test_new_request_does_not_jump_the_queue(self):
        """Если на предмет уже есть очередь, новая заявка встаёт в конец, даже когда запас позволяет выдать."""
        self.workshop.request_item("SLD-010", "Дамир", 30)  # ждёт: на складе 20
        result = self.workshop.request_item("SLD-010", "Алия", 5)  # 5 ≤ 20, но Дамир раньше
        self.assertIsInstance(result, LoanRequest)
        self.assertEqual([r.borrower for r in self.workshop.waitlist()], ["Дамир", "Алия"])

    def test_later_small_request_does_not_overtake_earlier_big_one(self):
        """Дефект: Алия ждёт 5 шт., Дамир — 1 шт.; пополнение на 1 шт. не должно отдать его Дамиру раньше Алии."""
        workshop = Workshop(today=lambda: TODAY)
        workshop.add_item(Consumable("RES-010", "Резистор 10 кОм", "Компоненты", 0, min_stock=0))
        workshop.request_item("RES-010", "Алия", 5)
        workshop.request_item("RES-010", "Дамир", 1)
        served = workshop.restock("RES-010", 1)
        self.assertEqual(served, [])
        self.assertEqual([r.borrower for r in workshop.waitlist()], ["Алия", "Дамир"])
        served = workshop.restock("RES-010", 4)  # теперь 5 шт.: сначала Алия, потом остаток
        self.assertEqual([(l.borrower, l.quantity) for l in served], [("Алия", 5)])
        self.assertEqual([r.borrower for r in workshop.waitlist()], ["Дамир"])

    def test_queues_for_different_items_are_independent(self):
        """Заявка на один предмет не блокирует заявки на другой."""
        self.workshop.request_item("SLD-010", "Дамир", 30)  # застрянет: нужно пополнение
        loan = self.workshop.issue("SLD-001", "Алия", 2)
        self.workshop.request_item("SLD-001", "Берик", 1)
        _, served = self.workshop.return_loan(loan.loan_id)
        self.assertEqual([l.borrower for l in served], ["Берик"])
        self.assertEqual([r.borrower for r in self.workshop.waitlist()], ["Дамир"])

    def test_remove_item_with_waiting_request(self):
        """Удалить предмет, на который есть заявка → ItemInUseError."""
        self.workshop.request_item("SLD-010", "Дамир", 30)
        with self.assertRaises(ItemInUseError):
            self.workshop.remove_item("SLD-010")


class ReportAndStateTests(unittest.TestCase):
    def setUp(self):
        self.workshop = make_workshop()
        self.workshop.issue("SLD-001", "Алия", 2)
        self.workshop.issue("RES-010", "Алия", 30)
        self.workshop.request_item("SLD-001", "Дамир", 1)

    def test_report_contents(self):
        """Отчёт: что требует внимания, выдачи по людям, сводка по категориям, очередь."""
        report = self.workshop.build_report()
        problems = {row["sku"] for row in report["needs_attention"]}
        self.assertEqual(problems, {"SLD-001", "SLD-010"})  # всё выдано / ниже минимума
        self.assertEqual(report["totals"]["active_loans"], 1)
        self.assertEqual(report["totals"]["waiting_requests"], 1)
        self.assertEqual(list(report["active_loans_by_borrower"]), ["Алия"])
        self.assertEqual(report["by_category"]["Компоненты"], {"positions": 1, "units_on_hand": 70})
        self.assertEqual(report["waitlist"][0]["borrower"], "Дамир")

    def test_report_of_empty_workshop(self):
        """Отчёт пустой мастерской → нули и пустые разделы."""
        report = Workshop(today=lambda: TODAY).build_report()
        self.assertEqual(report["totals"]["positions"], 0)
        self.assertEqual(report["needs_attention"], [])
        self.assertEqual(report["by_category"], {})

    def test_state_roundtrip(self):
        """to_dict → from_dict → to_dict даёт тот же результат (включая выдачи и очередь)."""
        data = self.workshop.to_dict()
        restored = Workshop.from_dict(data, today=lambda: TODAY)
        self.assertEqual(restored.to_dict(), data)
        # и восстановленная мастерская работает: возврат выдаёт предмет ждущему
        _, served = restored.return_loan(1)
        self.assertEqual([l.borrower for l in served], ["Дамир"])

    def test_from_dict_missing_field(self):
        """В состоянии нет поля 'items' → ValidationError."""
        data = self.workshop.to_dict()
        del data["items"]
        with self.assertRaises(ValidationError):
            Workshop.from_dict(data)

    def test_from_dict_wrong_types(self):
        """Не словарь, неверная версия, 'items' = None → ValidationError."""
        good = self.workshop.to_dict()
        for bad in ([], "text", {**good, "version": 99}, {**good, "items": None}):
            with self.subTest(bad=type(bad).__name__):
                with self.assertRaises(ValidationError):
                    Workshop.from_dict(bad)

    def test_from_dict_request_for_unknown_item(self):
        """Заявка на несуществующий артикул → ValidationError."""
        data = self.workshop.to_dict()
        data["waitlist"][0]["sku"] = "ZZZ-999"
        with self.assertRaises(ValidationError):
            Workshop.from_dict(data)

    def test_from_dict_unsorted_loans_are_sorted(self):
        """Журнал выдач в файле в неверном порядке → загружается отсортированным, предупреждение в log."""
        data = self.workshop.to_dict()
        data["loans"].reverse()
        with self.assertLogs("workshop.models", level="WARNING"):
            restored = Workshop.from_dict(data, today=lambda: TODAY)
        self.assertEqual(restored.find_loan(2).sku, "RES-010")

    def test_from_dict_duplicate_loan_ids(self):
        """Повторяющиеся номера выдач → ValidationError."""
        data = self.workshop.to_dict()
        data["loans"][1]["loan_id"] = data["loans"][0]["loan_id"]
        with self.assertRaises(ValidationError):
            Workshop.from_dict(data)


if __name__ == "__main__":
    unittest.main()
