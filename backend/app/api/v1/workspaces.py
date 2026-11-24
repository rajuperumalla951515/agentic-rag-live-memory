from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, Workspace, WorkspaceMember
from app.db.session import get_db_session
from app.schemas import WorkspaceCreate, WorkspaceResponse
from app.security import authenticated_user

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user: User = Depends(authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[Workspace]:
    result = await session.scalars(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at)
    )
    return list(result)


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    user: User = Depends(authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> Workspace:
    workspace = Workspace(name=payload.name)
    session.add(workspace)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await session.commit()
    await session.refresh(workspace)
    return workspace
