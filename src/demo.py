"""Populate a fresh database with demo data. Run via: just demo-data"""

import asyncio
import secrets
from datetime import date, datetime, timedelta

from sqlalchemy import select

import src.auth.models  # noqa: F401
import src.bags.models  # noqa: F401
import src.notifications.models  # noqa: F401
import src.packing.models  # noqa: F401
import src.trips.models  # noqa: F401
from src.auth.models import User
from src.auth.service import _hash_password
from src.bags.models import Bag
from src.database import Base, SessionFactory, engine
from src.packing.models import PackingList
from src.packing.seed import seed_default_templates
from src.trips.models import Flight, Trip, TripBag, TripCheckin, TripCheckinBag, trip_checkin_flight

_DEMO_USERNAME = "demo"
_DEMO_EMAIL = "demo@bagtag.aero"
_DEMO_PASSWORD = "demo"  # nosec B105 — intentional demo credential


def _dt(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute)


async def _seed(db) -> None:
    today = date.today()

    existing = (
        await db.execute(select(User).where(User.username == _DEMO_USERNAME))
    ).scalar_one_or_none()
    if existing:
        print("Demo user already exists — skipping.")
        return

    user = User(
        username=_DEMO_USERNAME,
        email=_DEMO_EMAIL,
        hashed_password=_hash_password(_DEMO_PASSWORD),
    )
    db.add(user)
    await db.flush()

    # Bags
    suitcase = Bag(
        user_id=user.id,
        name="Large Suitcase",
        brand="Samsonite",
        model="Omni PC",
        color="BK",
        bag_type="02",
        material="R",
        has_wheels=True,
        has_retractable_handle=True,
        has_combination_lock=True,
        volume_liters=75.0,
        tare_weight_kg=4.2,
        public_token=secrets.token_hex(6),
    )
    cabin = Bag(
        user_id=user.id,
        name="Cabin Bag",
        brand="Travelpro",
        model="Maxlite 5",
        color="BK",
        bag_type="22",
        is_cabin_size=True,
        has_wheels=True,
        has_retractable_handle=True,
        volume_liters=38.0,
        tare_weight_kg=2.8,
        public_token=secrets.token_hex(6),
    )
    backpack = Bag(
        user_id=user.id,
        name="Hiking Backpack",
        brand="Osprey",
        model="Farpoint 40",
        color="BU",
        bag_type="29",
        volume_liters=40.0,
        tare_weight_kg=1.6,
        public_token=secrets.token_hex(6),
    )
    db.add_all([suitcase, cabin, backpack])
    await db.flush()

    # ── Past trip (7–6 weeks ago, fully completed) ─────────────────────────────
    p_dep = today - timedelta(weeks=7)
    p_ret = today - timedelta(weeks=6)

    past = Trip(
        user_id=user.id,
        name="Amsterdam City Break",
        trip_type="city_break",
        departure_date=p_dep,
        return_date=p_ret,
    )
    db.add(past)
    await db.flush()
    db.add(PackingList(trip_id=past.id))

    db.add_all(
        [
            TripBag(trip_id=past.id, bag_id=cabin.id),
            TripBag(trip_id=past.id, bag_id=backpack.id),
        ]
    )

    pf_out = Flight(
        trip_id=past.id,
        flight_number="EZY345",
        airline="easyJet",
        departure_airport="EDI",
        arrival_airport="AMS",
        departure_at=_dt(p_dep, 8, 30),
        arrival_at=_dt(p_dep, 11, 15),
    )
    pf_ret = Flight(
        trip_id=past.id,
        flight_number="EZY346",
        airline="easyJet",
        departure_airport="AMS",
        arrival_airport="EDI",
        departure_at=_dt(p_ret, 17, 0),
        arrival_at=_dt(p_ret, 18, 45),
        is_return=True,
    )
    db.add_all([pf_out, pf_ret])
    await db.flush()

    pc_out = TripCheckin(trip_id=past.id, created_at=_dt(p_dep, 7, 0))
    db.add(pc_out)
    await db.flush()
    await db.execute(trip_checkin_flight.insert().values(checkin_id=pc_out.id, flight_id=pf_out.id))
    db.add(
        TripCheckinBag(
            checkin_id=pc_out.id,
            bag_id=cabin.id,
            status="carry_on",
            checked_in_at=_dt(p_dep, 7, 5),
            collected_at=_dt(p_dep, 11, 20),
            collection_outcome="collected",
        )
    )

    pc_ret = TripCheckin(trip_id=past.id, created_at=_dt(p_ret, 16, 0))
    db.add(pc_ret)
    await db.flush()
    await db.execute(trip_checkin_flight.insert().values(checkin_id=pc_ret.id, flight_id=pf_ret.id))
    db.add(
        TripCheckinBag(
            checkin_id=pc_ret.id,
            bag_id=cabin.id,
            status="carry_on",
            checked_in_at=_dt(p_ret, 16, 10),
            collected_at=_dt(p_ret, 18, 50),
            collection_outcome="collected",
        )
    )

    # ── Current trip (started 3 days ago, returns in 3 days) ──────────────────
    c_dep = today - timedelta(days=3)
    c_ret = today + timedelta(days=3)

    curr = Trip(
        user_id=user.id,
        name="New York Business",
        trip_type="business",
        departure_date=c_dep,
        return_date=c_ret,
    )
    db.add(curr)
    await db.flush()
    db.add(PackingList(trip_id=curr.id))

    db.add_all(
        [
            TripBag(trip_id=curr.id, bag_id=suitcase.id),
            TripBag(trip_id=curr.id, bag_id=cabin.id),
        ]
    )

    cf_out = Flight(
        trip_id=curr.id,
        flight_number="BA117",
        airline="British Airways",
        departure_airport="LHR",
        arrival_airport="JFK",
        departure_at=_dt(c_dep, 10, 0),
        arrival_at=_dt(c_dep, 13, 0),
    )
    cf_ret = Flight(
        trip_id=curr.id,
        flight_number="BA178",
        airline="British Airways",
        departure_airport="JFK",
        arrival_airport="LHR",
        departure_at=_dt(c_ret, 19, 0),
        arrival_at=_dt(c_ret + timedelta(days=1), 7, 30),
        is_return=True,
    )
    db.add_all([cf_out, cf_ret])
    await db.flush()

    # Suitcase checked in but not yet collected → shows as active check-in on dashboard
    cc_out = TripCheckin(trip_id=curr.id, created_at=_dt(c_dep, 8, 0))
    db.add(cc_out)
    await db.flush()
    await db.execute(trip_checkin_flight.insert().values(checkin_id=cc_out.id, flight_id=cf_out.id))
    db.add_all(
        [
            TripCheckinBag(
                checkin_id=cc_out.id,
                bag_id=suitcase.id,
                status="checked_in",
                licence_plate_number="AB123456",
                weight_kg=18.5,
                checked_in_at=_dt(c_dep, 8, 15),
            ),
            TripCheckinBag(
                checkin_id=cc_out.id,
                bag_id=cabin.id,
                status="carry_on",
                checked_in_at=_dt(c_dep, 8, 15),
                collected_at=_dt(c_dep, 13, 10),
                collection_outcome="collected",
            ),
        ]
    )

    # ── Future trip (departs in ~2.5 weeks) ───────────────────────────────────
    f_dep = today + timedelta(weeks=2, days=3)
    f_ret = today + timedelta(weeks=3)

    future = Trip(
        user_id=user.id,
        name="Rome Weekend",
        trip_type="city_break",
        departure_date=f_dep,
        return_date=f_ret,
    )
    db.add(future)
    await db.flush()
    db.add(PackingList(trip_id=future.id))

    db.add_all(
        [
            TripBag(trip_id=future.id, bag_id=cabin.id),
            TripBag(trip_id=future.id, bag_id=backpack.id),
        ]
    )
    db.add_all(
        [
            Flight(
                trip_id=future.id,
                flight_number="FR2345",
                airline="Ryanair",
                departure_airport="EDI",
                arrival_airport="FCO",
                departure_at=_dt(f_dep, 6, 30),
                arrival_at=_dt(f_dep, 10, 0),
            ),
            Flight(
                trip_id=future.id,
                flight_number="FR2346",
                airline="Ryanair",
                departure_airport="FCO",
                arrival_airport="EDI",
                departure_at=_dt(f_ret, 18, 0),
                arrival_at=_dt(f_ret, 21, 30),
                is_return=True,
            ),
        ]
    )

    await db.commit()
    print(f"Demo data created. Login: username='{_DEMO_USERNAME}' password='{_DEMO_PASSWORD}'")


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionFactory() as db:
        await seed_default_templates(db)
        await _seed(db)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
