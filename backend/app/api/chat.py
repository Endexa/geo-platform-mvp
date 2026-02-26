"""Chat assistant API endpoints with SSE streaming.

Provides POST /{audit_id}/chat for streaming LLM responses grounded in
audit data and GET /{audit_id}/history for conversation history retrieval.
Both endpoints are gated to PRO tier subscribers.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import SubscriptionTier, require_tier
from app.core.security import get_current_active_user
from app.models.audit import Audit
from app.models.profile import Profile
from app.schemas.chat import ChatHistoryResponse, ChatMessageRequest, ChatMessageSchema
from app.services.chat_service import ChatService

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/chat",
    tags=["chat"],
)


def _verify_audit_ownership(
    audit_id: str, db: Session, current_user: Profile
) -> Audit:
    """Verify audit exists, belongs to current user, and is completed."""
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit or audit.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit not found",
        )
    if audit.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat is only available for completed audits",
        )
    return audit


@router.post(
    "/{audit_id}/chat",
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
)
async def chat_message(
    audit_id: str,
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Send a chat message and receive a streamed LLM response.

    Streams tokens as Server-Sent Events (SSE). Each event contains a JSON
    object with either {"token": "..."} for content tokens, {"done": true,
    "full_response": "..."} on completion, or {"error": "..."} on failure.

    The LLM response is grounded in the user's actual audit data: scores,
    failing criteria, recommendations, and visibility breakdown.

    Requires PRO subscription tier.
    """
    audit = _verify_audit_ownership(audit_id, db, current_user)

    chat_service = ChatService(db)
    session = chat_service.get_or_create_session(audit.id, current_user.id)

    # Add user message to session BEFORE starting LLM call
    # (persists even if streaming fails)
    user_msg = {
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    current_messages = list(session.messages or [])
    current_messages.append(user_msg)
    session.messages = current_messages
    db.commit()

    # Build the full messages array for LLM
    llm_messages = chat_service.build_messages(audit, session)

    async def event_generator():
        """Async generator that yields SSE events from the LLM stream."""
        full_response = ""
        try:
            async for chunk_json in chat_service.stream_response(llm_messages):
                data = json.loads(chunk_json)
                if "token" in data:
                    full_response += data["token"]
                yield {"data": chunk_json}

                # On completion, save assistant message to session
                if data.get("done"):
                    assistant_msg = {
                        "role": "assistant",
                        "content": full_response,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    msgs = list(session.messages or [])
                    msgs.append(assistant_msg)
                    session.messages = msgs
                    session.model_used = settings.CHAT_MODEL
                    db.commit()

        except Exception as e:
            logger.error(f"SSE event generator error: {e}")
            yield {"data": json.dumps({"error": str(e)})}

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get(
    "/{audit_id}/history",
    response_model=ChatHistoryResponse,
    dependencies=[Depends(require_tier(SubscriptionTier.PRO))],
)
async def chat_history(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    """Get conversation history for an audit.

    Returns all messages in the chat session for the given audit.
    Returns an empty message list if no session exists yet.

    Requires PRO subscription tier.
    """
    audit = _verify_audit_ownership(audit_id, db, current_user)

    from app.models.chat_session import ChatSession

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.audit_id == audit.id,
            ChatSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        return ChatHistoryResponse(
            audit_id=str(audit.id),
            messages=[],
            model_used=None,
        )

    return ChatHistoryResponse(
        audit_id=str(audit.id),
        messages=[
            ChatMessageSchema(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp", ""),
            )
            for msg in (session.messages or [])
        ],
        model_used=session.model_used,
    )
