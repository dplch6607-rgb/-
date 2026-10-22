"""Тесты интерфейса: сеанс «проигрывается» по списку введённых строк."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from workshop.models import Consumable, ReusableTool, Workshop
from workshop.storage import load_state
from workshop.ui import ConsoleUI

TODAY = date(2026, 10, 22)


class ScriptedSession:
    """Подставляет заранее заданные ответы вместо input() и собирает вывод."""

    def __init__(self, answers):
        self._answers = iter(answers)
        self.output: list[str] = []

    def input(self, prompt: str) -> str:
        self.output.append(prompt)
        try:
            return next(self._answers)
        except StopIteration:
            raise EOFError from None

    def print(self, text: str = "") -> None:
        self.output.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self.output)


class ConsoleUITests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.state = self.dir / "state.json"
        self.report = self.dir / "report.json"
        self.workshop = Workshop(today=lambda: TODAY)
        self.workshop.add_item(ReusableTool("SLD-001", "Паяльная станция", "Пайка", 2))
        self.workshop.add_item(Consumable("RES-010", "Резистор 10 кОм", "Компоненты", 100, 50))

    def play(self, answers) -> ScriptedSession:
        session = ScriptedSession(answers)
        ConsoleUI(self.workshop, self.state, self.report, self.dir / "items.csv",
                  input_fn=session.input, output_fn=session.print).run()
        return session

    def test_exit(self):
        """Пункт 0 завершает работу."""
        self.assertIn("До свидания", self.play(["0"]).text)

    def test_unknown_menu_item(self):
        """Неизвестный пункт меню ('99', 'abc', пустая строка) → подсказка, программа продолжает работать."""
        session = self.play(["99", "abc", "", "0"])
        self.assertEqual(session.text.count("Нет пункта меню"), 3)
        self.assertIn("До свидания", session.text)

    def test_eof_ends_gracefully(self):
        """Конец ввода (Ctrl+D) → аккуратное завершение, без traceback."""
        self.assertIn("Ввод прерван", self.play(["1"]).text)

    def test_non_numeric_quantity_is_asked_again(self):
        """Количество 'пять', '0', '-3' → три сообщения об ошибке, затем '1' принято и выдача сделана."""
        session = self.play(["6", "SLD-001", "Алия", "пять", "0", "-3", "1", "0"])
        self.assertIn("Нужно целое число, а введено 'пять'", session.text)
        self.assertEqual(session.text.count("Число не может быть меньше 1"), 2)
        self.assertIn("Выдано (выдача №1)", session.text)

    def test_unknown_sku_reports_error_and_continues(self):
        """Выдача несуществующего артикула → 'Ошибка: …', склад не тронут, меню продолжает работу."""
        session = self.play(["6", "ZZZ-999", "Алия", "1", "0"])
        self.assertIn("Ошибка: Предмета с артикулом 'ZZZ-999' нет на складе", session.text)
        self.assertEqual(self.workshop.active_loans(), [])
        self.assertIn("До свидания", session.text)

    def test_add_item_validates_each_field_and_saves(self):
        """Добавление: плохой артикул 'abc' и пустое название → повторный запрос; затем предмет сохранён в JSON."""
        session = self.play(["3", "2", "abc", "led-007", "  ", "Светодиод жёлтый", "компоненты", "-1", "80", "20", "", "шт", "0"])
        self.assertIn("Артикул 'ABC' не подходит", session.text)
        self.assertIn("Название: значение не может быть пустым", session.text)
        restored = load_state(self.state, today=lambda: TODAY)
        item = restored.inventory.get("LED-007")
        self.assertEqual((item.name, item.category, item.quantity, item.min_stock), ("Светодиод жёлтый", "Компоненты", 80, 20))

    def test_add_duplicate_sku(self):
        """Добавление существующего артикула → ошибка сразу после ввода артикула."""
        session = self.play(["3", "1", "sld-001", "0"])
        self.assertIn("Ошибка: Артикул SLD-001 уже есть на складе", session.text)

    def test_queue_flow(self):
        """Выдать всё → встать в очередь → принять возврат → ожидающий получает предмет."""
        session = self.play(["6", "SLD-001", "Алия", "2",
                             "6", "SLD-001", "Дамир", "1",
                             "7", "1",
                             "9", "0"])
        self.assertIn("заявка поставлена в очередь, позиция 1", session.text)
        self.assertIn("из очереди выдано: Дамир получил «Паяльная станция» ×1", session.text)
        self.assertEqual(self.workshop.waitlist(), [])

    def test_search_modes(self):
        """Поиск по началу названия находит предмет и называет алгоритм; пустой результат → 'Ничего нет'."""
        session = self.play(["2", "2", "пая", "2", "2", "яя", "0"])
        self.assertIn("бинарный поиск", session.text)
        self.assertIn("SLD-001", session.text)
        self.assertIn("Ничего нет.", session.text)

    def test_sorting_menu(self):
        """Сортировка по остатку по убыванию → расходник (100) раньше инструмента (2)."""
        session = self.play(["1", "4", "д", "0"])
        listing = session.text
        self.assertLess(listing.index("RES-010"), listing.index("SLD-001"))

    def test_remove_cancelled_and_invalid_confirmation(self):
        """Подтверждение удаления: 'может быть' → повторный вопрос, 'н' → отмена, предмет остался."""
        session = self.play(["5", "SLD-001", "может быть", "н", "0"])
        self.assertIn("Ответьте «д» или «н»", session.text)
        self.assertIn("Отменено.", session.text)
        self.assertIn("SLD-001", self.workshop.inventory)

    def test_report_written_to_json(self):
        """Пункт 10 печатает отчёт и записывает report.json."""
        session = self.play(["10", "0"])
        self.assertIn("Требует внимания", session.text)
        data = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(data["totals"]["positions"], 2)

    def test_import_missing_file_reports_error(self):
        """Импорт несуществующего файла → 'Ошибка: Файл не найден', меню продолжает работу."""
        session = self.play(["11", str(self.dir / "нет.csv"), "0"])
        self.assertIn("Ошибка: Файл не найден", session.text)
        self.assertIn("До свидания", session.text)


if __name__ == "__main__":
    unittest.main()
