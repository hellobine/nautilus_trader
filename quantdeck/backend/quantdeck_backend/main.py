from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from quantdeck_backend.api import catalog, config, downloads, health, ws
from quantdeck_backend.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="QuantDeck API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(ws.router)
    app.include_router(config.router)
    app.include_router(catalog.router)
    app.include_router(downloads.router)
    return app


app = create_app()
