"""Notification service and router tests."""

import itertools

from src.bags import service as bag_service
from src.bags.schemas import BagCreate, BagUpdateCreate
from src.notifications import service as notification_service

_nid = itertools.count(5000)


def _bag_name():
    return f"Notif Bag {next(_nid)}"


async def _make_bag_and_update(db, user):
    bag = await bag_service.create_bag(db, user.id, BagCreate(name=_bag_name()))
    update = await bag_service.create_bag_update(
        db, bag.id, BagUpdateCreate(finder_name="Finder", comment="Found it")
    )
    return bag, update


# ── Service ───────────────────────────────────────────────────────────────────


async def test_create_notification(user, db):
    _, update = await _make_bag_and_update(db, user)
    notif = await notification_service.create_notification(
        db, user.id, update.id, "Your bag was found"
    )
    assert notif.id is not None
    assert notif.message == "Your bag was found"
    assert not notif.is_read


async def test_get_notifications_returns_created(user, db):
    _, update = await _make_bag_and_update(db, user)
    notif = await notification_service.create_notification(db, user.id, update.id, "msg")
    results = await notification_service.get_notifications(db, user.id)
    assert any(n.id == notif.id for n in results)


async def test_get_unread_count_increments(user, db):
    before = await notification_service.get_unread_count(db, user.id)
    _, update = await _make_bag_and_update(db, user)
    await notification_service.create_notification(db, user.id, update.id, "new")
    after = await notification_service.get_unread_count(db, user.id)
    assert after == before + 1


async def test_mark_read(user, db):
    _, update = await _make_bag_and_update(db, user)
    notif = await notification_service.create_notification(db, user.id, update.id, "msg")
    assert not notif.is_read
    await notification_service.mark_read(db, user.id, notif.id)
    await db.refresh(notif)
    assert notif.is_read


async def test_mark_all_read_clears_count(user, db):
    _, u1 = await _make_bag_and_update(db, user)
    _, u2 = await _make_bag_and_update(db, user)
    await notification_service.create_notification(db, user.id, u1.id, "one")
    await notification_service.create_notification(db, user.id, u2.id, "two")
    await notification_service.mark_all_read(db, user.id)
    assert await notification_service.get_unread_count(db, user.id) == 0


async def test_mark_read_wrong_user_does_not_affect(user, db):
    """mark_read for a different user_id should not mark the notification read."""
    _, update = await _make_bag_and_update(db, user)
    notif = await notification_service.create_notification(db, user.id, update.id, "msg")
    await notification_service.mark_read(db, user_id=99999, notification_id=notif.id)
    await db.refresh(notif)
    assert not notif.is_read


# ── Router ────────────────────────────────────────────────────────────────────


async def test_notifications_page_renders(auth_client):
    resp = await auth_client.get("/notifications/")
    assert resp.status_code == 200


async def test_notifications_page_marks_all_read(auth_client, user, db):
    _, update = await _make_bag_and_update(db, user)
    await notification_service.create_notification(db, user.id, update.id, "unread")
    await auth_client.get("/notifications/")
    assert await notification_service.get_unread_count(db, user.id) == 0


async def test_unread_count_endpoint_returns_json(auth_client):
    resp = await auth_client.get("/notifications/unread-count")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert isinstance(data["count"], int)


async def test_mark_read_endpoint(auth_client, user, db):
    _, update = await _make_bag_and_update(db, user)
    notif = await notification_service.create_notification(db, user.id, update.id, "needs reading")
    resp = await auth_client.post(f"/notifications/{notif.id}/read", follow_redirects=False)
    assert resp.status_code == 302
    await db.refresh(notif)
    assert notif.is_read


async def test_notifications_requires_auth(anon_client):
    resp = await anon_client.get("/notifications/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]


async def test_unread_count_requires_auth(anon_client):
    resp = await anon_client.get("/notifications/unread-count", follow_redirects=False)
    assert resp.status_code == 302
