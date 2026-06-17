from contextlib import asynccontextmanager
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.routes.access import router as access_router
from app.routes.audit import router as audit_router
from app.routes.auth import router as auth_router
from app.routes.checkers import router as checkers_router
from app.routes.residents import router as residents_router
from app.routes.units import router as units_router
from app.routes.cleanup import router as cleanup_router

logger = logging.getLogger("cleanup")


async def run_periodic_cleanup():
    while True:
        try:
            await asyncio.sleep(settings.CLEANUP_INTERVAL_SECONDS)
            from app.core.database import async_session_factory
            from app.services.cleanup_service import CleanupService
            async with async_session_factory() as session:
                svc = CleanupService(session)
                results = await svc.cleanup_all()
                logger.info(f"Periodic cleanup completed: {results}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(run_periodic_cleanup())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


async def custom_rate_limit_handler(request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Hardware-Bound Offline QR Access Control System",
        lifespan=lifespan,
    )

    # Wire slowapi Limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

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
    app.include_router(cleanup_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()