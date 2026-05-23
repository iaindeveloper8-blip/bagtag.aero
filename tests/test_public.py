"""Public bag page tests — anonymous and verified-owner updates."""

import itertools

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.bags import service as bag_service
from src.bags.models import Bag
from src.bags.schemas import BagCreate

_bid = itertools.count(3000)


def _bag_name():
    return f"Public Bag {next(_bid)}"


# ── GET /b/{token} ────────────────────────────────────────────────────────────


async def test_public_bag_renders(anon_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await anon_client.get(f"/b/{bag.public_token}")
    assert resp.status_code == 200
    assert "Leave an Update" in resp.text


async def test_public_bag_not_found(anon_client):
    resp = await anon_client.get("/b/doesnotexist00")
    assert resp.status_code == 404


async def test_public_bag_shows_iata_code(anon_client, user, db):
    bag = await bag_service.create_bag(
        db, user.id, BagCreate(name=_bag_name(), color="BK", bag_type="23")
    )
    resp = await anon_client.get(f"/b/{bag.public_token}")
    assert resp.status_code == 200
    assert "BK23" in resp.text


async def test_non_owner_sees_name_field(anon_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await anon_client.get(f"/b/{bag.public_token}")
    assert resp.status_code == 200
    assert 'name="finder_name"' in resp.text


async def test_owner_sees_verified_owner_banner(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await auth_client.get(f"/b/{bag.public_token}")
    assert resp.status_code == 200
    assert "Verified Owner" in resp.text


async def test_owner_page_hides_name_field(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await auth_client.get(f"/b/{bag.public_token}")
    assert 'name="finder_name"' not in resp.text


# ── POST /b/{token}/updates — anonymous ───────────────────────────────────────


async def test_submit_update_anonymous(anon_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await anon_client.post(
        f"/b/{bag.public_token}/updates",
        data={"finder_name": "Jane Smith", "comment": "Found at carousel 3"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "success" in resp.headers["location"]


async def test_submit_update_with_location(anon_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await anon_client.post(
        f"/b/{bag.public_token}/updates",
        data={
            "finder_name": "Bob",
            "comment": "Found near gate B12",
            "latitude": "51.4700",
            "longitude": "-0.4543",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "success" in resp.headers["location"]


async def test_submit_update_missing_name_redirects_with_error(anon_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await anon_client.post(
        f"/b/{bag.public_token}/updates",
        data={"comment": "Found your bag"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "error" in resp.headers["location"]


async def test_submit_update_unknown_token_redirects(anon_client):
    resp = await anon_client.post(
        "/b/doesnotexist00/updates",
        data={"finder_name": "Jane", "comment": "Found it"},
        follow_redirects=False,
    )
    assert resp.status_code == 302


# ── POST /b/{token}/updates — verified owner ──────────────────────────────────


async def test_verified_owner_update_stored(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await auth_client.post(
        f"/b/{bag.public_token}/updates",
        data={"comment": "Bag has been recovered"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "success" in resp.headers["location"]

    result = await db.execute(
        select(Bag).where(Bag.id == bag.id).options(selectinload(Bag.updates))
    )
    loaded = result.scalar_one()
    assert loaded.updates[-1].finder_name == "Verified Owner"


async def test_verified_owner_badge_in_update_list(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    await auth_client.post(
        f"/b/{bag.public_token}/updates",
        data={"comment": "Owner comment"},
    )
    resp = await auth_client.get(f"/b/{bag.public_token}")
    assert "Verified Owner" in resp.text


async def test_non_owner_cannot_post_as_verified_owner(anon_client, user, db):
    """Anonymous user submitting without a name gets an error, not Verified Owner."""
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await anon_client.post(
        f"/b/{bag.public_token}/updates",
        data={"comment": "Trying without name"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "error" in resp.headers["location"]
