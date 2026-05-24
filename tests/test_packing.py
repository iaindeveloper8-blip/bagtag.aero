"""Packing template and trip packing-list endpoint tests."""

import itertools
from datetime import date

from src.packing import service as packing_service
from src.packing.models import PackingTemplate
from src.packing.schemas import PackingTemplateCreate, PackingTemplateItemCreate
from src.trips import service as trip_service
from src.trips.schemas import TripCreate

_pk_uid = itertools.count(400)

_DEP = date(2026, 8, 1)
_RET = date(2026, 8, 14)


def _tname():
    return f"Template {next(_pk_uid)}"


def _trip_name():
    return f"Packing Trip {next(_pk_uid)}"


def _new_trip(name: str | None = None) -> TripCreate:
    return TripCreate(name=name or _trip_name(), departure_date=_DEP, return_date=_RET)


# ── Default templates ─────────────────────────────────────────────────────────


async def test_template_list_renders(auth_client):
    resp = await auth_client.get("/packing/templates")
    assert resp.status_code == 200
    assert "Packing Templates" in resp.text


async def test_five_default_templates_present(auth_client):
    resp = await auth_client.get("/packing/templates")
    # Seeds 5 default templates; all should appear on the page
    for name in ("Weekend Getaway", "Business Trip", "Beach Holiday", "City Break", "Hiking"):
        assert name in resp.text


async def test_default_template_detail_renders(auth_client, db):
    from sqlalchemy import select

    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True).limit(1)  # noqa: E712
    )
    tmpl = result.scalar_one()
    resp = await auth_client.get(f"/packing/templates/{tmpl.id}")
    assert resp.status_code == 200
    assert tmpl.name in resp.text


async def test_default_template_shows_affiliate_links(auth_client, db):
    from sqlalchemy import select

    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True).limit(1)  # noqa: E712
    )
    tmpl = result.scalar_one()
    resp = await auth_client.get(f"/packing/templates/{tmpl.id}")
    # At least some items should have Amazon links
    assert "amazon" in resp.text
    assert "bagtagaero-20" in resp.text


# ── Clone default template ────────────────────────────────────────────────────


async def test_clone_default_template(auth_client, user, db):
    from sqlalchemy import select

    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True).limit(1)  # noqa: E712
    )
    tmpl = result.scalar_one()
    resp = await auth_client.post(
        f"/packing/templates/{tmpl.id}/clone",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    # Should redirect to the new cloned template
    loc = resp.headers["location"]
    assert "/packing/templates/" in loc


async def test_cloned_items_preserve_affiliate_urls(auth_client, user, db):
    """Affiliate URLs from default templates must carry over to the clone."""
    from sqlalchemy import select

    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True).limit(1)  # noqa: E712
    )
    tmpl_bare = result.scalar_one()
    # Load with items so clone_template can iterate them
    default_tmpl = await packing_service.get_template(db, tmpl_bare.id)
    cloned = await packing_service.clone_template(db, default_tmpl, user.id)

    cloned = await packing_service.get_template(db, cloned.id)
    original_affiliate_count = sum(1 for i in default_tmpl.items if i.affiliate_url)
    cloned_affiliate_count = sum(1 for i in cloned.items if i.affiliate_url)
    assert cloned_affiliate_count == original_affiliate_count


# ── Cannot edit/delete default templates ─────────────────────────────────────


async def test_cannot_edit_default_template(auth_client, db):
    from sqlalchemy import select

    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True).limit(1)  # noqa: E712
    )
    tmpl = result.scalar_one()
    resp = await auth_client.post(
        f"/packing/templates/{tmpl.id}/edit",
        data={"name": "Hacked Name"},
        follow_redirects=False,
    )
    # Redirect back with error
    assert resp.status_code == 302
    assert (
        "error" in resp.headers["location"].lower() or "cannot" in resp.headers["location"].lower()
    )


async def test_cannot_delete_default_template(auth_client, db):
    from sqlalchemy import select

    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True).limit(1)  # noqa: E712
    )
    tmpl = result.scalar_one()
    resp = await auth_client.post(
        f"/packing/templates/{tmpl.id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    # Template should still exist
    still_there = await auth_client.get(f"/packing/templates/{tmpl.id}")
    assert still_there.status_code == 200


# ── User template CRUD ────────────────────────────────────────────────────────


async def test_new_template_form_renders(auth_client):
    resp = await auth_client.get("/packing/templates/new")
    assert resp.status_code == 200
    assert "Create Packing Template" in resp.text


async def test_create_user_template(auth_client):
    name = _tname()
    resp = await auth_client.post(
        "/packing/templates/new",
        data={"name": name, "trip_type": "weekend", "description": "My custom list"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/packing/templates/" in resp.headers["location"]


async def test_user_template_appears_in_list(auth_client):
    name = _tname()
    await auth_client.post("/packing/templates/new", data={"name": name})
    resp = await auth_client.get("/packing/templates")
    assert name in resp.text


async def test_edit_user_template(auth_client, user, db):
    tmpl = await packing_service.create_template(db, user.id, PackingTemplateCreate(name=_tname()))
    new_name = _tname()
    resp = await auth_client.post(
        f"/packing/templates/{tmpl.id}/edit",
        data={"name": new_name},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/packing/templates/{tmpl.id}")
    assert new_name in detail.text


async def test_delete_user_template(auth_client, user, db):
    tmpl = await packing_service.create_template(db, user.id, PackingTemplateCreate(name=_tname()))
    resp = await auth_client.post(
        f"/packing/templates/{tmpl.id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    gone = await auth_client.get(f"/packing/templates/{tmpl.id}")
    assert gone.status_code == 404


# ── Template items ────────────────────────────────────────────────────────────


async def test_add_item_to_user_template(auth_client, user, db):
    tmpl = await packing_service.create_template(db, user.id, PackingTemplateCreate(name=_tname()))
    resp = await auth_client.post(
        f"/packing/templates/{tmpl.id}/items",
        data={"name": "Sunscreen", "category": "toiletries", "quantity": "2"},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/packing/templates/{tmpl.id}")
    assert "Sunscreen" in detail.text


async def test_delete_item_from_user_template(auth_client, user, db):
    tmpl = await packing_service.create_template(db, user.id, PackingTemplateCreate(name=_tname()))
    item = await packing_service.add_template_item(
        db, tmpl, PackingTemplateItemCreate(name="Passport", category="documents")
    )
    resp = await auth_client.post(
        f"/packing/templates/{tmpl.id}/items/{item.id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/packing/templates/{tmpl.id}")
    assert "Passport" not in detail.text


# ── Trip packing list ─────────────────────────────────────────────────────────


async def test_add_item_to_packing_list(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    resp = await auth_client.post(
        f"/packing/trips/{trip.id}/items",
        data={"name": "Laptop charger", "category": "electronics", "quantity": "1"},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/trips/{trip.id}")
    assert "Laptop charger" in detail.text


async def test_toggle_item_packed_returns_json(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    pl = await packing_service.get_packing_list(db, trip.id)
    from src.packing.schemas import PackingListItemCreate

    item = await packing_service.add_list_item(
        db, pl, PackingListItemCreate(name="Toothbrush", category="toiletries")
    )

    resp = await auth_client.post(f"/packing/trips/{trip.id}/items/{item.id}/toggle")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_packed" in data
    assert data["is_packed"] is True

    # Toggle again → unpacked
    resp2 = await auth_client.post(f"/packing/trips/{trip.id}/items/{item.id}/toggle")
    assert resp2.json()["is_packed"] is False


async def test_delete_packing_list_item(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    pl = await packing_service.get_packing_list(db, trip.id)
    from src.packing.schemas import PackingListItemCreate

    item = await packing_service.add_list_item(
        db, pl, PackingListItemCreate(name="Delete me", category="other")
    )

    resp = await auth_client.post(
        f"/packing/trips/{trip.id}/items/{item.id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302

    detail = await auth_client.get(f"/trips/{trip.id}")
    assert "Delete me" not in detail.text


async def test_clone_template_to_trip(auth_client, user, db):
    trip = await trip_service.create_trip(db, user.id, _new_trip())

    from sqlalchemy import select

    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True).limit(1)  # noqa: E712
    )
    tmpl = result.scalar_one()

    resp = await auth_client.post(
        f"/packing/trips/{trip.id}/clone-template",
        data={"template_id": tmpl.id},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    # Items from the default template should now appear in the trip packing list
    pl = await packing_service.get_packing_list(db, trip.id)
    assert len(pl.items) > 0


async def test_cloned_to_trip_items_keep_affiliate_urls(user, db):
    """Affiliate URLs must survive the clone-to-trip operation."""
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    pl = await packing_service.get_packing_list(db, trip.id)

    from sqlalchemy import select

    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True).limit(1)  # noqa: E712
    )
    default_tmpl = result.scalar_one()
    # Reload with items
    default_tmpl = await packing_service.get_template(db, default_tmpl.id)

    await packing_service.clone_template_to_list(db, default_tmpl, pl)

    pl = await packing_service.get_packing_list(db, trip.id)
    expected = sum(1 for i in default_tmpl.items if i.affiliate_url)
    got = sum(1 for i in pl.items if i.affiliate_url)
    assert got == expected


async def test_user_added_items_have_no_affiliate_url(user, db):
    """Items added directly by the user must never have an affiliate URL."""
    trip = await trip_service.create_trip(db, user.id, _new_trip())
    pl = await packing_service.get_packing_list(db, trip.id)
    from src.packing.schemas import PackingListItemCreate

    item = await packing_service.add_list_item(
        db, pl, PackingListItemCreate(name="My own item", category="other")
    )
    assert item.affiliate_url is None
