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
