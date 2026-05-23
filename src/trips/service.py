import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bags.models import Bag
from src.config import settings
from src.packing.models import PackingList, PackingListItem
from src.trips.exceptions import BagAlreadyOnTrip, FlightNotFound, TripNotFound
from src.trips.models import (
    Flight,
    Trip,
    TripBag,
    TripCheckin,
    TripCheckinBag,
    TripCheckinBagDamagePhoto,
)
from src.trips.schemas import FlightCreate, TripCreate, TripUpdate

_ALLOWED_RECEIPT_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
}
_ALLOWED_RECEIPT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}
_ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def compute_active_checkin(trip: Trip) -> TripCheckin | None:
    """Return the most recent check-in with at least one uncollected checked-in bag."""
    for checkin in trip.checkins:  # already ordered newest-first
        if any(b.status == "checked_in" and not b.collected_at for b in checkin.bag_checkins):
            return checkin
    return None


async def get_trips(db: AsyncSession, user_id: int) -> list[Trip]:
    result = await db.execute(
        select(Trip)
        .where(Trip.user_id == user_id)
        .options(
            selectinload(Trip.flights).selectinload(Flight.reroutings),
            selectinload(Trip.trip_bags).selectinload(TripBag.bag),
        )
        .order_by(Trip.departure_date.asc().nullslast(), Trip.created_at.desc())
    )
    return list(result.scalars().all())


async def get_trip(db: AsyncSession, trip_id: int, user_id: int) -> Trip:
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
        .options(
            selectinload(Trip.flights).selectinload(Flight.reroutings),
            selectinload(Trip.trip_bags).selectinload(TripBag.bag).selectinload(Bag.images),
            selectinload(Trip.checkins)
            .selectinload(TripCheckin.bag_checkins)
            .selectinload(TripCheckinBag.bag)
            .selectinload(Bag.images),
            selectinload(Trip.checkins)
            .selectinload(TripCheckin.bag_checkins)
            .selectinload(TripCheckinBag.damage_photos),
            selectinload(Trip.packing_list)
            .selectinload(PackingList.items)
            .selectinload(PackingListItem.bag),
        )
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise TripNotFound()
    return trip


async def create_trip(db: AsyncSession, user_id: int, data: TripCreate) -> Trip:
    from src.packing.models import PackingList

    trip = Trip(user_id=user_id, **data.model_dump())
    db.add(trip)
    await db.flush()
    packing_list = PackingList(trip_id=trip.id, name="Packing List")
    db.add(packing_list)
    await db.commit()
    await db.refresh(trip)
    return trip


async def update_trip(db: AsyncSession, trip: Trip, data: TripUpdate) -> Trip:
    for field, value in data.model_dump().items():
        setattr(trip, field, value)
    await db.commit()
    await db.refresh(trip)
    return trip


async def delete_trip(db: AsyncSession, trip: Trip) -> None:
    await db.delete(trip)
    await db.commit()


async def add_flight(db: AsyncSession, trip: Trip, data: FlightCreate) -> Flight:
    flight = Flight(trip_id=trip.id, **data.model_dump())
    db.add(flight)
    await db.commit()
    await db.refresh(flight)
    return flight


async def cancel_flight(db: AsyncSession, trip: Trip, flight_id: int) -> None:
    flight = next((f for f in trip.flights if f.id == flight_id), None)
    if not flight:
        raise FlightNotFound()
    flight.is_cancelled = True
    await db.commit()


async def uncancel_flight(db: AsyncSession, trip: Trip, flight_id: int) -> None:
    flight = next((f for f in trip.flights if f.id == flight_id), None)
    if not flight:
        raise FlightNotFound()
    flight.is_cancelled = False
    await db.commit()


async def delete_flight(db: AsyncSession, trip: Trip, flight_id: int) -> None:
    flight = next((f for f in trip.flights if f.id == flight_id), None)
    if not flight:
        raise FlightNotFound()
    # Null out rerouted_from_id on any reroutings before deleting the parent
    # (SQLite does not enforce FK ON DELETE SET NULL without PRAGMA foreign_keys)
    for child in list(flight.reroutings):
        child.rerouted_from_id = None
    await db.flush()
    await db.delete(flight)
    await db.commit()


async def get_available_bags(db: AsyncSession, trip: Trip, user_id: int) -> list[Bag]:
    """Return user's bags not yet assigned to this trip."""
    assigned_ids_result = await db.execute(select(TripBag.bag_id).where(TripBag.trip_id == trip.id))
    assigned_ids = set(assigned_ids_result.scalars().all())
    result = await db.execute(
        select(Bag)
        .where(Bag.user_id == user_id)
        .options(selectinload(Bag.images))
        .order_by(Bag.name)
    )
    return [b for b in result.scalars().all() if b.id not in assigned_ids]


async def assign_bag(db: AsyncSession, trip: Trip, bag_id: int, user_id: int) -> None:
    existing = (
        await db.execute(
            select(TripBag).where(TripBag.trip_id == trip.id, TripBag.bag_id == bag_id)
        )
    ).scalar_one_or_none()
    if existing:
        raise BagAlreadyOnTrip()
    if not (
        await db.execute(select(Bag).where(Bag.id == bag_id, Bag.user_id == user_id))
    ).scalar_one_or_none():
        raise TripNotFound()
    trip_bag = TripBag(trip_id=trip.id, bag_id=bag_id)
    db.add(trip_bag)
    await db.commit()


async def remove_bag(db: AsyncSession, trip: Trip, bag_id: int) -> None:
    trip_bag = (
        await db.execute(
            select(TripBag).where(TripBag.trip_id == trip.id, TripBag.bag_id == bag_id)
        )
    ).scalar_one_or_none()
    if trip_bag:
        await db.delete(trip_bag)
        await db.commit()


async def save_checkin(
    db: AsyncSession,
    trip: Trip,
    active_checkin: TripCheckin | None,
    checkin_data: dict[int, dict],
) -> TripCheckin:
    """Create a new check-in or update the active one."""
    now = datetime.utcnow()

    if active_checkin is None:
        checkin = TripCheckin(trip_id=trip.id)
        db.add(checkin)
        await db.flush()
        bag_checkins_by_bag: dict[int, TripCheckinBag] = {}
    else:
        checkin = active_checkin
        bag_checkins_by_bag = {b.bag_id: b for b in checkin.bag_checkins}

    for bag_id, data in checkin_data.items():
        existing = bag_checkins_by_bag.get(bag_id)
        if existing:
            existing.status = data["status"]
            existing.licence_plate_number = data.get("licence_plate_number")
            existing.weight_kg = data.get("weight_kg")
            if data["status"] == "checked_in" and not existing.checked_in_at:
                existing.checked_in_at = now
            elif data["status"] == "carry_on":
                existing.checked_in_at = None
        else:
            bag_checkin = TripCheckinBag(
                checkin_id=checkin.id,
                bag_id=bag_id,
                status=data["status"],
                licence_plate_number=data.get("licence_plate_number"),
                weight_kg=data.get("weight_kg"),
                checked_in_at=now if data["status"] == "checked_in" else None,
            )
            db.add(bag_checkin)

    await db.commit()
    return checkin


async def save_checkin_bag_receipt(
    db: AsyncSession, checkin_id: int, bag_id: int, file: UploadFile
) -> None:
    bag_checkin = (
        await db.execute(
            select(TripCheckinBag).where(
                TripCheckinBag.checkin_id == checkin_id,
                TripCheckinBag.bag_id == bag_id,
            )
        )
    ).scalar_one_or_none()
    if not bag_checkin:
        return

    content_type = file.content_type or ""
    suffix = Path(file.filename or "").suffix.lower()
    if (
        content_type not in _ALLOWED_RECEIPT_CONTENT_TYPES
        and suffix not in _ALLOWED_RECEIPT_EXTENSIONS
    ):
        return

    content = await file.read()
    if not content:
        return

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        return

    if suffix not in _ALLOWED_RECEIPT_EXTENSIONS:
        suffix = ".jpg"

    if bag_checkin.receipt_filename:
        (settings.UPLOAD_DIR / bag_checkin.receipt_filename).unlink(missing_ok=True)

    filename = f"checkin_{uuid.uuid4().hex}{suffix}"
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(settings.UPLOAD_DIR / filename, "wb") as f:
        await f.write(content)

    bag_checkin.receipt_filename = filename
    await db.commit()


async def save_collection_outcomes(
    db: AsyncSession,
    checkin: TripCheckin,
    outcome_data: dict[int, dict],
) -> None:
    now = datetime.utcnow()
    for bc in checkin.bag_checkins:
        if bc.bag_id in outcome_data and bc.status == "checked_in" and not bc.collected_at:
            data = outcome_data[bc.bag_id]
            bc.collected_at = now
            bc.collection_outcome = data["outcome"]
            bc.pir_reference = data.get("pir_reference")
    await db.commit()


async def _write_upload(content: bytes, prefix: str, suffix: str) -> str:
    filename = f"{prefix}_{uuid.uuid4().hex}{suffix}"
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(settings.UPLOAD_DIR / filename, "wb") as f:
        await f.write(content)
    return filename


async def save_damage_photos(
    db: AsyncSession, checkin_id: int, bag_id: int, files: list[UploadFile]
) -> None:
    bag_checkin = (
        await db.execute(
            select(TripCheckinBag).where(
                TripCheckinBag.checkin_id == checkin_id,
                TripCheckinBag.bag_id == bag_id,
            )
        )
    ).scalar_one_or_none()
    if not bag_checkin:
        return

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    saved = 0
    for file in files:
        if saved >= 6:
            break
        content_type = file.content_type or ""
        suffix = Path(file.filename or "").suffix.lower()
        if (
            content_type not in _ALLOWED_IMAGE_CONTENT_TYPES
            and suffix not in _ALLOWED_IMAGE_EXTENSIONS
        ):
            continue
        content = await file.read()
        if not content or len(content) > max_bytes:
            continue
        if suffix not in _ALLOWED_IMAGE_EXTENSIONS:
            suffix = ".jpg"
        filename = await _write_upload(content, "damage", suffix)
        db.add(TripCheckinBagDamagePhoto(bag_checkin_id=bag_checkin.id, filename=filename))
        saved += 1
    if saved:
        await db.commit()


async def save_pir_receipt(
    db: AsyncSession, checkin_id: int, bag_id: int, file: UploadFile
) -> None:
    bag_checkin = (
        await db.execute(
            select(TripCheckinBag).where(
                TripCheckinBag.checkin_id == checkin_id,
                TripCheckinBag.bag_id == bag_id,
            )
        )
    ).scalar_one_or_none()
    if not bag_checkin:
        return

    content_type = file.content_type or ""
    suffix = Path(file.filename or "").suffix.lower()
    if (
        content_type not in _ALLOWED_RECEIPT_CONTENT_TYPES
        and suffix not in _ALLOWED_RECEIPT_EXTENSIONS
    ):
        return

    content = await file.read()
    if not content:
        return
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        return
    if suffix not in _ALLOWED_RECEIPT_EXTENSIONS:
        suffix = ".jpg"

    if bag_checkin.pir_receipt_filename:
        (settings.UPLOAD_DIR / bag_checkin.pir_receipt_filename).unlink(missing_ok=True)

    bag_checkin.pir_receipt_filename = await _write_upload(content, "pir", suffix)
    await db.commit()


async def get_bag_incidents(db: AsyncSession, bag_id: int) -> list[TripCheckinBag]:
    result = await db.execute(
        select(TripCheckinBag)
        .where(
            TripCheckinBag.bag_id == bag_id,
            TripCheckinBag.collection_outcome.in_(["damaged", "missing"]),
        )
        .options(
            selectinload(TripCheckinBag.checkin).selectinload(TripCheckin.trip),
            selectinload(TripCheckinBag.damage_photos),
        )
        .order_by(TripCheckinBag.collected_at.desc())
    )
    return list(result.scalars().all())


async def resolve_incident(
    db: AsyncSession, bag_checkin_id: int, bag_id: int, resolution: str
) -> None:
    bc = (
        await db.execute(
            select(TripCheckinBag).where(
                TripCheckinBag.id == bag_checkin_id,
                TripCheckinBag.bag_id == bag_id,
            )
        )
    ).scalar_one_or_none()
    if not bc:
        return
    bc.resolution = resolution
    bc.resolved_at = datetime.utcnow()
    await db.commit()
