import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api.ai_models import router as ai_models_router
from app.api.audit import router as audit_router
from app.api.control import router as control_router
from app.api.discovery import router as discovery_router
from app.api.gate import router as gate_router
from app.api.regulatory import router as regulatory_router
from app.api.risk import router as risk_router
from app.config import get_settings
from app.database import SessionLocal
from app.errors import register_error_handlers
from app.services.regulatory_seed import seed_regulatory_mappings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db = SessionLocal()
    try:
        seed_regulatory_mappings(db)
    except OperationalError:
        # Tables don't exist yet — migrations haven't run against this DB.
        # Real deployments run `alembic upgrade head` before starting the
        # app, so this path isn't expected there; it protects test apps that
        # point get_db at their own isolated DB via a dependency override,
        # which this lifespan (bound to the production engine) can't see.
        logger.warning("Skipped regulatory mapping seed: tables not present yet")
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(ai_models_router)
    app.include_router(risk_router)
    app.include_router(regulatory_router)
    app.include_router(control_router)
    app.include_router(gate_router)
    app.include_router(audit_router)
    app.include_router(discovery_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "environment": settings.environment}

    return app


app = create_app()
