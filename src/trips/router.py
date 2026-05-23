from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.database import get_db
from src.trips import service as trip_service
from src.trips.constants import TRIP_TYPE_LABELS, TripType
from src.trips.dependencies import OwnedTrip
from src.trips.schemas import FlightCreate, TripCreate, TripUpdate

router = APIRouter(tags=["trips"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def list_trips(
    request: Request,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    trips = await trip_service.get_trips(db, user.id)
    return templates.TemplateResponse(
        request=request,
        name="trips/index.html",
        context={"trips": trips, "user": user, "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_trip_form(request: Request, user: CurrentUser):
    return templates.TemplateResponse(
        request=request,
        name="trips/form.html",
        context={
            "trip": None,
            "user": user,
            "TripType": TripType,
            "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS,
        },
    )


@router.post("/new")
async def create_trip(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    trip_type: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    departure_date: Annotated[str | None, Form()] = None,
    return_date: Annotated[str | None, Form()] = None,
):
    from datetime import date as _date

    def _parse_date(v: str | None):
        try:
            return _date.fromisoformat(v) if v and v.strip() else None
        except ValueError:
            return None

    data = TripCreate(
        name=name,
        trip_type=trip_type or None,
        description=description or None,
        departure_date=_parse_date(departure_date),
        return_date=_parse_date(return_date),
    )
    trip = await trip_service.create_trip(db, user.id, data)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Trip+created",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/{trip_id}", response_class=HTMLResponse)
async def trip_detail(
    request: Request,
    trip: OwnedTrip,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from src.packing import service as packing_service

    available_bags = await trip_service.get_available_bags(db, trip, user.id)
    packing_templates = await packing_service.get_templates(db, user.id)
    return templates.TemplateResponse(
        request=request,
        name="trips/detail.html",
        context={
            "trip": trip,
            "user": user,
            "available_bags": available_bags,
            "packing_templates": packing_templates,
            "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS,
        },
    )


@router.get("/{trip_id}/edit", response_class=HTMLResponse)
async def edit_trip_form(request: Request, trip: OwnedTrip, user: CurrentUser):
    return templates.TemplateResponse(
        request=request,
        name="trips/form.html",
        context={
            "trip": trip,
            "user": user,
            "TripType": TripType,
            "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS,
        },
    )


@router.post("/{trip_id}/edit")
async def update_trip(
    trip: OwnedTrip,
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    trip_type: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    departure_date: Annotated[str | None, Form()] = None,
    return_date: Annotated[str | None, Form()] = None,
):
    from datetime import date as _date

    def _parse_date(v: str | None):
        try:
            return _date.fromisoformat(v) if v and v.strip() else None
        except ValueError:
            return None

    data = TripUpdate(
        name=name,
        trip_type=trip_type or None,
        description=description or None,
        departure_date=_parse_date(departure_date),
        return_date=_parse_date(return_date),
    )
    await trip_service.update_trip(db, trip, data)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Trip+updated",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{trip_id}/delete")
async def delete_trip(
    trip: OwnedTrip,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await trip_service.delete_trip(db, trip)
    return RedirectResponse(
        url="/trips?success=Trip+deleted",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{trip_id}/flights")
async def add_flight(
    trip: OwnedTrip,
    db: Annotated[AsyncSession, Depends(get_db)],
    flight_number: Annotated[str | None, Form()] = None,
    airline: Annotated[str | None, Form()] = None,
    departure_airport: Annotated[str, Form()] = "",
    arrival_airport: Annotated[str, Form()] = "",
    departure_at: Annotated[str | None, Form()] = None,
    arrival_at: Annotated[str | None, Form()] = None,
    is_return: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
):
    from datetime import datetime as _dt

    def _parse_dt(v: str | None):
        if not v or not v.strip():
            return None
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return _dt.strptime(v, fmt)
            except ValueError:
                continue
        return None

    data = FlightCreate(
        flight_number=flight_number or None,
        airline=airline or None,
        departure_airport=(departure_airport or "").upper().strip(),
        arrival_airport=(arrival_airport or "").upper().strip(),
        departure_at=_parse_dt(departure_at),
        arrival_at=_parse_dt(arrival_at),
        is_return=is_return == "on",
        notes=notes or None,
    )
    await trip_service.add_flight(db, trip, data)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Flight+added&tab=flights",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{trip_id}/flights/{flight_id}/delete")
async def delete_flight(
    trip: OwnedTrip,
    flight_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await trip_service.delete_flight(db, trip, flight_id)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Flight+removed&tab=flights",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{trip_id}/bags")
async def assign_bag(
    trip: OwnedTrip,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    bag_id: Annotated[int, Form()],
):
    await trip_service.assign_bag(db, trip, bag_id, user.id)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Bag+assigned&tab=bags",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{trip_id}/bags/{bag_id}/remove")
async def remove_bag(
    trip: OwnedTrip,
    bag_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await trip_service.remove_bag(db, trip, bag_id)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Bag+removed&tab=bags",
        status_code=status.HTTP_302_FOUND,
    )
