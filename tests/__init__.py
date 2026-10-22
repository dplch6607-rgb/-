"""Тесты проекта. Запуск из корня: ``python -m unittest -v``."""
import logging

# Чтобы предупреждения модулей не засоряли вывод тестов (assertLogs при этом продолжает работать).
logging.getLogger("workshop").addHandler(logging.NullHandler())
