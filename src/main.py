from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Ensure all models are registered with Base.metadata before create_all
import src.auth.models  # noqa: F401, E402
import src.bags.models  # noqa: F401, E402
import src.notifications.models  # noqa: F401, E402
import src.packing.models  # noqa: F401, E402
import src.trips.models  # noqa: F401, E402
from src.auth import router as auth_router
from src.auth.dependencies import CurrentUser, OptionalUser
from src.bags import public_router as bags_public_router
from src.bags import router as bags_router
from src.bags.models import Bag
from src.config import settings
from src.database import Base, SessionFactory, engine, get_db
from src.exceptions import RedirectToLogin
from src.notifications import router as notifications_router
from src.packing import router as packing_router
from src.trips import router as trips_router
from src.trips.models import Trip, TripCheckin
from src.trips.service import compute_active_checkin


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionFactory() as db:
        from src.packing.seed import seed_default_templates

        await seed_default_templates(db)

    yield

    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="Track your luggage and trips — bagtag.aero",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT in {"local", "staging"} else None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router.router, prefix="/auth")
app.include_router(bags_router.router, prefix="/bags")
app.include_router(bags_public_router.router, prefix="/b")
app.include_router(trips_router.router, prefix="/trips")
app.include_router(packing_router.router, prefix="/packing")
app.include_router(notifications_router.router, prefix="/notifications")


@app.exception_handler(RedirectToLogin)
async def redirect_to_login_handler(request: Request, exc: RedirectToLogin):
    return RedirectResponse(
        url=f"/auth/login?next={quote(exc.next_url, safe='')}",
        status_code=302,
    )


templates = Jinja2Templates(directory="templates")


@app.get("/")
async def landing(request: Request, user: OptionalUser):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="landing.html", context={})


@app.get("/dashboard")
async def dashboard(
    request: Request,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from datetime import date

    bag_count = (await db.execute(select(func.count()).where(Bag.user_id == user.id))).scalar()
    trip_count = (await db.execute(select(func.count()).where(Trip.user_id == user.id))).scalar()

    today = date.today()

    from src.trips.models import Flight

    current_trips_result = await db.execute(
        select(Trip)
        .where(
            Trip.user_id == user.id,
            Trip.departure_date <= today,
            Trip.return_date >= today,
        )
        .options(
            selectinload(Trip.flights).selectinload(Flight.reroutings),
            selectinload(Trip.trip_bags),
            selectinload(Trip.checkins).selectinload(TripCheckin.bag_checkins),
        )
        .order_by(Trip.departure_date.asc())
    )
    current_trips = list(current_trips_result.scalars().all())
    active_checkins = {t.id: compute_active_checkin(t) for t in current_trips}

    upcoming_result = await db.execute(
        select(Trip)
        .where(Trip.user_id == user.id, Trip.departure_date > today)
        .options(selectinload(Trip.flights).selectinload(Flight.reroutings))
        .order_by(Trip.departure_date.asc())
        .limit(3)
    )
    upcoming_trips = list(upcoming_result.scalars().all())

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "bag_count": bag_count,
            "trip_count": trip_count,
            "current_trips": current_trips,
            "upcoming_trips": upcoming_trips,
            "active_checkins": active_checkins,
        },
    )
