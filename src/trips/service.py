from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bags.models import Bag
from src.packing.models import PackingList, PackingListItem
from src.trips.exceptions import BagAlreadyOnTrip, FlightNotFound, TripNotFound
from src.trips.models import Flight, Trip, TripBag
from src.trips.schemas import FlightCreate, TripCreate, TripUpdate


async def get_trips(db: AsyncSession, user_id: int) -> list[Trip]:
    result = await db.execute(
        select(Trip)
        .where(Trip.user_id == user_id)
        .options(selectinload(Trip.flights), selectinload(Trip.trip_bags).selectinload(TripBag.bag))
        .order_by(Trip.departure_date.asc().nullslast(), Trip.created_at.desc())
    )
    return list(result.scalars().all())


async def get_trip(db: AsyncSession, trip_id: int, user_id: int) -> Trip:
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
        .options(
            selectinload(Trip.flights),
            selectinload(Trip.trip_bags).selectinload(TripBag.bag).selectinload(Bag.images),
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


async def delete_flight(db: AsyncSession, trip: Trip, flight_id: int) -> None:
    flight = next((f for f in trip.flights if f.id == flight_id), None)
    if not flight:
        raise FlightNotFound()
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
