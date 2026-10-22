"""Тесты хранения: CSV-конвейер (генераторы), отклонение плохих строк, JSON, повреждённые файлы."""
import inspect
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from workshop.exceptions import StorageError
from workshop.models import Consumable, ReusableTool, Workshop
from workshop.storage import (
    ImportResult,
    import_items,
    load_state,
    read_csv_rows,
    save_report,
    save_state,
)

HEADER = "sku,name,category,kind,quantity,min_stock,unit\n"
TODAY = date(2026, 10, 22)
PROJECT = Path(__file__).resolve().parent.parent


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def write(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path


class CsvImportTests(TempDirTestCase):
    def new_workshop(self) -> Workshop:
        return Workshop(today=lambda: TODAY)

    def test_reader_is_a_lazy_generator(self):
        """read_csv_rows — генератор: до первого next() файл даже не открывается."""
        generator = read_csv_rows(self.dir / "нет_такого.csv")
        self.assertTrue(inspect.isgenerator(generator))  # ошибка файла ещё не возникла
        with self.assertRaises(StorageError):
            next(generator)

    def test_reader_yields_rows_one_by_one(self):
        """Строки отдаются по одной вместе с номерами строк файла."""
        path = self.write("a.csv", HEADER + "SLD-001,Паяльник,Пайка,tool,2,,\nRES-010,Резистор,Компоненты,consumable,5,1,шт\n")
        rows = read_csv_rows(path)
        line_no, row = next(rows)
        self.assertEqual((line_no, row["sku"]), (2, "SLD-001"))
        line_no, row = next(rows)
        self.assertEqual((line_no, row["sku"]), (3, "RES-010"))
        with self.assertRaises(StopIteration):
            next(rows)

    def test_import_good_file(self):
        """Корректный data/items.csv → все 22 предмета добавлены, ничего не отклонено."""
        workshop = self.new_workshop()
        result = import_items(workshop, PROJECT / "data" / "items.csv")
        self.assertEqual((result.imported, result.rejected), (22, []))
        self.assertEqual(len(workshop.inventory), 22)
        self.assertEqual(workshop.inventory.get("SLD-001").total, 4)
        self.assertEqual(workshop.inventory.get("SLD-010").unit, "г")

    def test_import_file_with_errors(self):
        """data/items_with_errors.csv → 2 предмета добавлено, 8 строк отклонено с причинами."""
        workshop = self.new_workshop()
        with self.assertLogs("workshop.storage", level="WARNING") as logs:
            result = import_items(workshop, PROJECT / "data" / "items_with_errors.csv")
        self.assertEqual(result.imported, 2)  # KEY-001 и GLU-001
        self.assertEqual(len(result.rejected), 8)
        self.assertEqual(len(logs.records), 8)  # каждая отклонённая строка записана в журнал
        self.assertEqual(sorted(i.sku for i in workshop.inventory), ["GLU-001", "KEY-001"])
        joined = "\n".join(result.rejected)
        for fragment in ("Артикул", "не целое число", "неизвестный тип", "уже есть на складе",
                         "Название", "больше значений", "не хватает значений"):
            self.assertIn(fragment, joined)

    def test_negative_quantity_rejected_by_property(self):
        """quantity = -5 у расходника → строка отклонена проверкой в классе, в склад не попадает."""
        path = self.write("a.csv", HEADER + "RES-010,Резистор,Компоненты,consumable,-5,1,шт\n")
        workshop = self.new_workshop()
        with self.assertLogs("workshop.storage", level="WARNING"):
            result = import_items(workshop, path)
        self.assertEqual(result.imported, 0)
        self.assertEqual(len(workshop.inventory), 0)

    def test_duplicate_of_existing_item_rejected(self):
        """Артикул, который уже есть на складе, отклоняется; существующий предмет не меняется."""
        workshop = self.new_workshop()
        workshop.add_item(ReusableTool("SLD-001", "Старый паяльник", "Пайка", 1))
        path = self.write("a.csv", HEADER + "SLD-001,Новый паяльник,Пайка,tool,9,,\n")
        with self.assertLogs("workshop.storage", level="WARNING"):
            result = import_items(workshop, path)
        self.assertEqual(result.imported, 0)
        self.assertEqual(workshop.inventory.get("SLD-001").name, "Старый паяльник")

    def test_header_only_file(self):
        """Файл только с заголовком → 0 предметов, 0 отклонённых, без ошибок."""
        result = import_items(self.new_workshop(), self.write("a.csv", HEADER))
        self.assertEqual((result.imported, result.rejected), (0, []))

    def test_empty_file(self):
        """Совсем пустой файл → StorageError (нет заголовка)."""
        with self.assertRaises(StorageError):
            import_items(self.new_workshop(), self.write("a.csv", ""))

    def test_missing_columns(self):
        """В заголовке нет обязательного столбца → StorageError с его именем."""
        path = self.write("a.csv", "sku,name\nSLD-001,Паяльник\n")
        with self.assertRaises(StorageError) as caught:
            import_items(self.new_workshop(), path)
        self.assertIn("category", str(caught.exception))

    def test_missing_file(self):
        """Файла нет → StorageError, склад не изменён."""
        workshop = self.new_workshop()
        with self.assertRaises(StorageError):
            import_items(workshop, self.dir / "нет_такого.csv")
        self.assertEqual(len(workshop.inventory), 0)

    def test_bad_encoding_rolls_back(self):
        """Файл портится далеко за началом (не UTF-8, после >8 КБ корректных строк) → StorageError и откат добавленного."""
        good_rows = "".join(f"TST-{n:03d},Деталь {n},Тест,tool,1,,\n" for n in range(300))
        path = self.dir / "a.csv"
        path.write_bytes((HEADER + good_rows).encode("utf-8") + b"BAD-001,\xff\xfe\xfd,Boom,tool,1,,\n")
        workshop = self.new_workshop()
        with self.assertLogs("workshop.storage", level="ERROR") as logs:
            with self.assertRaises(StorageError):
                import_items(workshop, path)
        self.assertNotIn("(0)", logs.output[0])  # до сбоя что-то уже было добавлено и затем откатано
        self.assertEqual(len(workshop.inventory), 0)

    def test_blank_unit_and_min_stock_defaults(self):
        """Пустые min_stock и unit у расходника → 0 и 'шт'."""
        path = self.write("a.csv", HEADER + "RES-010,Резистор,Компоненты,consumable,5,,\n")
        workshop = self.new_workshop()
        import_items(workshop, path)
        item = workshop.inventory.get("RES-010")
        self.assertEqual((item.min_stock, item.unit), (0, "шт"))

    def test_import_result_is_dataclass_with_defaults(self):
        """ImportResult() по умолчанию: 0 и пустой список, списки разных экземпляров не общие."""
        first, second = ImportResult(), ImportResult()
        first.reject(2, "тест")
        self.assertEqual(second.rejected, [])


class JsonStateTests(TempDirTestCase):
    def build(self) -> Workshop:
        workshop = Workshop(today=lambda: TODAY)
        workshop.add_item(ReusableTool("SLD-001", "Паяльная станция", "Пайка", 2))
        workshop.add_item(Consumable("RES-010", "Резистор 10 кОм", "Компоненты", 10, 5))
        workshop.issue("SLD-001", "Алия", 2)
        workshop.request_item("SLD-001", "Дамир", 1)
        return workshop

    def test_save_load_roundtrip(self):
        """save_state → load_state восстанавливает предметы, выдачи и очередь (русский текст читаем в файле)."""
        path = self.dir / "sub" / "state.json"  # вложенной папки ещё нет
        original = self.build()
        save_state(original, path)
        self.assertIn("Паяльная станция", path.read_text(encoding="utf-8"))  # ensure_ascii=False
        restored = load_state(path, today=lambda: TODAY)
        self.assertEqual(restored.to_dict(), original.to_dict())

    def test_no_temp_file_left(self):
        """После успешной записи временного файла .tmp не остаётся."""
        save_state(self.build(), self.dir / "state.json")
        self.assertEqual([p.name for p in self.dir.iterdir()], ["state.json"])

    def test_corrupt_json(self):
        """Файл состояния — не JSON → StorageError (приложение не продолжает с мусором)."""
        with self.assertRaises(StorageError):
            load_state(self.write("state.json", "{ это не json"))

    def test_valid_json_wrong_content(self):
        """Корректный JSON с неверным содержимым → StorageError."""
        for text in ("[]", '{"version": 1}', '{"version": 1, "items": [{"kind": "tool"}], "loans": [], "waitlist": [], "next_loan_id": 1}'):
            with self.subTest(text=text[:30]):
                with self.assertRaises(StorageError):
                    load_state(self.write("state.json", text))

    def test_missing_state_file(self):
        """Файла состояния нет → StorageError."""
        with self.assertRaises(StorageError):
            load_state(self.dir / "state.json")

    def test_unwritable_path(self):
        """Путь, по которому нельзя записать (родитель — обычный файл) → StorageError."""
        blocker = self.write("blocker", "x")
        with self.assertRaises(StorageError):
            save_state(self.build(), blocker / "state.json")

    def test_save_report(self):
        """Отчёт записывается в JSON и читается обратно."""
        workshop = self.build()
        path = self.dir / "report.json"
        save_report(workshop.build_report(), path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["totals"]["active_loans"], 1)
        self.assertEqual(data["waitlist"][0]["borrower"], "Дамир")


if __name__ == "__main__":
    unittest.main()
