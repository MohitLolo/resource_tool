from __future__ import annotations

import importlib
import inspect
import pkgutil

from app.core.base import BaseProcessor


class ProcessorRegistry:
    _processors: dict[str, type[BaseProcessor]] = {}

    @classmethod
    def clear(cls) -> None:
        cls._processors.clear()

    @classmethod
    def register(cls, processor_class: type[BaseProcessor]) -> None:
        if not issubclass(processor_class, BaseProcessor):
            raise TypeError("processor_class must inherit BaseProcessor")
        if not processor_class.name:
            raise ValueError("processor_class.name is required")
        cls._processors[processor_class.name] = processor_class

    @classmethod
    def get(cls, name: str) -> BaseProcessor:
        if name not in cls._processors:
            raise KeyError(f"Processor not found: {name}")
        return cls._processors[name]()

    @classmethod
    def list_by_category(cls, category: str) -> list[dict]:
        return [item for item in cls.list_all() if item["category"] == category]

    @classmethod
    def list_all(cls) -> list[dict]:
        items = []
        for processor_name in sorted(cls._processors):
            processor = cls._processors[processor_name]
            items.append(
                {
                    "name": processor.name,
                    "label": processor.label,
                    "category": processor.category,
                    "params_schema": processor.params_schema,
                }
            )
        return items

    @classmethod
    def auto_discover(cls, package_name: str = "app.processors") -> None:
        package = importlib.import_module(package_name)
        if not hasattr(package, "__path__"):
            return

        for _, module_name, _ in pkgutil.walk_packages(
            package.__path__, prefix=f"{package.__name__}."
        ):
            module = importlib.import_module(module_name)
            for _, member in inspect.getmembers(module, inspect.isclass):
                if member is BaseProcessor:
                    continue
                if not issubclass(member, BaseProcessor):
                    continue
                if member.__module__ != module.__name__:
                    continue
                cls.register(member)
