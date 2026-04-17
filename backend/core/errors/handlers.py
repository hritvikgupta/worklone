"""FastAPI exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.core.errors.exceptions import AppError
from backend.core.logging import get_logger

logger = get_logger("errors")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        log_message = exc.log_message or exc.message
        if exc.status_code >= 500:
            logger.error("%s path=%s details=%s", log_message, request.url.path, exc.details)
        else:
            logger.warning("%s path=%s details=%s", log_message, request.url.path, exc.details)
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        logger.warning("HTTP exception path=%s status=%s detail=%s", request.url.path, exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": str(exc.detail),
                    "retryable": False,
                    "details": {"status_code": exc.status_code},
                },
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "The server could not complete the request.",
                    "retryable": False,
                    "details": {},
                },
            },
        )
