from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.mneme.bootstrap.lifespan import lifespan
from app.mneme.bootstrap.root_routes import router as root_router
from app.mneme.bootstrap.router_registry import register_routers
from app.mneme.conf.config import settings
from app.mneme.api.errors import BusinessException, business_exception_handler, unhandled_exception_handler


REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST_DIR = REPO_ROOT / "app" / "mneme_frontend_v0.2.1" / "dist"


def configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX or None,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )


def configure_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def configure_trusted_hosts(app: FastAPI) -> None:
    if settings.TRUSTED_HOSTS:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)


def configure_frontend(app: FastAPI) -> None:
    @app.get("/{frontend_path:path}", include_in_schema=False)
    async def frontend_entry(frontend_path: str):
        index_file = FRONTEND_DIST_DIR / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404)

        if not frontend_path:
            return FileResponse(FRONTEND_DIST_DIR / "index.html")

        candidate = (FRONTEND_DIST_DIR / frontend_path).resolve()
        try:
            candidate.relative_to(FRONTEND_DIST_DIR.resolve())
        except ValueError:
            return FileResponse(FRONTEND_DIST_DIR / "index.html")

        if candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(FRONTEND_DIST_DIR / "index.html")


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
    )
    configure_cors(app)
    configure_trusted_hosts(app)
    configure_exception_handlers(app)
    app.include_router(root_router)
    register_routers(app)
    configure_frontend(app)
    return app
