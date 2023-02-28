from copy import deepcopy
import re
from typing import Any, Callable, Coroutine, Optional, Type, TypeAlias, TypeVar
from uuid import UUID

from dblib import database
from fastapi import APIRouter, Depends, HTTPException
from pydantic import create_model
from sqlalchemy import select
from sqlalchemy.sql import Delete, Select
from sqlmodel import SQLModel
from starlette import status

PAGINATION: TypeAlias = dict[str, Optional[int]]
CALLABLE_LIST: TypeAlias = Callable[..., Coroutine[Any, Any, list[SQLModel]]]
CALLABLE: TypeAlias = Callable[..., Coroutine[Any, Any, SQLModel]]
Q = TypeVar("Q", Select, Delete)
T = TypeVar("T", bound=SQLModel)


class AsyncCRUDRouter(APIRouter):
    sql_model: Type[SQLModel]
    exclude: set = {"created_at", "updated_at", "id"}
    pk_field: str = "uuid"
    pk_type: Type = UUID

    def __init__(
        self,
        sql_model: Type[SQLModel],
    ):
        exclude = deepcopy(self.exclude)
        self.pagination = _pagination_factory(max_limit=None)
        self.sql_model = sql_model
        model_name = sql_model.__name__
        category = sql_model.__module__.split(".")[-1]
        tag = f"{category.capitalize()} - {_make_spaces(model_name)}"
        self.schema = _schema_factory(sql_model, exclude, "Schema")
        exclude.add(self.pk_field)
        self.create_schema = _schema_factory(sql_model, exclude, "Create")
        self.update_schema = _schema_factory(sql_model, exclude, "Update")
        # super().__init__(
        #     schema=schema,
        #     db_model=sql_model,
        #     create_schema=create_schema,
        #     update_schema=update_schema,
        #     db=database.connection,
        #     prefix=f"/{model_name}",
        #     tags=[tag],
        # )
        super().__init__(prefix=f"/{model_name}", tags=[tag])

        NOT_FOUND = HTTPException(404, "Not Found")

        super().add_api_route(
            "",
            self._get_all(),
            methods=["GET"],
            response_model=Optional[list[self.schema]],  # type: ignore
            summary="Get All",
        )

        super().add_api_route(
            "",
            self._create(),
            methods=["POST"],
            response_model=self.schema,
            summary="Create One",
        )

        super().add_api_route(
            "",
            self._delete_all(),
            methods=["DELETE"],
            response_model=Optional[list[self.schema]],  # type: ignore
            summary="Delete All",
        )

        super().add_api_route(
            "/{uuid}",
            self._get_one(),
            methods=["GET"],
            response_model=self.schema,
            summary="Get One",
            responses=self._error_responses(NOT_FOUND),
        )

        super().add_api_route(
            "/{uuid}",
            self._update(),
            methods=["PATCH"],
            response_model=self.schema,
            summary="Update One",
            responses=self._error_responses(NOT_FOUND),
        )

        super().add_api_route(
            "/{uuid}",
            self._delete_one(),
            methods=["DELETE"],
            response_model=self.schema,
            summary="Delete One",
            responses=self._error_responses(NOT_FOUND),
        )

    @staticmethod
    def _error_responses(*errors: HTTPException) -> dict[int, dict[str, str]]:
        responses = {err.status_code: {"detail": err.detail} for err in errors}
        return responses

    async def _database(self) -> database.SESSION:
        async with database.connection() as db:
            yield db

    def _get_all(self, *args: Any, **kwargs: Any) -> CALLABLE_LIST:
        async def route(
            pagination: PAGINATION = self.pagination,
            db: database.SESSION = Depends(self._database),
        ) -> list[self.sql_model]:  # type: ignore
            skip, limit = pagination.get("skip"), pagination.get("limit")
            statement = select(self.sql_model)
            statement = (
                statement.order_by(getattr(self.sql_model, self.pk_field))
                .limit(limit)
                .offset(skip)
            )
            results = await db.execute(statement)
            return results.scalars().all()

        return route

    def _get_one(self, *args: Any, **kwargs: Any) -> CALLABLE:
        async def route(
            uuid: self.pk_type,  # type: ignore
            db: database.SESSION = Depends(self._database),
        ) -> self.sql_model:  # type: ignore
            statement = select(self.sql_model)
            statement = statement.where(getattr(self.sql_model, self.pk_field) == uuid)
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
            db: database.SESSION = Depends(self._database),
        ) -> self.sql_model:
            db_model = self.sql_model(**model.dict())
            db.add(db_model)
            await db.commit()
            await db.refresh(db_model)
            return db_model

        return route

    def _update(self, *args: Any, **kwargs: Any) -> CALLABLE:
        async def route(
            uuid: self.pk_type,  # type: ignore
            model: self.update_schema,  # type: ignore
            db: database.SESSION = Depends(self._database),
        ) -> self.sql_model:
            get_one = self._get_one()
            db_model = await get_one(uuid, db)
            for key, value in model.dict(exclude={self.pk_field}).items():
                if hasattr(db_model, key):
                    setattr(db_model, key, value)
            await db.commit()
            await db.refresh(db_model)
            return db_model

        return route

    def _delete_all(self, *args: Any, **kwargs: Any) -> CALLABLE_LIST:
        async def route(
            db: database.SESSION = Depends(self._database),
        ) -> list[self.sql_model]:
            statement = select(self.sql_model)
            results = await db.execute(statement)
            for result in results.scalars().all():
                await db.delete(result)

            get_remaining = self._get_all()
            remaining = await get_remaining({"skip": 0, "limit": None}, db)
            return remaining

        return route

    def _delete_one(self, *args: Any, **kwargs: Any) -> CALLABLE:
        async def route(
            uuid: self.pk_type,  # type: ignore
            db: database.SESSION = Depends(self._database),
        ):
            get_one = self._get_one()
            one = await get_one(uuid, db)
            await db.delete(one)

        return route

    def __hash__(self):
        return hash(self.sql_model)


def _schema_factory(schema_cls: Type[T], exclude: set = set(), action: str = "Create"):
    """
    Used in place of fastapi-crudrouter's schema_factory, due to alternate naming conventions required.
    """

    fields = {
        f.name: (f.type_, ...)
        for f in schema_cls.__fields__.values()
        if f.name not in exclude
    }

    *_, module = schema_cls.__module__.split(".")
    name = schema_cls.__name__
    model_name = f"{module}{name}{action}"
    schema: Type[T] = create_model(__model_name=model_name, **fields)  # type: ignore
    return schema


def _pagination_factory(max_limit: Optional[int] = None) -> Any:
    """
    Created the pagination dependency to be used in the router
    """

    def pagination(skip: int = 0, limit: Optional[int] = max_limit) -> PAGINATION:
        if skip < 0:
            raise _create_query_validation_exception(
                field="skip",
                msg="skip query parameter must be greater or equal to zero",
            )

        if limit is not None:
            if limit <= 0:
                raise _create_query_validation_exception(
                    field="limit", msg="limit query parameter must be greater then zero"
                )

            elif max_limit and max_limit < limit:
                raise _create_query_validation_exception(
                    field="limit",
                    msg=f"limit query parameter must be less then {max_limit}",
                )

        return {"skip": skip, "limit": limit}

    return Depends(pagination)


def _create_query_validation_exception(field: str, msg: str) -> HTTPException:
    return HTTPException(
        422,
        detail={
            "detail": [
                {"loc": ["query", field], "msg": msg, "type": "type_error.integer"}
            ]
        },
    )


def _make_spaces(phrase: str) -> str:
    capitalized = "[A-Z][a-z]+"
    acronym = "[A-Z]+(?=[A-Z])"
    regex = f"({acronym}|{capitalized})"
    words = re.findall(regex, phrase)
    return " ".join(words)
