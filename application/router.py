import string
from typing import Any, Callable, Coroutine, Optional, Type, TypeAlias, TypeVar

from dblib import database
from fastapi import Depends, HTTPException
from fastapi_crudrouter import SQLAlchemyCRUDRouter  # type: ignore
from sqlalchemy import select
from sqlalchemy.sql import Delete, Select
from sqlmodel import SQLModel
from starlette import status

PAGINATION: TypeAlias = dict[str, Optional[int]]
CALLABLE_LIST: TypeAlias = Callable[..., Coroutine[Any, Any, list[SQLModel]]]
CALLABLE: TypeAlias = Callable[..., Coroutine[Any, Any, SQLModel]]
NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
ST = TypeVar("ST", Select, Delete)


class AsyncCRUDRouter(SQLAlchemyCRUDRouter):
    sql_model: Type[SQLModel]

    def __init__(
        self,
        sql_model: Type[SQLModel],
    ):
        self.sql_model = sql_model
        model_name = sql_model.__name__
        category = sql_model.__module__.split(".")[-1]
        name = self._spaces_on_capital(model_name)
        tag = f"{category.capitalize()} - {name}"
        super().__init__(
            schema=sql_model,
            db_model=sql_model,
            db=database.connection,
            prefix=f"/{model_name}",
            tags=[tag],
        )

    @staticmethod
    def _spaces_on_capital(phrase: str) -> str:
        chars = []
        for index, char in enumerate(phrase):
            if index > 0 and char in string.ascii_uppercase:
                chars.append(" ")
            chars.append(char)
        capitalized = "".join(chars)
        return capitalized

    @staticmethod
    async def database():
        async with database.connection() as db:
            yield db

    def _get_all(self, *args: Any, **kwargs: Any) -> CALLABLE_LIST:
        async def route(
            pagination: PAGINATION = self.pagination,
            db: database.SESSION = Depends(self.database),
        ) -> list[self.db_model]:  # type: ignore
            skip, limit = pagination.get("skip"), pagination.get("limit")
            statement = select(self.db_model)
            statement = (
                statement.order_by(getattr(self.db_model, self._pk))
                .limit(limit)
                .offset(skip)
            )
            results = await db.execute(statement)
            return results.scalars().all()

        return route

    def _get_one(self, *args: Any, **kwargs: Any) -> CALLABLE:
        async def route(
            item_id: self._pk_type,  # type: ignore
            db: database.SESSION = Depends(self.database),
        ) -> self.db_model:  # type: ignore
            statement = select(self.db_model)
            statement = statement.where(getattr(self.db_model, self._pk) == item_id)
            results = await db.execute(statement)
            items = results.first()
            if items:
                return items[0]
            detail = f"{self.sql_model.__name__.lower()} not found"
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

        return route

    def _create(self, *args: Any, **kwargs: Any) -> CALLABLE:
        async def route(
            model: self.create_schema,  # type: ignore
            db: database.SESSION = Depends(self.database),
        ):
            db_model = self.db_model(**model.dict())
            db.add(db_model)
            await db.commit()
            await db.refresh(db_model)
            return db_model

        return route

    def _update(self, *args: Any, **kwargs: Any) -> CALLABLE:
        async def route(
            item_id: self._pk_type,  # type: ignore
            model: self.update_schema,  # type: ignore
            db: database.SESSION = Depends(self.database),
        ):
            get_one = self._get_one()
            db_model = await get_one(item_id, db)
            for key, value in model.dict(exclude={self._pk}).items():
                if hasattr(db_model, key):
                    setattr(db_model, key, value)
            await db.commit()
            await db.refresh(db_model)
            return db_model

        return route

    def _delete_all(self, *args: Any, **kwargs: Any) -> CALLABLE_LIST:
        async def route(
            db: database.SESSION = Depends(self.database),
        ) -> list[SQLModel]:
            statement = select(self.db_model)
            results = await db.execute(statement)
            for result in results.scalars().all():
                await db.delete(result)

            get_remaining = self._get_all()
            remaining = await get_remaining({"skip": 0, "limit": None}, db)
            return remaining

        return route

    def _delete_one(self, *args: Any, **kwargs: Any) -> CALLABLE:
        async def route(
            item_id: self._pk_type,  # type: ignore
            db: database.SESSION = Depends(self.database),
        ):
            get_one = self._get_one()
            one = await get_one(item_id, db)
            await db.delete(one)
            return one

        return route

    def __hash__(self):
        return hash(self.sql_model)
