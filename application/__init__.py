from dblib import database
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status

from . import models
from .router import AsyncCRUDRouter
from .settings import Settings


def setup_application() -> FastAPI:
    settings = Settings()
    database.create_tables()
    debug = settings.log_level.upper() == "DEBUG"
    app = FastAPI(debug=debug)
    crud = crudrouter()
    app.include_router(crud, prefix="/crud")
    wrapper = app.get("/health", tags=["Health"])
    wrapper(check)
    return app


def crudrouter() -> APIRouter:
    router = APIRouter()
    for package in models.find_packages():
        prefix = package.__name__.replace("dblib.models.", "").lower()
        pkg_router = APIRouter(prefix=f"/{prefix}")
        for model in models.find_data_models(package):
            crud = AsyncCRUDRouter(sql_model=model)
            pkg_router.include_router(crud)
        router.include_router(pkg_router)
    return router


async def check():
    try:
        async with database.connection() as db:
            await db.connection()
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
