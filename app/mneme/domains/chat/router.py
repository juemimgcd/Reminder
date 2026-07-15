import asyncio
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database, get_write_database
from app.mneme.domains.chat.service import (
    ask_in_chat_session,
    create_chat_session,
    delete_chat_session,
    get_chat_session_detail,
    list_chat_sessions,
    message_to_data,
    require_owned_chat_session,
    stream_in_chat_session,
    update_chat_session,
)
from app.mneme.models.user import User
from app.mneme.schemas.chat_session import (
    ChatSessionCreateRequest,
    ChatSessionData,
    ChatSessionDetailData,
    ChatSessionListData,
    ChatSessionMessageRequest,
    ChatSessionUpdateRequest,
)
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/kb/chat/sessions", tags=["chat"])


@router.get("")
async def list_chat_sessions_api(
    knowledge_base_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    sessions = await list_chat_sessions(db, current_user=current_user, knowledge_base_id=knowledge_base_id)
    items = [ChatSessionData.model_validate(session) for session in sessions]
    return success_response(data=ChatSessionListData(items=items, total=len(items)))


@router.post("")
async def create_chat_session_api(
    payload: ChatSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    session = await create_chat_session(
        db,
        current_user=current_user,
        knowledge_base_id=payload.knowledge_base_id,
        title=payload.title,
    )
    return success_response(data=ChatSessionData.model_validate(session), message="chat session created")


@router.get("/{session_id}")
async def get_chat_session_api(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    session, messages = await get_chat_session_detail(db, current_user=current_user, session_id=session_id)
    return success_response(
        data=ChatSessionDetailData(
            session=ChatSessionData.model_validate(session),
            messages=[message_to_data(message) for message in messages],
        )
    )


@router.patch("/{session_id}")
async def update_chat_session_api(
    session_id: str,
    payload: ChatSessionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    session = await update_chat_session(
        db,
        current_user=current_user,
        session_id=session_id,
        title=payload.title,
        archived=payload.archived,
    )
    return success_response(data=ChatSessionData.model_validate(session), message="chat session updated")


@router.delete("/{session_id}")
async def delete_chat_session_api(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    deleted_count = await delete_chat_session(db, current_user=current_user, session_id=session_id)
    return success_response(
        data={"session_id": session_id, "deleted_count": deleted_count},
        message="chat session deleted",
    )


@router.post("/{session_id}/messages")
async def create_chat_message_api(
    session_id: str,
    payload: ChatSessionMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    session, messages = await ask_in_chat_session(
        db,
        current_user=current_user,
        session_id=session_id,
        question=payload.question,
        top_k=payload.top_k,
        answer_mode=payload.answer_mode,
        expected_knowledge_base_id=None,
    )
    return success_response(
        data=ChatSessionDetailData(
            session=ChatSessionData.model_validate(session),
            messages=[message_to_data(message) for message in messages],
        ),
        message="chat message created",
    )


@router.post("/{session_id}/messages/stream")
async def stream_chat_message_api(
    session_id: str,
    payload: ChatSessionMessageRequest,
    request_obj: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    if session.archived_at is not None:
        raise BusinessException(message="chat session is archived", code=4049, status_code=400)
    abort_signal = asyncio.Event()

    async def event_stream():
        try:
            async for event in stream_in_chat_session(
                db,
                current_user=current_user,
                session_id=session_id,
                question=payload.question,
                top_k=payload.top_k,
                answer_mode=payload.answer_mode,
                abort_signal=abort_signal,
            ):
                if await request_obj.is_disconnected():
                    abort_signal.set()
                    break
                data = json.dumps(event.to_stream_dict(), ensure_ascii=False)
                yield f"event: {event.type.value}\ndata: {data}\n\n"
        finally:
            abort_signal.set()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
