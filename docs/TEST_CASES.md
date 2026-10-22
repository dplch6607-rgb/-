# Таблица тест-кейсов

Всего тестов: **114**, провалено: **0**. Запуск: `python -m unittest -v` из корня проекта.

Колонка «Вход → ожидаемый результат» взята из docstring каждого теста, поэтому таблица не расходится с кодом.

| ID | Проверяемый модуль | Класс тестов | Тест | Вход → ожидаемый результат | Статус |
|---|---|---|---|---|---|
| ALG-01 | `algorithms.py` | BinarySearchTests | `test_agrees_with_linear_scan` | Случайные отсортированные данные → бинарный поиск = первый индекс при полном переборе. | OK |
| ALG-02 | `algorithms.py` | BinarySearchTests | `test_duplicates_return_leftmost` | Повторяющийся ключ → индекс первого вхождения. | OK |
| ALG-03 | `algorithms.py` | BinarySearchTests | `test_empty_collection` | Пустая коллекция → -1. | OK |
| ALG-04 | `algorithms.py` | BinarySearchTests | `test_found_at_start_middle_end` | Элемент в начале, середине и конце → правильные индексы. | OK |
| ALG-05 | `algorithms.py` | BinarySearchTests | `test_key_function` | Поиск по полю записи через key. | OK |
| ALG-06 | `algorithms.py` | BinarySearchTests | `test_left_bound_is_insertion_point` | binary_search_left → позиция вставки, в т.ч. 0 и len(records). | OK |
| ALG-07 | `algorithms.py` | BinarySearchTests | `test_missing_value` | Значения нет (меньше, между, больше всех) → -1. | OK |
| ALG-08 | `algorithms.py` | HelpersTests | `test_is_sorted` | is_sorted: возрастание, убывание, пустой и неупорядоченный списки. | OK |
| ALG-09 | `algorithms.py` | HelpersTests | `test_linear_find_all_empty_and_no_match` | Пустая коллекция и отсутствие совпадений → пустой список. | OK |
| ALG-10 | `algorithms.py` | HelpersTests | `test_linear_find_all_keeps_order` | Совпадения возвращаются в исходном порядке. | OK |
| ALG-11 | `algorithms.py` | MergeSortTests | `test_already_sorted` | Уже отсортированный вход → без изменений. | OK |
| ALG-12 | `algorithms.py` | MergeSortTests | `test_descending` | reverse=True → по убыванию. | OK |
| ALG-13 | `algorithms.py` | MergeSortTests | `test_empty_list` | Пустой список → пустой список. | OK |
| ALG-14 | `algorithms.py` | MergeSortTests | `test_matches_builtin_sorted_on_random_data` | 200 случайных списков → результат совпадает со встроенным sorted(). | OK |
| ALG-15 | `algorithms.py` | MergeSortTests | `test_reversed_input` | Обратный порядок → по возрастанию. | OK |
| ALG-16 | `algorithms.py` | MergeSortTests | `test_single_element` | Один элемент → тот же элемент. | OK |
| ALG-17 | `algorithms.py` | MergeSortTests | `test_source_not_modified` | Исходный список не изменяется. | OK |
| ALG-18 | `algorithms.py` | MergeSortTests | `test_stable_ascending` | Равные ключи сохраняют исходный порядок (по возрастанию). | OK |
| ALG-19 | `algorithms.py` | MergeSortTests | `test_stable_descending` | Равные ключи сохраняют исходный порядок и при reverse=True. | OK |
| MOD-01 | `models.py` | FieldValidationTests | `test_bad_sku_rejected` | Неверные артикулы ('', 'abc', 'SLD001', 'S-001', 'SLD-1', число) → ValidationError. | OK |
| MOD-02 | `models.py` | FieldValidationTests | `test_category_first_letter_capitalized` | Категория 'пайка' → 'Пайка'. | OK |
| MOD-03 | `models.py` | FieldValidationTests | `test_consumable_negative_values_rejected` | Отрицательные quantity и min_stock → ValidationError. | OK |
| MOD-04 | `models.py` | FieldValidationTests | `test_empty_name_rejected` | Пустое название → ValidationError. | OK |
| MOD-05 | `models.py` | FieldValidationTests | `test_sku_is_normalized` | Артикул в нижнем регистре с пробелами → 'SLD-001'. | OK |
| MOD-06 | `models.py` | FieldValidationTests | `test_sku_is_read_only` | Артикул нельзя присвоить напрямую (property без setter) → AttributeError. | OK |
| MOD-07 | `models.py` | FieldValidationTests | `test_tool_available_cannot_exceed_total` | available > total → ValidationError; available = total допустимо. | OK |
| MOD-08 | `models.py` | FieldValidationTests | `test_tool_available_setter_validates` | Прямое присваивание available = -1 → ValidationError, значение не меняется. | OK |
| MOD-09 | `models.py` | FieldValidationTests | `test_tool_total_must_be_positive_int` | total = 0, -1, 2.5, True, '3' → ValidationError. | OK |
| MOD-10 | `models.py` | InventoryTests | `test_categories_unique_and_sorted` | Категории: без повторов и по алфавиту. | OK |
| MOD-11 | `models.py` | InventoryTests | `test_duplicate_sku_rejected` | Повторный артикул → DuplicateItemError, склад не изменился. | OK |
| MOD-12 | `models.py` | InventoryTests | `test_empty_inventory` | Пустой склад: сортировка и все виды поиска → пустой список, без ошибок. | OK |
| MOD-13 | `models.py` | InventoryTests | `test_get_is_case_insensitive` | get('sld-001') находит SLD-001. | OK |
| MOD-14 | `models.py` | InventoryTests | `test_get_missing` | Отсутствующий артикул → ItemNotFoundError. | OK |
| MOD-15 | `models.py` | InventoryTests | `test_remove_updates_everything` | Удаление убирает предмет из списка, индекса, поиска и пустую категорию. | OK |
| MOD-16 | `models.py` | InventoryTests | `test_search_bad_input` | Пустой запрос и неизвестный режим → ValidationError. | OK |
| MOD-17 | `models.py` | InventoryTests | `test_search_by_sku` | Поиск по артикулу: точное совпадение, регистр не важен, нет такого → []. | OK |
| MOD-18 | `models.py` | InventoryTests | `test_search_category` | Категория (без учёта регистра) → предметы категории. | OK |
| MOD-19 | `models.py` | InventoryTests | `test_search_contains` | Часть названия 'метр' (в любом месте слова) → 'Мультиметр цифровой'. | OK |
| MOD-20 | `models.py` | InventoryTests | `test_search_prefix_binary` | Начало названия 'пая' (любой регистр) → 'Паяльная станция'; 'Р' → резистор; 'яя' → пусто. | OK |
| MOD-21 | `models.py` | InventoryTests | `test_search_prefix_returns_all_with_prefix` | Несколько названий с общим началом → найдены все, в алфавитном порядке. | OK |
| MOD-22 | `models.py` | InventoryTests | `test_sort_descending` | Сортировка по остатку по убыванию → RES-010 (100) первым. | OK |
| MOD-23 | `models.py` | InventoryTests | `test_sort_each_field` | Сортировка по sku/name/category/on_hand → порядок как у встроенной сортировки. | OK |
| MOD-24 | `models.py` | InventoryTests | `test_sort_unknown_field` | Неизвестное поле сортировки → ValidationError. | OK |
| MOD-25 | `models.py` | InventoryTests | `test_update_is_atomic` | Некорректная категория при корректном имени → ничего не изменено. | OK |
| MOD-26 | `models.py` | InventoryTests | `test_update_refreshes_name_view` | После переименования префиксный поиск находит новое имя и не находит старое. | OK |
| MOD-27 | `models.py` | PolymorphismTests | `test_common_interface_take_and_add_stock` | Оба типа через один интерфейс: take(2) уменьшает on_hand на 2, add_stock(5) увеличивает на 5. | OK |
| MOD-28 | `models.py` | PolymorphismTests | `test_describe_contains_sku` | describe() обоих типов содержит артикул. | OK |
| MOD-29 | `models.py` | PolymorphismTests | `test_factory_unknown_kind` | Неизвестный kind или отсутствующее поле → ValidationError. | OK |
| MOD-30 | `models.py` | PolymorphismTests | `test_give_back_differs_by_type` | give_back: инструмент принимается, расходник → ValidationError. | OK |
| MOD-31 | `models.py` | PolymorphismTests | `test_needs_attention_differs_by_type` | Инструмент требует внимания при available = 0, расходник — при остатке ниже минимума. | OK |
| MOD-32 | `models.py` | PolymorphismTests | `test_roundtrip_through_dict_factory` | to_dict → item_from_dict возвращает предмет того же типа с теми же данными. | OK |
| MOD-33 | `models.py` | PolymorphismTests | `test_take_too_much_raises` | take больше остатка у обоих типов → InsufficientStockError. | OK |
| MOD-34 | `models.py` | PolymorphismTests | `test_tool_give_back_beyond_total_rejected` | Вернуть инструмента больше, чем выдавали → ValidationError. | OK |
| MOD-35 | `models.py` | ReportAndStateTests | `test_from_dict_duplicate_loan_ids` | Повторяющиеся номера выдач → ValidationError. | OK |
| MOD-36 | `models.py` | ReportAndStateTests | `test_from_dict_missing_field` | В состоянии нет поля 'items' → ValidationError. | OK |
| MOD-37 | `models.py` | ReportAndStateTests | `test_from_dict_request_for_unknown_item` | Заявка на несуществующий артикул → ValidationError. | OK |
| MOD-38 | `models.py` | ReportAndStateTests | `test_from_dict_unsorted_loans_are_sorted` | Журнал выдач в файле в неверном порядке → загружается отсортированным, предупреждение в log. | OK |
| MOD-39 | `models.py` | ReportAndStateTests | `test_from_dict_wrong_types` | Не словарь, неверная версия, 'items' = None → ValidationError. | OK |
| MOD-40 | `models.py` | ReportAndStateTests | `test_report_contents` | Отчёт: что требует внимания, выдачи по людям, сводка по категориям, очередь. | OK |
| MOD-41 | `models.py` | ReportAndStateTests | `test_report_of_empty_workshop` | Отчёт пустой мастерской → нули и пустые разделы. | OK |
| MOD-42 | `models.py` | ReportAndStateTests | `test_state_roundtrip` | to_dict → from_dict → to_dict даёт тот же результат (включая выдачи и очередь). | OK |
| MOD-43 | `models.py` | WorkshopLoanTests | `test_find_loan_by_binary_search` | Выдачи №1..5 находятся по номеру бинарным поиском. | OK |
| MOD-44 | `models.py` | WorkshopLoanTests | `test_issue_bad_arguments` | Пустое имя, количество 0 или 'пять', неизвестный артикул → понятные исключения. | OK |
| MOD-45 | `models.py` | WorkshopLoanTests | `test_issue_consumable_is_not_returnable` | Выдача расходника: остаток уменьшается, выдача сразу неактивна. | OK |
| MOD-46 | `models.py` | WorkshopLoanTests | `test_issue_insufficient` | Выдать больше, чем есть → InsufficientStockError, склад и журнал не изменились. | OK |
| MOD-47 | `models.py` | WorkshopLoanTests | `test_issue_tool_reduces_available` | Выдача инструмента: available уменьшается, выдача активна, дата = сегодня. | OK |
| MOD-48 | `models.py` | WorkshopLoanTests | `test_remove_item_after_return` | После возврата предмет удаляется. | OK |
| MOD-49 | `models.py` | WorkshopLoanTests | `test_remove_item_with_active_loan` | Удалить предмет с невозвращённой выдачей → ItemInUseError. | OK |
| MOD-50 | `models.py` | WorkshopLoanTests | `test_return_consumable_rejected` | Возврат выдачи расходника → ValidationError. | OK |
| MOD-51 | `models.py` | WorkshopLoanTests | `test_return_restores_stock` | Возврат возвращает инструмент на склад и закрывает выдачу. | OK |
| MOD-52 | `models.py` | WorkshopLoanTests | `test_return_twice` | Повторный возврат той же выдачи → ValidationError. | OK |
| MOD-53 | `models.py` | WorkshopLoanTests | `test_return_unknown_loan` | Несуществующий номер выдачи (в т.ч. на пустом журнале) → LoanNotFoundError. | OK |
| MOD-54 | `models.py` | WorkshopQueueTests | `test_impossible_request_rejected` | Заявка на инструментов больше, чем существует (3 при total=2) → ValidationError, в очередь не попадает. | OK |
| MOD-55 | `models.py` | WorkshopQueueTests | `test_later_small_request_does_not_overtake_earlier_big_one` | Дефект: Алия ждёт 5 шт., Дамир — 1 шт.; пополнение на 1 шт. не должно отдать его Дамиру раньше Алии. | OK |
| MOD-56 | `models.py` | WorkshopQueueTests | `test_new_request_does_not_jump_the_queue` | Если на предмет уже есть очередь, новая заявка встаёт в конец, даже когда запас позволяет выдать. | OK |
| MOD-57 | `models.py` | WorkshopQueueTests | `test_queues_for_different_items_are_independent` | Заявка на один предмет не блокирует заявки на другой. | OK |
| MOD-58 | `models.py` | WorkshopQueueTests | `test_remove_item_with_waiting_request` | Удалить предмет, на который есть заявка → ItemInUseError. | OK |
| MOD-59 | `models.py` | WorkshopQueueTests | `test_request_issues_immediately_when_available` | Предмет есть → request_item сразу возвращает Loan, очередь пуста. | OK |
| MOD-60 | `models.py` | WorkshopQueueTests | `test_request_queues_when_unavailable` | Предмета нет → request_item возвращает LoanRequest, склад не меняется. | OK |
| MOD-61 | `models.py` | WorkshopQueueTests | `test_restock_serves_waitlist` | Пополнение расходника обслуживает ожидающего. | OK |
| MOD-62 | `models.py` | WorkshopQueueTests | `test_return_serves_waitlist` | Возврат инструмента сразу выдаёт его первому в очереди. | OK |
| STO-01 | `storage.py` | CsvImportTests | `test_bad_encoding_rolls_back` | Файл портится далеко за началом (не UTF-8, после >8 КБ корректных строк) → StorageError и откат добавленного. | OK |
| STO-02 | `storage.py` | CsvImportTests | `test_blank_unit_and_min_stock_defaults` | Пустые min_stock и unit у расходника → 0 и 'шт'. | OK |
| STO-03 | `storage.py` | CsvImportTests | `test_duplicate_of_existing_item_rejected` | Артикул, который уже есть на складе, отклоняется; существующий предмет не меняется. | OK |
| STO-04 | `storage.py` | CsvImportTests | `test_empty_file` | Совсем пустой файл → StorageError (нет заголовка). | OK |
| STO-05 | `storage.py` | CsvImportTests | `test_header_only_file` | Файл только с заголовком → 0 предметов, 0 отклонённых, без ошибок. | OK |
| STO-06 | `storage.py` | CsvImportTests | `test_import_file_with_errors` | data/items_with_errors.csv → 2 предмета добавлено, 8 строк отклонено с причинами. | OK |
| STO-07 | `storage.py` | CsvImportTests | `test_import_good_file` | Корректный data/items.csv → все 22 предмета добавлены, ничего не отклонено. | OK |
| STO-08 | `storage.py` | CsvImportTests | `test_import_result_is_dataclass_with_defaults` | ImportResult() по умолчанию: 0 и пустой список, списки разных экземпляров не общие. | OK |
| STO-09 | `storage.py` | CsvImportTests | `test_missing_columns` | В заголовке нет обязательного столбца → StorageError с его именем. | OK |
| STO-10 | `storage.py` | CsvImportTests | `test_missing_file` | Файла нет → StorageError, склад не изменён. | OK |
| STO-11 | `storage.py` | CsvImportTests | `test_negative_quantity_rejected_by_property` | quantity = -5 у расходника → строка отклонена проверкой в классе, в склад не попадает. | OK |
| STO-12 | `storage.py` | CsvImportTests | `test_reader_is_a_lazy_generator` | read_csv_rows — генератор: до первого next() файл даже не открывается. | OK |
| STO-13 | `storage.py` | CsvImportTests | `test_reader_yields_rows_one_by_one` | Строки отдаются по одной вместе с номерами строк файла. | OK |
| STO-14 | `storage.py` | JsonStateTests | `test_corrupt_json` | Файл состояния — не JSON → StorageError (приложение не продолжает с мусором). | OK |
| STO-15 | `storage.py` | JsonStateTests | `test_missing_state_file` | Файла состояния нет → StorageError. | OK |
| STO-16 | `storage.py` | JsonStateTests | `test_no_temp_file_left` | После успешной записи временного файла .tmp не остаётся. | OK |
| STO-17 | `storage.py` | JsonStateTests | `test_save_load_roundtrip` | save_state → load_state восстанавливает предметы, выдачи и очередь (русский текст читаем в файле). | OK |
| STO-18 | `storage.py` | JsonStateTests | `test_save_report` | Отчёт записывается в JSON и читается обратно. | OK |
| STO-19 | `storage.py` | JsonStateTests | `test_unwritable_path` | Путь, по которому нельзя записать (родитель — обычный файл) → StorageError. | OK |
| STO-20 | `storage.py` | JsonStateTests | `test_valid_json_wrong_content` | Корректный JSON с неверным содержимым → StorageError. | OK |
| UI-01 | `ui.py` | ConsoleUITests | `test_add_duplicate_sku` | Добавление существующего артикула → ошибка сразу после ввода артикула. | OK |
| UI-02 | `ui.py` | ConsoleUITests | `test_add_item_validates_each_field_and_saves` | Добавление: плохой артикул 'abc' и пустое название → повторный запрос; затем предмет сохранён в JSON. | OK |
| UI-03 | `ui.py` | ConsoleUITests | `test_eof_ends_gracefully` | Конец ввода (Ctrl+D) → аккуратное завершение, без traceback. | OK |
| UI-04 | `ui.py` | ConsoleUITests | `test_exit` | Пункт 0 завершает работу. | OK |
| UI-05 | `ui.py` | ConsoleUITests | `test_import_missing_file_reports_error` | Импорт несуществующего файла → 'Ошибка: Файл не найден', меню продолжает работу. | OK |
| UI-06 | `ui.py` | ConsoleUITests | `test_non_numeric_quantity_is_asked_again` | Количество 'пять', '0', '-3' → три сообщения об ошибке, затем '1' принято и выдача сделана. | OK |
| UI-07 | `ui.py` | ConsoleUITests | `test_queue_flow` | Выдать всё → встать в очередь → принять возврат → ожидающий получает предмет. | OK |
| UI-08 | `ui.py` | ConsoleUITests | `test_remove_cancelled_and_invalid_confirmation` | Подтверждение удаления: 'может быть' → повторный вопрос, 'н' → отмена, предмет остался. | OK |
| UI-09 | `ui.py` | ConsoleUITests | `test_report_written_to_json` | Пункт 10 печатает отчёт и записывает report.json. | OK |
| UI-10 | `ui.py` | ConsoleUITests | `test_search_modes` | Поиск по началу названия находит предмет и называет алгоритм; пустой результат → 'Ничего нет'. | OK |
| UI-11 | `ui.py` | ConsoleUITests | `test_sorting_menu` | Сортировка по остатку по убыванию → расходник (100) раньше инструмента (2). | OK |
| UI-12 | `ui.py` | ConsoleUITests | `test_unknown_menu_item` | Неизвестный пункт меню ('99', 'abc', пустая строка) → подсказка, программа продолжает работать. | OK |
| UI-13 | `ui.py` | ConsoleUITests | `test_unknown_sku_reports_error_and_continues` | Выдача несуществующего артикула → 'Ошибка: …', склад не тронут, меню продолжает работу. | OK |

## Исправленный дефект

**Симптом.** Тест `test_later_small_request_does_not_overtake_earlier_big_one` (MOD-55) падал.
В очереди стояли Алия (5 шт.) и Дамир (1 шт.) на один и тот же расходник; после пополнения на 1 шт.
предмет получал Дамир, хотя Алия ждала дольше.

**Причина.** Первая версия `Workshop._serve_waitlist` проверяла каждую заявку независимо: заявку Алии
пропускала (не хватает), а заявку Дамира выполняла. Маленькие заявки могли обгонять большие бесконечно,
и большая заявка рисковала не выполниться никогда.

**Исправление.** В `_serve_waitlist` добавлено множество `blocked`: как только заявка на предмет X не выполнена,
все более поздние заявки на X тоже ждут. Заявки на разные предметы по-прежнему не мешают друг другу
(тест `test_queues_for_different_items_are_independent`).

**Где видно в Git.** Коммит `test: воспроизведён дефект очереди…` (тест падает) → коммит `fix: очередь FIFO по каждому предмету…` (тест проходит).
