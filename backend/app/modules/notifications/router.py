import uuid
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notifications import ws_manager
from app.core.security import decode_token
from app.database.session import AsyncSessionLocal, get_db
from app.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
)
from app.modules.notifications.service import (
    get_user_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Authenticated User's Notifications"
)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Notification as Read"
)
async def read_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await mark_notification_as_read(db, notification_id, current_user.id)


@router.patch(
    "/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark All Notifications as Read"
)
async def read_all_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await mark_all_notifications_as_read(db, current_user.id)


@router.websocket("/ws")
async def websocket_notifications_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Bearer access token")
):
    """Real-time bi-directional WebSocket connection for live notification streaming."""
    # Authenticate token
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_id = uuid.UUID(user_id_str)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify user exists and is active
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
        user = res.scalar_one_or_none()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    user_key = str(user.id)
    await ws_manager.connect(user_key, websocket)
    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "event": "connected",
            "message": "Connected to DevHire real-time notification stream",
            "user_id": user_key
        })

        # Keep connection alive & handle incoming pings
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_key, websocket)
    except Exception:
        await ws_manager.disconnect(user_key, websocket)

