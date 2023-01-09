import importlib
import os
import pkgutil
from types import ModuleType
from typing import Iterator, Type, TypeVar

from dblib import models
from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)


def find_packages() -> Iterator[ModuleType]:
    pkgpath = os.path.dirname(models.__file__)
    for _, name, _ in pkgutil.iter_modules([pkgpath]):
        if not name.startswith("_"):
            module = importlib.import_module(f"dblib.models.{name}")
            yield module


def find_data_models(package: ModuleType) -> Iterator[Type[SQLModel]]:
    trimmed = (
        getattr(package, model) for model in dir(package) if not model.startswith("_")
    )
    return filter(
        lambda m: m.__module__ == package.__name__,
        filter(lambda m: hasattr(m, "__table__"), trimmed),
    )
