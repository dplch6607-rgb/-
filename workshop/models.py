"""Модель предметной области «Мастерская электроники».

Классы:
    Item (абстрактный) → ReusableTool, Consumable — предметы склада (отношение «является»);
    Loan, LoanRequest — dataclass-записи о выдаче и о заявке в очереди;
    Inventory — коллекция предметов: list (порядок), dict (поиск по артикулу), set (категории);
    Workshop — фасад, который владеет Inventory, журналом выдач и очередью заявок (композиция).
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Iterator, Optional, Union

from .algorithms import (
    binary_search,
    binary_search_left,
    is_sorted,
    linear_find_all,
    merge_sort,
)
from .exceptions import (
    DuplicateItemError,
    InsufficientStockError,
    ItemInUseError,
    ItemNotFoundError,
    LoanNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

SKU_PATTERN = re.compile(r"^[A-Z]{2,4}-\d{3}$")
STATE_VERSION = 1


# --------------------------------------------------------------------------- проверки полей

def _require_int(value: Any, field_name: str, minimum: int = 0) -> int:
    """Убедиться, что value — целое число (не bool) не меньше minimum."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name}: нужно целое число, получено {value!r}")
    if value < minimum:
        raise ValidationError(f"{field_name}: значение не может быть меньше {minimum} (получено {value})")
    return value


def _require_text(value: Any, field_name: str, max_length: int) -> str:
    """Убедиться, что value — непустая строка не длиннее max_length; лишние пробелы убираются."""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name}: нужна строка, получено {value!r}")
    text = " ".join(value.split())
    if not text:
        raise ValidationError(f"{field_name}: значение не может быть пустым")
    if len(text) > max_length:
        raise ValidationError(f"{field_name}: не длиннее {max_length} символов (получено {len(text)})")
    return text


def normalize_sku(value: Any) -> str:
    """Привести артикул к виду ABC-123 или поднять ValidationError."""
    text = _require_text(value, "Артикул", 20).upper()
    if not SKU_PATTERN.match(text):
        raise ValidationError(
            f"Артикул {text!r} не подходит: нужен вид ABC-123 (2–4 латинские буквы, дефис, 3 цифры)"
        )
    return text


def normalize_name(value: Any) -> str:
    """Проверить название предмета."""
    return _require_text(value, "Название", 60)


def normalize_category(value: Any) -> str:
    """Проверить категорию; первая буква делается заглавной, чтобы «пайка» и «Пайка» не расходились."""
    text = _require_text(value, "Категория", 30)
    return text[0].upper() + text[1:]


def normalize_person(value: Any) -> str:
    """Проверить имя того, кто берёт предмет."""
    return _require_text(value, "Имя", 40)


def normalize_unit(value: Any) -> str:
    """Проверить единицу измерения расходника."""
    return _require_text(value, "Единица измерения", 10)


def _parse_date(value: Any) -> date:
    """Разобрать дату формата ГГГГ-ММ-ДД из JSON."""
    if not isinstance(value, str):
        raise ValidationError(f"Дата: нужна строка ГГГГ-ММ-ДД, получено {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"Дата {value!r} не в формате ГГГГ-ММ-ДД") from exc


# --------------------------------------------------------------------------- предметы

class Item(ABC):
    """Предмет склада. Общая часть: артикул, название, категория.

    Подклассы по-разному отвечают на одни и те же вызовы (полиморфизм):
    инструмент возвращают, расходник списывают насовсем.
    """

    kind: str = ""
    returnable: bool = False

    def __init__(self, sku: str, name: str, category: str) -> None:
        self._sku = normalize_sku(sku)
        self._name = normalize_name(name)
        self._category = normalize_category(category)

    # Артикул, название и категорию нельзя присвоить напрямую: Inventory хранит по ним индекс
    # и отсортированное представление, поэтому менять их нужно через Inventory.update().
    @property
    def sku(self) -> str:
        return self._sku

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return self._category

    @property
    @abstractmethod
    def on_hand(self) -> int:
        """Сколько единиц можно выдать прямо сейчас."""

    @abstractmethod
    def can_issue(self, quantity: int) -> bool:
        """Можно ли выдать quantity единиц сейчас."""

    @abstractmethod
    def can_ever_issue(self, quantity: int) -> bool:
        """Может ли заявка на quantity единиц вообще когда-нибудь быть выполнена."""

    @abstractmethod
    def take(self, quantity: int) -> None:
        """Забрать quantity единиц со склада; при нехватке — InsufficientStockError."""

    @abstractmethod
    def give_back(self, quantity: int) -> None:
        """Принять quantity единиц обратно."""

    @abstractmethod
    def add_stock(self, amount: int) -> None:
        """Пополнить запас на amount единиц."""

    @abstractmethod
    def needs_attention(self) -> Optional[str]:
        """Текст проблемы (кончается, всё выдано) или None, если всё в порядке."""

    @abstractmethod
    def describe(self) -> str:
        """Строка для вывода в таблице склада."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Представление для JSON."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> "Item":
        """Создать предмет из словаря (с полной проверкой полей)."""

    def _head(self) -> str:
        return f"{self.sku:<8} {self.name:<30} {self.category:<18}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.sku!r}, {self.name!r})"


class ReusableTool(Item):
    """Возвращаемый инструмент или плата: всего ``total`` штук, из них ``available`` на месте."""

    kind = "tool"
    returnable = True

    def __init__(
        self,
        sku: str,
        name: str,
        category: str,
        total: int,
        available: Optional[int] = None,
    ) -> None:
        super().__init__(sku, name, category)
        self._total = _require_int(total, "Всего единиц", minimum=1)
        self._available = self._total
        if available is not None:
            self.available = available

    @property
    def total(self) -> int:
        return self._total

    @property
    def available(self) -> int:
        return self._available

    @available.setter
    def available(self, value: int) -> None:
        value = _require_int(value, "Доступно", minimum=0)
        if value > self._total:
            raise ValidationError(f"Доступно ({value}) не может быть больше общего числа ({self._total})")
        self._available = value

    @property
    def on_hand(self) -> int:
        return self._available

    def can_issue(self, quantity: int) -> bool:
        return 0 < quantity <= self._available

    def can_ever_issue(self, quantity: int) -> bool:
        return 0 < quantity <= self._total

    def take(self, quantity: int) -> None:
        if not self.can_issue(quantity):
            raise InsufficientStockError(
                f"«{self.name}»: запрошено {quantity}, на месте {self._available} из {self._total}"
            )
        self._available -= quantity

    def give_back(self, quantity: int) -> None:
        quantity = _require_int(quantity, "Возвращаемое количество", minimum=1)
        if self._available + quantity > self._total:
            raise ValidationError(
                f"«{self.name}»: нельзя вернуть {quantity}, на месте уже {self._available} из {self._total}"
            )
        self._available += quantity

    def add_stock(self, amount: int) -> None:
        amount = _require_int(amount, "Количество пополнения", minimum=1)
        self._total += amount
        self._available += amount

    def needs_attention(self) -> Optional[str]:
        if self._available == 0:
            return f"все {self._total} шт. сейчас выданы"
        return None

    def describe(self) -> str:
        return f"{self._head()} инструмент  {self._available}/{self._total} на месте"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "total": self._total,
            "available": self._available,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReusableTool":
        try:
            return cls(data["sku"], data["name"], data["category"], data["total"], data.get("available"))
        except KeyError as exc:
            raise ValidationError(f"Не хватает поля {exc.args[0]!r}") from exc


class Consumable(Item):
    """Расходный материал: выдаётся насовсем, при остатке ниже ``min_stock`` требует пополнения."""

    kind = "consumable"
    returnable = False

    def __init__(
        self,
        sku: str,
        name: str,
        category: str,
        quantity: int,
        min_stock: int = 0,
        unit: str = "шт",
    ) -> None:
        super().__init__(sku, name, category)
        self._quantity = _require_int(quantity, "Количество", minimum=0)
        self._min_stock = _require_int(min_stock, "Минимальный запас", minimum=0)
        self._unit = normalize_unit(unit)

    @property
    def quantity(self) -> int:
        return self._quantity

    @property
    def min_stock(self) -> int:
        return self._min_stock

    @property
    def unit(self) -> str:
        return self._unit

    @property
    def on_hand(self) -> int:
        return self._quantity

    def can_issue(self, quantity: int) -> bool:
        return 0 < quantity <= self._quantity

    def can_ever_issue(self, quantity: int) -> bool:
        # Расходник можно пополнить, поэтому ждать можно любое положительное количество.
        return quantity > 0

    def take(self, quantity: int) -> None:
        if not self.can_issue(quantity):
            raise InsufficientStockError(
                f"«{self.name}»: запрошено {quantity} {self._unit}, на складе {self._quantity}"
            )
        self._quantity -= quantity

    def give_back(self, quantity: int) -> None:
        raise ValidationError(f"«{self.name}» — расходный материал, возврату не подлежит")

    def add_stock(self, amount: int) -> None:
        self._quantity += _require_int(amount, "Количество пополнения", minimum=1)

    def needs_attention(self) -> Optional[str]:
        if self._quantity < self._min_stock:
            return f"осталось {self._quantity} {self._unit} при минимуме {self._min_stock}"
        return None

    def describe(self) -> str:
        return f"{self._head()} расходник   {self._quantity} {self._unit} (минимум {self._min_stock})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "quantity": self._quantity,
            "min_stock": self._min_stock,
            "unit": self._unit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Consumable":
        try:
            return cls(
                data["sku"],
                data["name"],
                data["category"],
                data["quantity"],
                data.get("min_stock", 0),
                data.get("unit", "шт"),
            )
        except KeyError as exc:
            raise ValidationError(f"Не хватает поля {exc.args[0]!r}") from exc


_ITEM_KINDS: dict[str, type[Item]] = {
    ReusableTool.kind: ReusableTool,
    Consumable.kind: Consumable,
}


def item_from_dict(data: dict[str, Any]) -> Item:
    """Фабрика: по полю ``kind`` выбрать нужный класс предмета."""
    if not isinstance(data, dict):
        raise ValidationError(f"Запись предмета должна быть объектом, получено {data!r}")
    kind = data.get("kind")
    if kind not in _ITEM_KINDS:
        raise ValidationError(f"Неизвестный тип предмета {kind!r} (ожидается tool или consumable)")
    return _ITEM_KINDS[kind].from_dict(data)


# --------------------------------------------------------------------------- записи-данные

@dataclass
class Loan:
    """Запись журнала: кто, что и когда взял. Возвращаемая выдача активна, пока нет даты возврата."""

    loan_id: int
    sku: str
    borrower: str
    quantity: int
    issued_on: date
    returnable: bool = True
    returned_on: Optional[date] = None

    def __post_init__(self) -> None:
        _require_int(self.loan_id, "Номер выдачи", minimum=1)
        _require_int(self.quantity, "Количество", minimum=1)
        self.borrower = normalize_person(self.borrower)
        if self.returned_on is not None and self.returned_on < self.issued_on:
            raise ValidationError("Дата возврата раньше даты выдачи")

    @property
    def is_active(self) -> bool:
        """Предмет ещё должны вернуть."""
        return self.returnable and self.returned_on is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "sku": self.sku,
            "borrower": self.borrower,
            "quantity": self.quantity,
            "issued_on": self.issued_on.isoformat(),
            "returnable": self.returnable,
            "returned_on": self.returned_on.isoformat() if self.returned_on else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Loan":
        try:
            returned = data.get("returned_on")
            return cls(
                loan_id=data["loan_id"],
                sku=data["sku"],
                borrower=data["borrower"],
                quantity=data["quantity"],
                issued_on=_parse_date(data["issued_on"]),
                returnable=bool(data["returnable"]),
                returned_on=None if returned is None else _parse_date(returned),
            )
        except KeyError as exc:
            raise ValidationError(f"В записи выдачи нет поля {exc.args[0]!r}") from exc


@dataclass(frozen=True)
class LoanRequest:
    """Заявка в очереди: человек ждёт предмет, которого сейчас нет в нужном количестве."""

    borrower: str
    sku: str
    quantity: int
    created_on: date

    def __post_init__(self) -> None:
        _require_int(self.quantity, "Количество", minimum=1)
        # frozen-dataclass: присваивание полей разрешено только через object.__setattr__
        object.__setattr__(self, "borrower", normalize_person(self.borrower))

    def to_dict(self) -> dict[str, Any]:
        return {
            "borrower": self.borrower,
            "sku": self.sku,
            "quantity": self.quantity,
            "created_on": self.created_on.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoanRequest":
        try:
            return cls(
                borrower=data["borrower"],
                sku=data["sku"],
                quantity=data["quantity"],
                created_on=_parse_date(data["created_on"]),
            )
        except KeyError as exc:
            raise ValidationError(f"В заявке нет поля {exc.args[0]!r}") from exc


# --------------------------------------------------------------------------- склад

SORT_FIELDS: dict[str, Callable[[Item], Any]] = {
    "sku": lambda item: item.sku,
    "name": lambda item: item.name.casefold(),
    "category": lambda item: item.category.casefold(),
    "on_hand": lambda item: item.on_hand,
}


def _name_key(item: Item) -> str:
    return item.name.casefold()


class Inventory:
    """Коллекция предметов.

    * ``list``  — порядок добавления и основа для сортировок и линейного поиска;
    * ``dict``  — индекс «артикул → предмет», поиск по артикулу за O(1);
    * ``set``   — уникальные категории (без повторов за O(1) на добавление);
    * кэш представления, отсортированного по названию, — для бинарного поиска по началу названия.
    """

    def __init__(self) -> None:
        self._items: list[Item] = []
        self._by_sku: dict[str, Item] = {}
        self._categories: set[str] = set()
        self._name_view: Optional[list[Item]] = None

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Item]:
        yield from self._items

    def __contains__(self, sku: object) -> bool:
        return isinstance(sku, str) and sku.strip().upper() in self._by_sku

    def add(self, item: Item) -> None:
        """Добавить предмет; повторный артикул → DuplicateItemError."""
        if item.sku in self._by_sku:
            raise DuplicateItemError(f"Артикул {item.sku} уже есть на складе («{self._by_sku[item.sku].name}»)")
        self._items.append(item)
        self._by_sku[item.sku] = item
        self._categories.add(item.category)
        self._name_view = None

    def get(self, sku: str) -> Item:
        """Найти предмет по артикулу за O(1); нет такого → ItemNotFoundError."""
        key = sku.strip().upper() if isinstance(sku, str) else sku
        try:
            return self._by_sku[key]
        except KeyError:
            raise ItemNotFoundError(f"Предмета с артикулом {sku!r} нет на складе") from None

    def remove(self, sku: str) -> Item:
        """Удалить предмет и вернуть его."""
        item = self.get(sku)
        self._items.remove(item)  # O(n): список приходится сдвигать
        del self._by_sku[item.sku]
        self._name_view = None
        self._rebuild_categories()
        return item

    def update(self, sku: str, name: Optional[str] = None, category: Optional[str] = None) -> Item:
        """Изменить название и/или категорию. Сначала проверяются оба значения, потом применяются."""
        item = self.get(sku)
        new_name = item.name if name is None else normalize_name(name)
        new_category = item.category if category is None else normalize_category(category)
        item._name = new_name
        item._category = new_category
        self._name_view = None
        self._rebuild_categories()
        return item

    def categories(self) -> list[str]:
        """Уникальные категории по алфавиту."""
        return merge_sort(self._categories, key=str.casefold)

    def sorted_by(self, field: str, reverse: bool = False) -> list[Item]:
        """Вернуть предметы, упорядоченные по полю sku/name/category/on_hand (собственная сортировка)."""
        if field not in SORT_FIELDS:
            raise ValidationError(f"Нельзя сортировать по {field!r}; доступно: {', '.join(SORT_FIELDS)}")
        return merge_sort(self._items, key=SORT_FIELDS[field], reverse=reverse)

    def search(self, mode: str, query: str) -> list[Item]:
        """Найти предметы: mode = sku | prefix | contains | category."""
        text = query.strip() if isinstance(query, str) else ""
        if not text:
            raise ValidationError("Пустой поисковый запрос")
        needle = text.casefold()
        if mode == "sku":
            try:
                return [self.get(text)]
            except ItemNotFoundError:
                return []
        if mode == "prefix":
            return self._search_prefix(needle)
        if mode == "contains":
            return linear_find_all(self._items, lambda item: needle in item.name.casefold())
        if mode == "category":
            return linear_find_all(self._items, lambda item: item.category.casefold() == needle)
        raise ValidationError(f"Неизвестный режим поиска {mode!r}")

    def _search_prefix(self, prefix: str) -> list[Item]:
        """Бинарный поиск по началу названия.

        Предусловие: представление отсортировано по casefold-названию, а prefix тоже casefold.
        Все названия с этим началом идут подряд, начиная с точки вставки prefix.
        Сложность: O(log n + k) после одной сортировки O(n log n), которая кэшируется.
        """
        if self._name_view is None:
            self._name_view = merge_sort(self._items, key=_name_key)
        view = self._name_view
        index = binary_search_left(view, prefix, key=_name_key)
        found: list[Item] = []
        while index < len(view) and _name_key(view[index]).startswith(prefix):
            found.append(view[index])
            index += 1
        return found

    def _rebuild_categories(self) -> None:
        self._categories = {item.category for item in self._items}


class Workshop:
    """Мастерская: владеет складом, журналом выдач и очередью заявок (композиция)."""

    def __init__(self, today: Callable[[], date] = date.today) -> None:
        self._today = today
        self.inventory = Inventory()
        self._loans: list[Loan] = []  # номера растут → список всегда отсортирован по loan_id
        self._waitlist: deque[LoanRequest] = deque()
        self._next_loan_id = 1

    # ----- записи о предметах

    def add_item(self, item: Item) -> None:
        self.inventory.add(item)
        logger.info("Добавлен предмет %s «%s»", item.sku, item.name)

    def update_item(self, sku: str, name: Optional[str] = None, category: Optional[str] = None) -> Item:
        item = self.inventory.update(sku, name, category)
        logger.info("Изменён предмет %s: «%s», категория %s", item.sku, item.name, item.category)
        return item

    def remove_item(self, sku: str) -> Item:
        """Удалить предмет, если он не выдан и на него нет заявок."""
        item = self.inventory.get(sku)
        if any(loan.sku == item.sku and loan.is_active for loan in self._loans):
            raise ItemInUseError(f"{item.sku}: есть невозвращённые выдачи, удалить нельзя")
        if any(request.sku == item.sku for request in self._waitlist):
            raise ItemInUseError(f"{item.sku}: на предмет есть заявки в очереди, удалить нельзя")
        self.inventory.remove(item.sku)
        logger.info("Удалён предмет %s «%s»", item.sku, item.name)
        return item

    def restock(self, sku: str, amount: int) -> list[Loan]:
        """Пополнить запас и сразу обслужить очередь. Возвращает выдачи, сделанные из очереди."""
        item = self.inventory.get(sku)
        item.add_stock(amount)
        logger.info("Пополнение %s на %s", item.sku, amount)
        return self._serve_waitlist()

    # ----- выдачи и очередь

    def issue(self, sku: str, borrower: str, quantity: int) -> Loan:
        """Выдать предмет сразу; при нехватке — InsufficientStockError."""
        borrower = normalize_person(borrower)
        quantity = _require_int(quantity, "Количество", minimum=1)
        item = self.inventory.get(sku)
        item.take(quantity)
        loan = Loan(self._next_loan_id, item.sku, borrower, quantity, self._today(), returnable=item.returnable)
        self._next_loan_id += 1
        self._loans.append(loan)
        logger.info("Выдача №%s: %s ×%s → %s", loan.loan_id, loan.sku, loan.quantity, loan.borrower)
        return loan

    def request_item(self, sku: str, borrower: str, quantity: int) -> Union[Loan, LoanRequest]:
        """Выдать предмет или, если его нет, поставить заявку в очередь.

        Если на этот предмет уже кто-то ждёт, новая заявка встаёт в очередь, даже когда
        запас позволяет выдать: иначе тот, кто пришёл позже, обгонял бы ждущих.
        """
        borrower = normalize_person(borrower)
        quantity = _require_int(quantity, "Количество", minimum=1)
        item = self.inventory.get(sku)
        if not item.can_ever_issue(quantity):
            raise ValidationError(f"«{item.name}»: запрос на {quantity} шт. невыполним — столько не бывает")
        queue_exists = any(request.sku == item.sku for request in self._waitlist)
        if not queue_exists and item.can_issue(quantity):
            return self.issue(item.sku, borrower, quantity)
        request = LoanRequest(borrower, item.sku, quantity, self._today())
        self._waitlist.append(request)
        logger.info("Заявка в очередь: %s ×%s → %s", request.sku, request.quantity, request.borrower)
        return request

    def find_loan(self, loan_id: int) -> Loan:
        """Найти выдачу по номеру бинарным поиском.

        Предусловие: журнал отсортирован по loan_id — номера выдаются по возрастанию и
        выдачи никогда не удаляются; при загрузке из файла порядок проверяется.
        """
        index = binary_search(self._loans, loan_id, key=lambda loan: loan.loan_id)
        if index == -1:
            raise LoanNotFoundError(f"Выдачи с номером {loan_id} нет в журнале")
        return self._loans[index]

    def return_loan(self, loan_id: int) -> tuple[Loan, list[Loan]]:
        """Принять возврат. Возвращает (закрытая выдача, выдачи, сделанные из очереди)."""
        loan = self.find_loan(loan_id)
        if not loan.returnable:
            raise ValidationError(f"Выдача №{loan_id} — расходный материал, возврату не подлежит")
        if loan.returned_on is not None:
            raise ValidationError(f"Выдача №{loan_id} уже закрыта {loan.returned_on.isoformat()}")
        self.inventory.get(loan.sku).give_back(loan.quantity)
        loan.returned_on = self._today()
        logger.info("Возврат по выдаче №%s: %s ×%s", loan.loan_id, loan.sku, loan.quantity)
        return loan, self._serve_waitlist()

    def _serve_waitlist(self) -> list[Loan]:
        """Обслужить очередь: для каждого предмета строго по порядку (FIFO).

        Заявки на разные предметы друг другу не мешают. Но если заявка на предмет X не может
        быть выполнена, все более поздние заявки на X тоже ждут (артикул попадает в ``blocked``):
        иначе маленькая заявка обгоняла бы раннюю большую, и та могла бы ждать вечно.
        Возвращает сделанные выдачи.
        """
        served: list[Loan] = []
        pending: deque[LoanRequest] = deque()
        blocked: set[str] = set()
        while self._waitlist:
            request = self._waitlist.popleft()  # O(1): у list.pop(0) было бы O(n)
            item = self.inventory.get(request.sku)
            if request.sku not in blocked and item.can_issue(request.quantity):
                served.append(self.issue(request.sku, request.borrower, request.quantity))
            else:
                blocked.add(request.sku)
                pending.append(request)
        self._waitlist = pending
        return served

    def iter_active_loans(self) -> Iterator[Loan]:
        """Генератор: невозвращённые выдачи по одной."""
        for loan in self._loans:
            if loan.is_active:
                yield loan

    def active_loans(self) -> list[Loan]:
        return list(self.iter_active_loans())

    def waitlist(self) -> list[LoanRequest]:
        """Копия очереди в порядке ожидания."""
        return list(self._waitlist)

    def waitlist_for(self, sku: str) -> list[LoanRequest]:
        key = sku.strip().upper()
        return [request for request in self._waitlist if request.sku == key]

    # ----- отчёт и сериализация

    def build_report(self) -> dict[str, Any]:
        """Итоговый отчёт: что заканчивается, у кого что на руках, сводка по категориям, очередь."""
        attention = []
        categories: dict[str, dict[str, int]] = {}
        tools = consumables = 0
        for item in self.inventory:
            problem = item.needs_attention()  # полиморфизм: у каждого типа своё условие
            if problem:
                attention.append({"sku": item.sku, "name": item.name, "kind": item.kind, "problem": problem})
            entry = categories.setdefault(item.category, {"positions": 0, "units_on_hand": 0})
            entry["positions"] += 1
            entry["units_on_hand"] += item.on_hand
            if item.kind == ReusableTool.kind:
                tools += 1
            else:
                consumables += 1

        by_borrower: dict[str, list[dict[str, Any]]] = {}
        for loan in self.iter_active_loans():
            by_borrower.setdefault(loan.borrower, []).append(
                {
                    "loan_id": loan.loan_id,
                    "sku": loan.sku,
                    "name": self.inventory.get(loan.sku).name,
                    "quantity": loan.quantity,
                    "issued_on": loan.issued_on.isoformat(),
                }
            )

        ordered_categories = dict(merge_sort(categories.items(), key=lambda pair: pair[0].casefold()))
        return {
            "generated_on": self._today().isoformat(),
            "totals": {
                "positions": len(self.inventory),
                "tools": tools,
                "consumables": consumables,
                "active_loans": sum(len(rows) for rows in by_borrower.values()),
                "waiting_requests": len(self._waitlist),
            },
            "needs_attention": attention,
            "by_category": ordered_categories,
            "active_loans_by_borrower": by_borrower,
            "waitlist": [request.to_dict() for request in self._waitlist],
        }

    def to_dict(self) -> dict[str, Any]:
        """Полное состояние для сохранения в JSON."""
        return {
            "version": STATE_VERSION,
            "saved_on": self._today().isoformat(),
            "next_loan_id": self._next_loan_id,
            "items": [item.to_dict() for item in self.inventory],
            "loans": [loan.to_dict() for loan in self._loans],
            "waitlist": [request.to_dict() for request in self._waitlist],
        }

    @classmethod
    def from_dict(cls, data: Any, today: Callable[[], date] = date.today) -> "Workshop":
        """Восстановить состояние из словаря; любые нарушения структуры → ValidationError."""
        if not isinstance(data, dict):
            raise ValidationError("Состояние должно быть JSON-объектом")
        if data.get("version") != STATE_VERSION:
            raise ValidationError(f"Неподдерживаемая версия состояния: {data.get('version')!r}")
        workshop = cls(today)
        try:
            for raw in data["items"]:
                workshop.inventory.add(item_from_dict(raw))
            loans = [Loan.from_dict(raw) for raw in data["loans"]]
            requests = [LoanRequest.from_dict(raw) for raw in data["waitlist"]]
            next_loan_id = _require_int(data["next_loan_id"], "next_loan_id", minimum=1)
        except KeyError as exc:
            raise ValidationError(f"В состоянии нет поля {exc.args[0]!r}") from exc
        except (TypeError, AttributeError) as exc:
            raise ValidationError(f"Неверная структура состояния: {exc}") from exc

        if not is_sorted(loans, key=lambda loan: loan.loan_id):
            logger.warning("Журнал выдач в файле не упорядочен по номеру — сортирую")
            loans = merge_sort(loans, key=lambda loan: loan.loan_id)
        ids = [loan.loan_id for loan in loans]
        if len(set(ids)) != len(ids):
            raise ValidationError("В журнале выдач повторяются номера")
        if ids and next_loan_id <= ids[-1]:
            raise ValidationError("next_loan_id не больше уже выданных номеров")
        for request in requests:
            if request.sku not in workshop.inventory:
                raise ValidationError(f"Заявка ссылается на несуществующий артикул {request.sku}")
        workshop._loans = loans
        workshop._waitlist = deque(requests)
        workshop._next_loan_id = next_loan_id
        return workshop
