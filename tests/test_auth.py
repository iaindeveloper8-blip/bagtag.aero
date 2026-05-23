"""Auth endpoint tests — register, login, logout, protected-route redirect."""

import itertools

import pytest

_reg_uid = itertools.count(100)


def _reg_data(suffix=None):
    n = suffix if suffix is not None else next(_reg_uid)
    return {
        "username": f"newuser{n}",
        "email": f"newuser{n}@test.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
    }


# ── Page rendering ───────────────────────────────────────────────────────────


async def test_login_page_renders(anon_client):
    resp = await anon_client.get("/auth/login")
    assert resp.status_code == 200
    assert "Sign in" in resp.text
    assert "<form" in resp.text


async def test_register_page_renders(anon_client):
    resp = await anon_client.get("/auth/register")
    assert resp.status_code == 200
    assert "Create an account" in resp.text
    assert "<form" in resp.text


# ── Registration ─────────────────────────────────────────────────────────────


async def test_register_success(anon_client):
    data = _reg_data()
    resp = await anon_client.post("/auth/register", data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]


async def test_register_duplicate_username(anon_client, user):
    data = _reg_data()
    data["username"] = user.username
    data["email"] = "unique_dup@test.com"
    resp = await anon_client.post("/auth/register", data=data)
    assert resp.status_code == 409
    assert "already registered" in resp.text


async def test_register_password_mismatch(anon_client):
    data = _reg_data()
    data["password_confirm"] = "different"
    resp = await anon_client.post("/auth/register", data=data)
    assert resp.status_code == 422
    assert "Passwords do not match" in resp.text


async def test_register_invalid_username_chars(anon_client):
    data = _reg_data()
    data["username"] = "bad user name!"
    resp = await anon_client.post("/auth/register", data=data)
    # Pydantic validation fails — returns 422 with error
    assert resp.status_code in {422, 200}


# ── Login ────────────────────────────────────────────────────────────────────


async def test_login_success_sets_cookie(anon_client, user, db):
    from sqlalchemy import update

    from src.auth.models import User
    from src.auth.service import _hash_password

    # Ensure the user has a known password
    hashed = _hash_password("KnownPass1!")
    await db.execute(update(User).where(User.id == user.id).values(hashed_password=hashed))
    await db.commit()

    resp = await anon_client.post(
        "/auth/login",
        data={"username": user.username, "password": "KnownPass1!", "next": "/"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "access_token" in resp.cookies


async def test_login_wrong_password(anon_client, user):
    resp = await anon_client.post(
        "/auth/login",
        data={"username": user.username, "password": "wrongpassword", "next": "/"},
    )
    assert resp.status_code == 401
    assert "Invalid" in resp.text


async def test_login_unknown_user(anon_client):
    resp = await anon_client.post(
        "/auth/login",
        data={"username": "nobody_exists", "password": "pass", "next": "/"},
    )
    assert resp.status_code == 401


# ── Logout ───────────────────────────────────────────────────────────────────


async def test_logout_clears_cookie(auth_client):
    resp = await auth_client.post("/auth/logout", follow_redirects=False)
    assert resp.status_code == 302
    # Cookie is deleted (set with empty/expired value)
    assert resp.cookies.get("access_token") == "" or "access_token" not in resp.cookies


# ── Protected-route redirect ─────────────────────────────────────────────────


@pytest.mark.parametrize("path", ["/bags/", "/trips/", "/packing/templates"])
async def test_protected_routes_redirect_unauthenticated(anon_client, path):
    resp = await anon_client.get(path, follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]


async def test_landing_page_unauthenticated(anon_client):
    resp = await anon_client.get("/", follow_redirects=False)
    assert resp.status_code == 200
    assert "bagtag" in resp.text.lower()


async def test_landing_redirects_authenticated(auth_client):
    resp = await auth_client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/dashboard"


async def test_authenticated_dashboard(auth_client):
    resp = await auth_client.get("/dashboard")
    assert resp.status_code == 200
    assert "bagtag" in resp.text.lower()


# ── Invalid / tampered cookies ───────────────────────────────────────────────


async def test_invalid_token_cookie_redirects_to_login(anon_client):
    """A garbage JWT in the cookie should redirect rather than 500."""
    anon_client.cookies.set("access_token", "not.a.valid.jwt")
    resp = await anon_client.get("/bags/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]


async def test_token_for_nonexistent_user_redirects_to_login(anon_client):
    """A valid JWT for a user ID that doesn't exist should redirect."""
    from src.auth import service as auth_service

    token = auth_service.create_access_token(user_id=999999)
    anon_client.cookies.set("access_token", token)
    resp = await anon_client.get("/bags/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]


async def test_invalid_token_on_optional_route_shows_landing(anon_client):
    """An invalid cookie on an OptionalUser route should still render (not crash)."""
    anon_client.cookies.set("access_token", "garbage.token.value")
    resp = await anon_client.get("/", follow_redirects=False)
    assert resp.status_code == 200


async def test_login_redirects_to_dashboard_on_external_next(anon_client, user, db):
    """An external URL in 'next' must be silently replaced with '/' for safety."""
    from sqlalchemy import update

    from src.auth.models import User
    from src.auth.service import _hash_password

    hashed = _hash_password("SafePass1!")
    await db.execute(update(User).where(User.id == user.id).values(hashed_password=hashed))
    await db.commit()

    resp = await anon_client.post(
        "/auth/login",
        data={
            "username": user.username,
            "password": "SafePass1!",
            "next": "https://evil.com/steal",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


async def test_login_inactive_user_rejected(anon_client, db):
    """An inactive account must not be able to log in."""
    from sqlalchemy import update

    from src.auth import service as auth_service
    from src.auth.models import User
    from src.auth.schemas import UserCreate
    from src.auth.service import _hash_password

    inactive = await auth_service.create_user(
        db,
        UserCreate(username="inactiveuser", email="inactive@test.com", password="Password123!"),
    )
    pw = _hash_password("Password123!")
    await db.execute(
        update(User).where(User.id == inactive.id).values(hashed_password=pw, is_active=False)
    )
    await db.commit()

    resp = await anon_client.post(
        "/auth/login",
        data={"username": "inactiveuser", "password": "Password123!", "next": "/"},
    )
    assert resp.status_code == 401
