from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai_models import router as ai_models_router
from app.api.risk import router as risk_router
from app.config import get_settings
from app.errors import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

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

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "environment": settings.environment}

    return app


app = create_app()
