import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bags.exceptions import BagNotFound, ImageNotFound, ImageTooLarge, InvalidImageType
from src.bags.models import Bag, BagImage
from src.bags.schemas import BagCreate, BagUpdate
from src.config import settings

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


async def get_bags(db: AsyncSession, user_id: int) -> list[Bag]:
    result = await db.execute(
        select(Bag)
        .where(Bag.user_id == user_id)
        .options(selectinload(Bag.images))
        .order_by(Bag.created_at.desc())
    )
    return list(result.scalars().all())


async def get_bag(db: AsyncSession, bag_id: int, user_id: int) -> Bag:
    result = await db.execute(
        select(Bag)
        .where(Bag.id == bag_id, Bag.user_id == user_id)
        .options(selectinload(Bag.images))
    )
    bag = result.scalar_one_or_none()
    if not bag:
        raise BagNotFound()
    return bag


async def create_bag(db: AsyncSession, user_id: int, data: BagCreate) -> Bag:
    bag = Bag(user_id=user_id, **data.model_dump())
    db.add(bag)
    await db.commit()
    await db.refresh(bag)
    return bag


async def update_bag(db: AsyncSession, bag: Bag, data: BagUpdate) -> Bag:
    for field, value in data.model_dump().items():
        setattr(bag, field, value)
    await db.commit()
    await db.refresh(bag)
    return bag


async def delete_bag(db: AsyncSession, bag: Bag) -> None:
    # Remove image files from disk
    for image in bag.images:
        _delete_image_file(image.filename)
    await db.delete(bag)
    await db.commit()


def _delete_image_file(filename: str) -> None:
    path = settings.UPLOAD_DIR / filename
    if path.exists():
        path.unlink(missing_ok=True)


async def add_image(
    db: AsyncSession,
    bag: Bag,
    file: UploadFile,
    description: str | None,
) -> BagImage:
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in _ALLOWED_EXTENSIONS:
            raise InvalidImageType()

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise ImageTooLarge(settings.MAX_UPLOAD_SIZE_MB)

    # Determine safe extension
    suffix = Path(file.filename or "image.jpg").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        suffix = ".jpg"

    filename = f"{uuid.uuid4().hex}{suffix}"
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = settings.UPLOAD_DIR / filename

    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    existing_count = (
        await db.execute(select(func.count()).where(BagImage.bag_id == bag.id))
    ).scalar()
    is_primary = existing_count == 0
    image = BagImage(
        bag_id=bag.id,
        filename=filename,
        original_filename=file.filename or filename,
        description=description,
        is_primary=is_primary,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def delete_image(db: AsyncSession, bag: Bag, image_id: int) -> None:
    image = next((img for img in bag.images if img.id == image_id), None)
    if not image:
        raise ImageNotFound()
    was_primary = image.is_primary
    _delete_image_file(image.filename)
    await db.delete(image)
    await db.commit()

    if was_primary and bag.images:
        remaining = [img for img in bag.images if img.id != image_id]
        if remaining:
            remaining[0].is_primary = True
            await db.commit()


async def set_primary_image(db: AsyncSession, bag: Bag, image_id: int) -> None:
    image = next((img for img in bag.images if img.id == image_id), None)
    if not image:
        raise ImageNotFound()
    await db.execute(update(BagImage).where(BagImage.bag_id == bag.id).values(is_primary=False))
    image.is_primary = True
    await db.commit()
