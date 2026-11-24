from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message, User, WorkspaceMember
from app.db.session import get_db_session
from app.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.security import authenticated_user

router = APIRouter(tags=["conversations"])


async def find_conversation(
    conversation_id: UUID,
    user_id: UUID,
    session: AsyncSession,
) -> Conversation:
    conversation = await session.scalar(
        select(Conversation)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Conversation.workspace_id)
        .where(Conversation.id == conversation_id, WorkspaceMember.user_id == user_id)
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get(
    "/workspaces/{workspace_id}/conversations",
    response_model=list[ConversationResponse],
)
async def list_conversations(
    workspace_id: UUID,
    user: User = Depends(authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[Conversation]:
    is_member = await session.scalar(
        select(WorkspaceMember.workspace_id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if is_member is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    result = await session.scalars(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result)


@router.post(
    "/workspaces/{workspace_id}/conversations",
    response_model=ConversationResponse,
    status_code=201,
)
async def create_conversation(
    workspace_id: UUID,
    payload: ConversationCreate,
    user: User = Depends(authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> Conversation:
    is_member = await session.scalar(
        select(WorkspaceMember.workspace_id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if is_member is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    conversation = Conversation(workspace_id=workspace_id, title=payload.title)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    user: User = Depends(authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[Message]:
    await find_conversation(conversation_id, user.id, session)
    result = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    )
    return list(result)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def create_message(
    conversation_id: UUID,
    payload: MessageCreate,
    user: User = Depends(authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> Message:
    await find_conversation(conversation_id, user.id, session)
    message = Message(conversation_id=conversation_id, role="user", content=payload.content)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message
