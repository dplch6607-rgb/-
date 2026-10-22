"""Тесты собственных алгоритмов поиска и сортировки."""
import random
import unittest

from workshop.algorithms import (
    binary_search,
    binary_search_left,
    is_sorted,
    linear_find_all,
    merge_sort,
)


class MergeSortTests(unittest.TestCase):
    def test_empty_list(self):
        """Пустой список → пустой список."""
        self.assertEqual(merge_sort([]), [])

    def test_single_element(self):
        """Один элемент → тот же элемент."""
        self.assertEqual(merge_sort([42]), [42])

    def test_already_sorted(self):
        """Уже отсортированный вход → без изменений."""
        self.assertEqual(merge_sort([1, 2, 3, 4]), [1, 2, 3, 4])

    def test_reversed_input(self):
        """Обратный порядок → по возрастанию."""
        self.assertEqual(merge_sort([5, 4, 3, 2, 1]), [1, 2, 3, 4, 5])

    def test_descending(self):
        """reverse=True → по убыванию."""
        self.assertEqual(merge_sort([3, 1, 2], reverse=True), [3, 2, 1])

    def test_stable_ascending(self):
        """Равные ключи сохраняют исходный порядок (по возрастанию)."""
        records = [("б", 1), ("а", 2), ("в", 1), ("г", 2)]
        result = merge_sort(records, key=lambda r: r[1])
        self.assertEqual(result, [("б", 1), ("в", 1), ("а", 2), ("г", 2)])

    def test_stable_descending(self):
        """Равные ключи сохраняют исходный порядок и при reverse=True."""
        records = [("б", 1), ("а", 2), ("в", 1), ("г", 2)]
        result = merge_sort(records, key=lambda r: r[1], reverse=True)
        self.assertEqual(result, [("а", 2), ("г", 2), ("б", 1), ("в", 1)])

    def test_source_not_modified(self):
        """Исходный список не изменяется."""
        source = [3, 1, 2]
        merge_sort(source)
        self.assertEqual(source, [3, 1, 2])

    def test_matches_builtin_sorted_on_random_data(self):
        """200 случайных списков → результат совпадает со встроенным sorted()."""
        rng = random.Random(2402)
        for _ in range(200):
            data = [rng.randint(-20, 20) for _ in range(rng.randint(0, 40))]
            self.assertEqual(merge_sort(data), sorted(data))
            self.assertEqual(merge_sort(data, reverse=True), sorted(data, reverse=True))


class BinarySearchTests(unittest.TestCase):
    DATA = [3, 5, 10, 40, 250, 400]

    def test_empty_collection(self):
        """Пустая коллекция → -1."""
        self.assertEqual(binary_search([], 1), -1)

    def test_found_at_start_middle_end(self):
        """Элемент в начале, середине и конце → правильные индексы."""
        self.assertEqual(binary_search(self.DATA, 3), 0)
        self.assertEqual(binary_search(self.DATA, 40), 3)
        self.assertEqual(binary_search(self.DATA, 400), 5)

    def test_missing_value(self):
        """Значения нет (меньше, между, больше всех) → -1."""
        for target in (1, 7, 1000):
            with self.subTest(target=target):
                self.assertEqual(binary_search(self.DATA, target), -1)

    def test_duplicates_return_leftmost(self):
        """Повторяющийся ключ → индекс первого вхождения."""
        self.assertEqual(binary_search([1, 2, 2, 2, 3], 2), 1)

    def test_key_function(self):
        """Поиск по полю записи через key."""
        records = [("а", 1), ("б", 5), ("в", 9)]
        self.assertEqual(binary_search(records, 5, key=lambda r: r[1]), 1)

    def test_left_bound_is_insertion_point(self):
        """binary_search_left → позиция вставки, в т.ч. 0 и len(records)."""
        self.assertEqual(binary_search_left(self.DATA, 7), 2)
        self.assertEqual(binary_search_left(self.DATA, 0), 0)
        self.assertEqual(binary_search_left(self.DATA, 999), len(self.DATA))
        self.assertEqual(binary_search_left([], 5), 0)

    def test_agrees_with_linear_scan(self):
        """Случайные отсортированные данные → бинарный поиск = первый индекс при полном переборе."""
        rng = random.Random(7)
        for _ in range(100):
            data = sorted(rng.randint(0, 15) for _ in range(rng.randint(0, 30)))
            target = rng.randint(-1, 16)
            expected = data.index(target) if target in data else -1
            self.assertEqual(binary_search(data, target), expected)


class HelpersTests(unittest.TestCase):
    def test_is_sorted(self):
        """is_sorted: возрастание, убывание, пустой и неупорядоченный списки."""
        self.assertTrue(is_sorted([]))
        self.assertTrue(is_sorted([1, 1, 2]))
        self.assertFalse(is_sorted([2, 1]))
        self.assertTrue(is_sorted([3, 2, 2], reverse=True))
        self.assertFalse(is_sorted([1, 2], reverse=True))

    def test_linear_find_all_empty_and_no_match(self):
        """Пустая коллекция и отсутствие совпадений → пустой список."""
        self.assertEqual(linear_find_all([], lambda x: True), [])
        self.assertEqual(linear_find_all([1, 2, 3], lambda x: x > 5), [])

    def test_linear_find_all_keeps_order(self):
        """Совпадения возвращаются в исходном порядке."""
        self.assertEqual(linear_find_all([5, 2, 8, 1, 6], lambda x: x > 4), [5, 8, 6])


if __name__ == "__main__":
    unittest.main()
