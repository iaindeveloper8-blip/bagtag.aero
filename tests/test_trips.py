"""Trip, flight, and bag-assignment endpoint tests."""

import itertools

from src.bags import service as bag_service
from src.bags.schemas import BagCreate
from src.trips import service as trip_service
from src.trips.schemas import TripCreate

_trip_uid = itertools.count(300)


def _trip_name():
    return f"Trip {next(_trip_uid)}"


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
    resp = await auth_client.post("/trips/new", data={"name": name}, follow_redirects=False)
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
    await auth_client.post("/trips/new", data={"name": name})
    resp = await auth_client.get("/trips/")
    assert name in resp.text


async def test_create_trip_auto_creates_packing_list(auth_client, user, db):
    """Creating a trip must automatically create its packing list."""
    from src.packing import service as packing_service

    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    pl = await packing_service.get_packing_list(db, trip.id)
    assert pl is not None
    assert pl.trip_id == trip.id


# ── Detail ───────────────────────────────────────────────────────────────────


async def test_trip_detail_renders(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    resp = await auth_client.get(f"/trips/{trip.id}")
    assert resp.status_code == 200
    assert trip.name in resp.text
    assert "Flights" in resp.text
    assert "Bags" in resp.text
    assert "Packing" in resp.text


async def test_trip_detail_shows_packing_list(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    resp = await auth_client.get(f"/trips/{trip.id}")
    assert resp.status_code == 200
    # Packing tab should be present
    assert "tab-packing" in resp.text


async def test_trip_not_found(auth_client):
    resp = await auth_client.get("/trips/999999")
    assert resp.status_code == 404


# ── Edit ─────────────────────────────────────────────────────────────────────


async def test_edit_trip_form_renders(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    resp = await auth_client.get(f"/trips/{trip.id}/edit")
    assert resp.status_code == 200
    assert trip.name in resp.text


async def test_edit_trip(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    new_name = _trip_name()
    resp = await auth_client.post(
        f"/trips/{trip.id}/edit",
        data={"name": new_name, "description": "Updated desc"},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/trips/{trip.id}")
    assert new_name in detail.text


# ── Delete ───────────────────────────────────────────────────────────────────


async def test_delete_trip(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    resp = await auth_client.post(f"/trips/{trip.id}/delete", follow_redirects=False)
    assert resp.status_code == 302
    assert "/trips" in resp.headers["location"]

    gone = await auth_client.get(f"/trips/{trip.id}")
    assert gone.status_code == 404


# ── Flights ──────────────────────────────────────────────────────────────────


async def test_add_flight(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    resp = await auth_client.post(
        f"/trips/{trip.id}/flights",
        data={
            "departure_airport": "LHR",
            "arrival_airport": "CDG",
            "flight_number": "BA303",
            "airline": "British Airways",
            "departure_at": "2026-08-01T09:00",
            "arrival_at": "2026-08-01T11:30",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/trips/{trip.id}")
    assert "LHR" in detail.text
    assert "CDG" in detail.text
    assert "BA303" in detail.text


async def test_delete_flight(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    from src.trips.schemas import FlightCreate

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
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))

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
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
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
    trip = await trip_service.create_trip(db, user.id, TripCreate(name=_trip_name()))
    await trip_service.assign_bag(db, trip, bag.id, user.id)

    trip = await trip_service.get_trip(db, trip.id, user.id)
    resp = await auth_client.post(
        f"/trips/{trip.id}/bags",
        data={"bag_id": bag.id},
        follow_redirects=False,
    )
    # Returns 409 (handled as HTTPException, not redirect)
    assert resp.status_code == 409
