import os

os.environ.setdefault("SECRET_KEY", "test-only-signing-key-that-is-long-enough")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import Settings
from app.db.base import Base
from app.db.models import User
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        secret_key=SecretStr("test-only-signing-key-that-is-long-enough"),
    )
    app = create_app(settings)

    async def create_tables():
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, email: str = "person@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 201
    return response.json()


def test_registration_login_and_password_hashing(client: TestClient):
    account = register(client, "Person@Example.com")
    assert account["user"]["email"] == "person@example.com"

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": "correct-horse-battery-staple"},
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "wrong-password"},
    )
    assert invalid_login.status_code == 401

    async def stored_user():
        async with client.app.state.session_factory() as session:
            return await session.scalar(select(User).where(User.email == "person@example.com"))

    user = asyncio.run(stored_user())
    assert user is not None
    assert user.password_hash != "correct-horse-battery-staple"
    assert user.password_hash.startswith("$argon2id$")


def test_workspace_conversation_and_message_access_is_isolated(client: TestClient):
    first = register(client, "first@example.com")
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    extra_workspace = client.post(
        "/api/v1/workspaces",
        headers=first_headers,
        json={"name": "Research"},
    )
    assert extra_workspace.status_code == 201
    workspace_list = client.get("/api/v1/workspaces", headers=first_headers).json()
    assert extra_workspace.json()["id"] in {workspace["id"] for workspace in workspace_list}
    first_workspace = workspace_list[0]

    conversation = client.post(
        f"/api/v1/workspaces/{first_workspace['id']}/conversations",
        headers=first_headers,
        json={"title": "Project notes"},
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]

    message = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=first_headers,
        json={"content": "Remember the deployment decision"},
    )
    assert message.status_code == 201
    assert message.json()["role"] == "user"
    stored_messages = client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=first_headers,
    )
    assert [item["content"] for item in stored_messages.json()] == [
        "Remember the deployment decision"
    ]

    second = register(client, "second@example.com")
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=second_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/workspaces/{first_workspace['id']}/conversations",
        headers=second_headers,
    ).status_code == 404


def test_protected_routes_require_authentication(client: TestClient):
    assert client.get("/health").json() == {"status": "ok", "database": "ok"}
    response = client.get("/api/v1/workspaces")
    assert response.status_code == 401


def test_registration_rejects_short_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_demo_session_is_disabled_by_default(client: TestClient):
    response = client.post("/api/v1/auth/demo-session")
    assert response.status_code == 404


def test_demo_session_stays_disabled_in_production(tmp_path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'production.db'}",
        secret_key=SecretStr("test-only-signing-key-that-is-long-enough"),
        app_env="production",
        demo_mode=True,
    )
    app = create_app(settings)

    async def create_tables():
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())
    with TestClient(app) as production_client:
        response = production_client.post("/api/v1/auth/demo-session")
        assert response.status_code == 404


def test_demo_session_is_opt_in_and_keeps_api_authenticated(tmp_path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'demo.db'}",
        secret_key=SecretStr("test-only-signing-key-that-is-long-enough"),
        app_env="development",
        demo_mode=True,
    )
    app = create_app(settings)

    async def create_tables():
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())
    with TestClient(app) as demo_client:
        first_session = demo_client.post("/api/v1/auth/demo-session")
        assert first_session.status_code == 200
        token = first_session.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        workspaces = demo_client.get("/api/v1/workspaces", headers=headers)
        assert workspaces.status_code == 200
        assert len(workspaces.json()) == 1
        assert workspaces.json()[0]["name"] == "Demo"

        second_session = demo_client.post("/api/v1/auth/demo-session")
        assert second_session.status_code == 200
        assert second_session.json()["user"]["id"] == first_session.json()["user"]["id"]

        unauthenticated = demo_client.get("/api/v1/workspaces")
        assert unauthenticated.status_code == 401
