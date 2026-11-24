from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import auth, conversations, workspaces
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    application_settings = settings or get_settings()
    if application_settings.secret_key is None or len(
        application_settings.secret_key.get_secret_value()
    ) < 32:
        raise ValueError("SECRET_KEY must contain at least 32 characters before starting the API")

    engine = create_async_engine(application_settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(title="agentic-rag-live-memory API", version="0.1.0", lifespan=lifespan)
    app.state.settings = application_settings
    app.state.session_factory = session_factory
    app.state.engine = engine
    app.add_middleware(
        CORSMiddleware,
        allow_origins=application_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(workspaces.router, prefix="/api/v1")
    app.include_router(conversations.router, prefix="/api/v1")

    @app.get("/health")
    async def health(response: Response) -> dict[str, str]:
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unhealthy", "database": "unavailable"}
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
