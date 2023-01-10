from dblib import database
from fastapi import APIRouter, FastAPI, HTTPException, status

from .router import AsyncCRUDRouter


def setup_application(debug: bool) -> FastAPI:
    app = FastAPI(debug=debug)
    crud = crudrouter()
    app.include_router(crud, prefix="/crud")
    wrapper = app.get("/health", tags=["Health"])
    wrapper(check)
    return app


def crudrouter() -> APIRouter:
    router = APIRouter()
    data_models = database.data_models()
    for name, models in data_models.items():
        pkg_router = APIRouter(prefix=f"/{name}")
        for model in models:
            model_router = AsyncCRUDRouter(sql_model=model)
            pkg_router.include_router(model_router)
        router.include_router(pkg_router)
    return router


async def check():
    try:
        async with database.connection() as db:
            await db.connection()
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
