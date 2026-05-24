"""Trip, flight, and bag-assignment endpoint tests."""

import itertools
from datetime import date

from src.bags import service as bag_service
from src.bags.schemas import BagCreate
from src.trips import service as trip_service
from src.trips.schemas import FlightCreate, TripCreate

_trip_uid = itertools.count(300)

_DEP = date(2026, 8, 1)
_RET = date(2026, 8, 14)


def _trip_name():
    return f"Trip {next(_trip_uid)}"


def _new_trip(name: str | None = None) -> TripCreate:
    return TripCreate(
        name=name or _trip_name(),
        departure_date=_DEP,
        return_date=_RET,
    )


# ── List / forms ─────────────────────────────────────────────────────────────


async def test_list_trips_page_renders(auth_client):
    resp = await auth_client.get("/trips/")
    assert resp.status_code == 200
    assert "My Trips" in resp.text


async def test_new_trip_form_renders(auth_client):
    resp = await auth_client.get("/trips/new")
    assert resp.status_code == 200
    assert "Plan a New Trip" in resp.text


# ── Create ───────────────────────────────────────────────────────────────────


async def test_create_trip_minimal(auth_client):
    name = _trip_name()
    resp = await auth_client.post(
        "/trips/new",
        data={"name": name, "departure_date": "2026-08-01", "return_date": "2026-08-14"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/trips/" in resp.headers["location"]


async def test_create_trip_full(auth_client):
    name = _trip_name()
    resp = await auth_client.post(
        "/trips/new",
        data={
            "name": name,
            "trip_type": "beach",
            "departure_date": "2026-08-01",
            "return_date": "2026-08-14",
            "description": "Summer holiday",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302


async def test_create_trip_appears_in_list(auth_client):
    name = _trip_name()
    await auth_client.post(
        "/trips/new",
        data={"name": name, "departure_date": "2026-08-01", "return_date": "2026-08-14"},
    )
    resp = await auth_client.get("/trips/")
    assert name in resp.text


async def test_create_trip_auto_creates_packing_list(auth_client, user, db):
    """Creating a trip must automatically create its packing list."""
    from src.packing import service as packing_service

    trip = await trip_service.create_trip(db, user.id, _new_trip())
    pl = await packing_service.get_packing_list(db, trip.id)
    assert pl is not None
    assert pl.trip_id == trip.id


# ── Detail ───────────────────────────────────────────────────────────────────


async def test_trip_detail_renders(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    resp = await auth_client.get(f"/trips/{trip.id}")
    assert resp.status_code == 200
    assert trip.name in resp.text
    assert "Flights" in resp.text
    assert "Bags" in resp.text
    assert "Packing" in resp.text


async def test_trip_detail_shows_packing_list(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    resp = await auth_client.get(f"/trips/{trip.id}")
    assert resp.status_code == 200
    assert "tab-packing" in resp.text


async def test_trip_not_found(auth_client):
    resp = await auth_client.get("/trips/999999")
    assert resp.status_code == 404


# ── Edit ─────────────────────────────────────────────────────────────────────


async def test_edit_trip_form_renders(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    resp = await auth_client.get(f"/trips/{trip.id}/edit")
    assert resp.status_code == 200
    assert trip.name in resp.text


async def test_edit_trip(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    new_name = _trip_name()
    resp = await auth_client.post(
        f"/trips/{trip.id}/edit",
        data={
            "name": new_name,
            "description": "Updated desc",
            "departure_date": "2026-08-01",
            "return_date": "2026-08-14",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/trips/{trip.id}")
    assert new_name in detail.text


# ── Delete ───────────────────────────────────────────────────────────────────


async def test_delete_trip(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    resp = await auth_client.post(f"/trips/{trip.id}/delete", follow_redirects=False)
    assert resp.status_code == 302
    assert "/trips" in resp.headers["location"]

    gone = await auth_client.get(f"/trips/{trip.id}")
    assert gone.status_code == 404


# ── Flights ──────────────────────────────────────────────────────────────────


async def test_add_flight_via_service(auth_client, user, db):
    """Flights added via service appear on the trip detail page."""
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    await trip_service.add_flight(
        db,
        trip,
        FlightCreate(departure_airport="LHR", arrival_airport="CDG", flight_number="BA303"),
    )
    detail = await auth_client.get(f"/trips/{trip.id}")
    assert "LHR" in detail.text
    assert "CDG" in detail.text
    assert "BA303" in detail.text


async def test_add_flight_endpoint_redirects(auth_client, user, db):
    """POST /flights always redirects (success or FR24 error)."""
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    resp = await auth_client.post(
        f"/trips/{trip.id}/flights",
        data={"flight_number": "BA303", "departure_date": "2026-08-01"},
        follow_redirects=False,
    )
    assert resp.status_code == 302


async def test_delete_flight(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    flight = await trip_service.add_flight(
        db,
        trip,
        FlightCreate(departure_airport="MAN", arrival_airport="AMS"),
    )
    resp = await auth_client.post(
        f"/trips/{trip.id}/flights/{flight.id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/trips/{trip.id}")
    assert "MAN" not in detail.text


# ── Bag assignment ────────────────────────────────────────────────────────────


async def test_assign_bag_to_trip(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=f"Bag {next(_trip_uid)}"))
    trip = await trip_service.create_trip(db, user.id, _new_trip())

    resp = await auth_client.post(
        f"/trips/{trip.id}/bags",
        data={"bag_id": bag.id},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/trips/{trip.id}")
    assert bag.name in detail.text


async def test_remove_bag_from_trip(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=f"Bag {next(_trip_uid)}"))
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    await trip_service.assign_bag(db, trip, bag.id, user.id)

    # Reload trip to pick up new trip_bags
    trip = await trip_service.get_trip(db, trip.id, user.id)
    resp = await auth_client.post(
        f"/trips/{trip.id}/bags/{bag.id}/remove",
        follow_redirects=False,
    )
    assert resp.status_code == 302


async def test_assign_bag_twice_is_conflict(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=f"Bag {next(_trip_uid)}"))
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    await trip_service.assign_bag(db, trip, bag.id, user.id)

    trip = await trip_service.get_trip(db, trip.id, user.id)
    resp = await auth_client.post(
        f"/trips/{trip.id}/bags",
        data={"bag_id": bag.id},
        follow_redirects=False,
    )
    # Returns 409 (handled as HTTPException, not redirect)
    assert resp.status_code == 409
