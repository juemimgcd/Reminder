from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.mneme.bootstrap.lifespan import lifespan
from app.mneme.bootstrap.root_routes import router as root_router
from app.mneme.bootstrap.router_registry import register_routers
from app.mneme.conf.config import settings
from app.mneme.utils.exceptions import BusinessException, business_exception_handler


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


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
    )
    configure_cors(app)
    configure_exception_handlers(app)
    app.include_router(root_router)
    register_routers(app)
    return app
