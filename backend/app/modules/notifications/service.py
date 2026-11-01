import json
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.notifications import ws_manager
from app.models import Notification
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
)


async def create_and_send_notification(
    db: AsyncSession,
    user_id: UUID,
    type: str,
    title: str,
    message: str,
    data: dict | None = None
) -> Notification:
    data_json = json.dumps(data) if data else None

    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data_json,
        is_read=False
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # Broadcast event in real-time over Redis and WebSockets
    payload = {
        "event": "notification",
        "notification": {
            "id": str(notification.id),
            "user_id": str(notification.user_id),
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "data": data,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat()
        }
    }
    await ws_manager.publish(str(user_id), payload)

    return notification


async def get_user_notifications(
    db: AsyncSession,
    user_id: UUID,
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0
) -> NotificationListResponse:
    # Count unread
    unread_count_stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    unread_count = (await db.execute(unread_count_stmt)).scalar() or 0

    # Total count
    total_stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id)
    )
    if unread_only:
        total_stmt = total_stmt.where(Notification.is_read.is_(False))
    total = (await db.execute(total_stmt)).scalar() or 0

    # Query items
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    items = list((await db.execute(stmt)).scalars().all())

    return NotificationListResponse(
        items=[
            NotificationResponse(
                id=n.id,
                user_id=n.user_id,
                type=n.type,
                title=n.title,
                message=n.message,
                data=n.data,
                is_read=n.is_read,
                created_at=n.created_at
            ) for n in items
        ],
        total=total,
        unread_count=unread_count
    )


async def mark_notification_as_read(
    db: AsyncSession,
    notification_id: UUID,
    user_id: UUID
) -> NotificationResponse:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id
    )
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)

    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        data=notification.data,
        is_read=notification.is_read,
        created_at=notification.created_at
    )


async def mark_all_notifications_as_read(
    db: AsyncSession,
    user_id: UUID
) -> dict:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}

