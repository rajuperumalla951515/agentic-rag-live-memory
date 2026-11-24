import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import User, Workspace, WorkspaceMember
from app.db.session import get_db_session
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])
DEMO_EMAIL = "demo@agentic-rag-live-memory.example"


def token_response(user: User, settings: Settings) -> TokenResponse:
    access_token, expires_in = create_access_token(user.id, settings)
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    settings: Settings = request.app.state.settings
    if payload.email == DEMO_EMAIL:
        raise HTTPException(status_code=409, detail="This email address is reserved")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    try:
        async with session.begin():
            session.add(user)
            await session.flush()
            workspace = Workspace(name="Personal")
            session.add(workspace)
            await session.flush()
            session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    except IntegrityError as error:
        if "users.email" not in str(error.orig).lower() and "ix_users_email" not in str(error.orig).lower():
            raise
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    return token_response(user, settings)


@router.post("/demo-session", response_model=TokenResponse)
async def create_demo_session(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    settings: Settings = request.app.state.settings
    if settings.app_env != "development" or not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Not found")

    user = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(32)),
        )
        session.add(user)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            user = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
            if user is None:
                raise

    if not user.is_active:
        raise HTTPException(status_code=404, detail="Not found")

    workspace = await session.scalar(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at)
        .limit(1)
    )
    if workspace is None:
        workspace = Workspace(name="Demo")
        session.add(workspace)
        await session.flush()
        session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await session.commit()
    return token_response(user, settings)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    settings: Settings = request.app.state.settings
    user = await session.scalar(
        select(User).where(User.email == payload.email, User.is_active.is_(True))
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return token_response(user, settings)
