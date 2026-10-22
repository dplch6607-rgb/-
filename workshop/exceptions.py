"""Исключения предметной области.

Все ожидаемые ошибки приложения наследуются от WorkshopError, поэтому интерфейс может
перехватить их одним ``except WorkshopError`` и показать понятное сообщение, не скрывая
при этом непредвиденные ошибки (TypeError, ZeroDivisionError и т. п.).
"""


class WorkshopError(Exception):
    """Базовое исключение приложения."""


class ValidationError(WorkshopError, ValueError):
    """Некорректное значение поля, пользовательского ввода или данных файла."""


class DuplicateItemError(WorkshopError):
    """Предмет с таким артикулом уже есть на складе."""


class ItemNotFoundError(WorkshopError):
    """Предмета с таким артикулом нет на складе."""


class InsufficientStockError(WorkshopError):
    """На складе меньше, чем запрошено."""


class ItemInUseError(WorkshopError):
    """Предмет нельзя удалить: он выдан или на него есть заявки."""


class LoanNotFoundError(WorkshopError):
    """Выдачи с таким номером нет в журнале."""


class StorageError(WorkshopError):
    """Файл не найден, не читается, повреждён или не может быть записан."""
