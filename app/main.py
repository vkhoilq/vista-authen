from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes.access import router as access_router
from app.routes.audit import router as audit_router
from app.routes.auth import router as auth_router
from app.routes.checkers import router as checkers_router
from app.routes.residents import router as residents_router
from app.routes.units import router as units_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Hardware-Bound Offline QR Access Control System",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all API routers
    app.include_router(units_router, prefix="/api/v1")
    app.include_router(residents_router, prefix="/api/v1")
    app.include_router(checkers_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(access_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()