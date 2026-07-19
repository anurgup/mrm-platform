"""Domain exceptions and their mapping to a consistent HTTP error envelope:
{"error": {"type": "...", "message": "..."}}"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for domain-level errors that carry their own HTTP status."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DuplicateModelError(DomainError):
    status_code = 409


class ModelNotFoundError(DomainError):
    status_code = 404


class AssessmentNotFoundError(DomainError):
    status_code = 404


class DuplicateRegulatoryMappingError(DomainError):
    status_code = 409


class RegulatoryMappingNotFoundError(DomainError):
    status_code = 404


class FindingNotFoundError(DomainError):
    status_code = 404


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"type": type(exc).__name__, "message": exc.message}},
        )
