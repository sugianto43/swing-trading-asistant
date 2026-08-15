from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ExceptionHandler

from app.api.v1.routes.backtests import router as backtests_router
from app.api.v1.routes.calendar import router as calendar_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.indicators import router as indicators_router
from app.api.v1.routes.instruments import router as instruments_router
from app.api.v1.routes.performance import router as performance_router
from app.api.v1.routes.positions import router as positions_router
from app.api.v1.routes.risk import router as risk_router
from app.api.v1.routes.scanner import router as scanner_router
from app.config import get_settings
from app.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(
        RequestValidationError, cast(ExceptionHandler, validation_exception_handler)
    )
    app.add_exception_handler(
        StarletteHTTPException, cast(ExceptionHandler, http_exception_handler)
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router, prefix=settings.api_v1_prefix)
    app.include_router(instruments_router, prefix=settings.api_v1_prefix)
    app.include_router(indicators_router, prefix=settings.api_v1_prefix)
    app.include_router(scanner_router, prefix=settings.api_v1_prefix)
    app.include_router(backtests_router, prefix=settings.api_v1_prefix)
    app.include_router(risk_router, prefix=settings.api_v1_prefix)
    app.include_router(positions_router, prefix=settings.api_v1_prefix)
    app.include_router(performance_router, prefix=settings.api_v1_prefix)
    app.include_router(calendar_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
