from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.notifications.models import Notification


async def get_notifications(db: AsyncSession, user_id: int) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .options(selectinload(Notification.bag_update))
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    from sqlalchemy import func

    result = await db.execute(
        select(func.count()).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    return result.scalar() or 0


async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )
    await db.commit()


async def mark_all_read(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()


async def create_notification(
    db: AsyncSession,
    user_id: int,
    bag_update_id: int,
    message: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        bag_update_id=bag_update_id,
        message=message,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification
