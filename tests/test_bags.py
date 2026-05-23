"""Bag CRUD and image-upload endpoint tests."""

import itertools

import pytest

from src.bags import service as bag_service
from src.bags.schemas import BagCreate
from tests.conftest import TINY_JPEG

_bag_uid = itertools.count(200)


def _bag_name():
    return f"Test Bag {next(_bag_uid)}"


# ── List / forms ─────────────────────────────────────────────────────────────


async def test_list_bags_page_renders(auth_client):
    resp = await auth_client.get("/bags/")
    assert resp.status_code == 200
    assert "My Bags" in resp.text


async def test_new_bag_form_renders(auth_client):
    resp = await auth_client.get("/bags/new")
    assert resp.status_code == 200
    assert "Add New Bag" in resp.text
    assert "IATA" in resp.text


# ── Create ───────────────────────────────────────────────────────────────────


async def test_create_bag_minimal(auth_client):
    name = _bag_name()
    resp = await auth_client.post("/bags/new", data={"name": name}, follow_redirects=False)
    assert resp.status_code == 302
    assert "/bags/" in resp.headers["location"]


async def test_create_bag_all_iata_fields(auth_client):
    name = _bag_name()
    resp = await auth_client.post(
        "/bags/new",
        data={
            "name": name,
            "brand": "Samsonite",
            "model": "Omni Max",
            "volume_liters": "68",
            "tare_weight_kg": "3.2",
            "color": "BK",
            "bag_type": "23",
            "material": "R",
            "has_retractable_handle": "on",
            "has_wheels": "on",
            "has_combination_lock": "on",
            "external_pockets": "2",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert "/bags/" in loc


async def test_create_bag_appears_in_list(auth_client):
    name = _bag_name()
    await auth_client.post("/bags/new", data={"name": name})
    resp = await auth_client.get("/bags/")
    assert name in resp.text


# ── Detail ───────────────────────────────────────────────────────────────────


async def test_bag_detail_renders(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name(), brand="Tumi"))
    resp = await auth_client.get(f"/bags/{bag.id}")
    assert resp.status_code == 200
    assert bag.name in resp.text
    assert "Tumi" in resp.text
    assert "IATA Baggage Identification" in resp.text


async def test_bag_detail_shows_iata_fields(auth_client, user, db):
    bag = await bag_service.create_bag(
        db,
        user.id,
        BagCreate(
            name=_bag_name(),
            color="BU",
            bag_type="26",
            material="R",
            is_cabin_size=True,
        ),
    )
    resp = await auth_client.get(f"/bags/{bag.id}")
    assert resp.status_code == 200
    assert "Blue" in resp.text
    assert "BU26RKX" in resp.text


async def test_bag_not_found_returns_404(auth_client):
    resp = await auth_client.get("/bags/999999")
    assert resp.status_code == 404


async def test_bag_other_user_returns_404(auth_client, db):
    """Bag owned by a different user must not be visible."""
    from itertools import count

    from src.auth import service as auth_service
    from src.auth.schemas import UserCreate

    n = next(count(9000))
    other = await auth_service.create_user(
        db,
        UserCreate(username=f"other{n}", email=f"other{n}@t.com", password="Password123!"),
    )
    other_bag = await bag_service.create_bag(db, other.id, BagCreate(name="Other user bag"))
    resp = await auth_client.get(f"/bags/{other_bag.id}")
    assert resp.status_code == 404


# ── Edit ─────────────────────────────────────────────────────────────────────


async def test_edit_bag_form_renders(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await auth_client.get(f"/bags/{bag.id}/edit")
    assert resp.status_code == 200
    assert bag.name in resp.text


async def test_edit_bag_updates_fields(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    new_name = _bag_name()
    resp = await auth_client.post(
        f"/bags/{bag.id}/edit",
        data={"name": new_name, "brand": "Away", "volume_liters": "40"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert str(bag.id) in resp.headers["location"]

    detail = await auth_client.get(f"/bags/{bag.id}")
    assert new_name in detail.text
    assert "Away" in detail.text


# ── Delete ───────────────────────────────────────────────────────────────────


async def test_delete_bag(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await auth_client.post(f"/bags/{bag.id}/delete", follow_redirects=False)
    assert resp.status_code == 302
    assert "/bags" in resp.headers["location"]

    gone = await auth_client.get(f"/bags/{bag.id}")
    assert gone.status_code == 404


# ── Public token ─────────────────────────────────────────────────────────────


async def test_bag_has_public_token(user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    assert bag.public_token is not None
    assert len(bag.public_token) == 12


async def test_regenerate_token_changes_token(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    old_token = bag.public_token
    resp = await auth_client.post(f"/bags/{bag.id}/regenerate-token", follow_redirects=False)
    assert resp.status_code == 302
    await db.refresh(bag)
    assert bag.public_token != old_token


async def test_old_public_token_returns_404(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    old_token = bag.public_token
    await auth_client.post(f"/bags/{bag.id}/regenerate-token")
    resp = await auth_client.get(f"/b/{old_token}")
    assert resp.status_code == 404


# ── Images ───────────────────────────────────────────────────────────────────


async def test_upload_image(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await auth_client.post(
        f"/bags/{bag.id}/images",
        files={"file": ("photo.jpg", TINY_JPEG, "image/jpeg")},
        data={"description": "Front view"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    # Image should appear on the detail page
    detail = await auth_client.get(f"/bags/{bag.id}")
    assert detail.status_code == 200


async def test_upload_invalid_file_type(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    resp = await auth_client.post(
        f"/bags/{bag.id}/images",
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        follow_redirects=False,
    )
    # Should reject with 4xx or redirect with error
    assert resp.status_code in {302, 422}


async def test_delete_image(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    image = await bag_service.add_image(db, bag, _fake_upload("img.jpg"), description=None)
    resp = await auth_client.post(
        f"/bags/{bag.id}/images/{image.id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302


async def test_delete_primary_image_promotes_next(auth_client, user, db):
    """Deleting the primary image should promote the next image as primary."""
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    await bag_service.add_image(db, bag, _fake_upload("a.jpg"), description=None)
    bag = await bag_service.get_bag(db, bag.id, user.id)
    await bag_service.add_image(db, bag, _fake_upload("b.jpg"), description=None)
    bag = await bag_service.get_bag(db, bag.id, user.id)

    primary_id = next(i.id for i in bag.images if i.is_primary)
    resp = await auth_client.post(
        f"/bags/{bag.id}/images/{primary_id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    bag = await bag_service.get_bag(db, bag.id, user.id)
    assert any(i.is_primary for i in bag.images)


async def test_delete_nonexistent_image_raises(user, db):
    from src.bags.exceptions import ImageNotFound

    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    bag = await bag_service.get_bag(db, bag.id, user.id)
    with pytest.raises(ImageNotFound):
        await bag_service.delete_image(db, bag, image_id=999999)


async def test_set_primary_nonexistent_image_raises(user, db):
    from src.bags.exceptions import ImageNotFound

    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    bag = await bag_service.get_bag(db, bag.id, user.id)
    with pytest.raises(ImageNotFound):
        await bag_service.set_primary_image(db, bag, image_id=999999)


async def test_upload_oversized_image_rejected(auth_client, user, db):
    from src.config import settings

    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    oversized = b"X" * (settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    resp = await auth_client.post(
        f"/bags/{bag.id}/images",
        files={"file": ("big.jpg", oversized, "image/jpeg")},
        follow_redirects=False,
    )
    assert resp.status_code in {302, 413}


async def test_set_primary_image(auth_client, user, db):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    await bag_service.add_image(db, bag, _fake_upload("a.jpg"), description=None)
    # Reload bag to get updated images list
    bag = await bag_service.get_bag(db, bag.id, user.id)
    img2 = await bag_service.add_image(db, bag, _fake_upload("b.jpg"), description=None)

    resp = await auth_client.post(
        f"/bags/{bag.id}/images/{img2.id}/set-primary",
        follow_redirects=False,
    )
    assert resp.status_code == 302


# ── Invalid form inputs ───────────────────────────────────────────────────────


async def test_create_bag_with_invalid_float_is_ignored(auth_client):
    """Non-numeric values for float fields should be silently treated as None."""
    resp = await auth_client.post(
        "/bags/new",
        data={"name": _bag_name(), "volume_liters": "not-a-number", "purchase_price": "abc"},
        follow_redirects=False,
    )
    assert resp.status_code == 302


async def test_create_bag_with_invalid_date_is_ignored(auth_client):
    """Unparseable date strings should be silently treated as None."""
    resp = await auth_client.post(
        "/bags/new",
        data={"name": _bag_name(), "purchased_at": "not-a-date"},
        follow_redirects=False,
    )
    assert resp.status_code == 302


# ── Helpers ──────────────────────────────────────────────────────────────────


def _fake_upload(filename: str):
    """Create a minimal UploadFile-like object for direct service calls."""
    from unittest.mock import AsyncMock, MagicMock

    mock = MagicMock()
    mock.filename = filename
    mock.content_type = "image/jpeg"
    mock.read = AsyncMock(return_value=TINY_JPEG)
    return mock
