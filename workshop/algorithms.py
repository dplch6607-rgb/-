"""Собственные алгоритмы проекта: линейный и бинарный поиск, сортировка слиянием.

Во всех функциях ``key`` — функция, которая достаёт из записи значение для сравнения.
Поэтому один и тот же алгоритм работает с любым полем и любым типом записей.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence, TypeVar

T = TypeVar("T")


def _identity(value: Any) -> Any:
    """Ключ по умолчанию: сравнивать сами элементы."""
    return value


def linear_find_all(records: Iterable[T], predicate: Callable[[T], bool]) -> list[T]:
    """Вернуть все записи, для которых ``predicate`` истинен, в исходном порядке.

    Предусловий нет: подходит для неотсортированных и пустых коллекций
    (пустая коллекция даёт пустой список).
    Сложность: время O(n), дополнительная память O(k), k — число найденных записей.
    """
    found: list[T] = []
    for record in records:
        if predicate(record):
            found.append(record)
    return found


def is_sorted(
    records: Sequence[T],
    key: Callable[[T], Any] = _identity,
    reverse: bool = False,
) -> bool:
    """Проверить, что записи упорядочены по ``key`` (по возрастанию или убыванию). O(n)."""
    for index in range(1, len(records)):
        previous, current = key(records[index - 1]), key(records[index])
        if (previous < current) if reverse else (previous > current):
            return False
    return True


def binary_search_left(
    records: Sequence[T],
    target: Any,
    key: Callable[[T], Any] = _identity,
) -> int:
    """Вернуть индекс первой записи, у которой ``key(запись) >= target`` (точка вставки).

    Предусловия:
      * ``records`` отсортирован по возрастанию по тому же ``key``;
      * ``target`` сравним со значениями ``key`` (тот же тип, та же нормализация регистра).
    Если все ключи меньше ``target`` (или коллекция пуста), вернёт ``len(records)``.
    Сложность: время O(log n), память O(1).
    """
    low, high = 0, len(records)
    while low < high:
        middle = (low + high) // 2
        if key(records[middle]) < target:
            low = middle + 1
        else:
            high = middle
    return low


def binary_search(
    records: Sequence[T],
    target: Any,
    key: Callable[[T], Any] = _identity,
) -> int:
    """Вернуть индекс первой записи с ``key(запись) == target`` или -1, если такой нет.

    Предусловия те же, что у ``binary_search_left``: коллекция отсортирована по ``key``.
    На неотсортированных данных результат не определён — это ответственность вызывающего.
    Если ключ повторяется, возвращается самое левое вхождение.
    Сложность: O(log n).
    """
    index = binary_search_left(records, target, key)
    if index < len(records) and key(records[index]) == target:
        return index
    return -1


def merge_sort(
    records: Iterable[T],
    key: Callable[[T], Any] = _identity,
    reverse: bool = False,
) -> list[T]:
    """Отсортировать записи слиянием и вернуть новый список (исходные данные не меняются).

    Свойства:
      * устойчивая: записи с равными ключами сохраняют исходный порядок
        (это же верно и при ``reverse=True``), поэтому можно сортировать по нескольким
        полям подряд — от менее важного к более важному;
      * пустая коллекция и коллекция из одной записи возвращаются как есть (копия).
    Сложность: время O(n log n) в лучшем, среднем и худшем случаях; память O(n).
    """
    items = list(records)
    if len(items) <= 1:
        return items
    middle = len(items) // 2
    left = merge_sort(items[:middle], key, reverse)
    right = merge_sort(items[middle:], key, reverse)
    return _merge(left, right, key, reverse)


def _merge(
    left: list[T],
    right: list[T],
    key: Callable[[T], Any],
    reverse: bool,
) -> list[T]:
    """Слить два уже упорядоченных списка в один. O(len(left) + len(right))."""
    merged: list[T] = []
    i = j = 0
    while i < len(left) and j < len(right):
        left_key, right_key = key(left[i]), key(right[j])
        # При равных ключах берём элемент из левой половины — так сохраняется устойчивость.
        take_left = left_key >= right_key if reverse else left_key <= right_key
        if take_left:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged
