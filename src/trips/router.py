from datetime import date
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
    departure_date: Annotated[str, Form()],
    return_date: Annotated[str, Form()],
    trip_type: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
):
    from datetime import date as _date

    data = TripCreate(
        name=name,
        trip_type=trip_type or None,
        description=description or None,
        departure_date=_date.fromisoformat(departure_date),
        return_date=_date.fromisoformat(return_date),
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
    today = date.today()
    is_in_progress = bool(
        trip.departure_date
        and trip.return_date
        and trip.departure_date <= today <= trip.return_date
    )
    active_checkin = trip_service.compute_active_checkin(trip)
    return templates.TemplateResponse(
        request=request,
        name="trips/detail.html",
        context={
            "trip": trip,
            "user": user,
            "available_bags": available_bags,
            "packing_templates": packing_templates,
            "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS,
            "is_in_progress": is_in_progress,
            "active_checkin": active_checkin,
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
    departure_date: Annotated[str, Form()],
    return_date: Annotated[str, Form()],
    trip_type: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
):
    from datetime import date as _date

    data = TripUpdate(
        name=name,
        trip_type=trip_type or None,
        description=description or None,
        departure_date=_date.fromisoformat(departure_date),
        return_date=_date.fromisoformat(return_date),
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
    flight_number: Annotated[str, Form()],
    departure_date: Annotated[str, Form()],
    is_return: Annotated[str | None, Form()] = None,
):
    from datetime import date as _date
    from urllib.parse import quote_plus

    from src.trips.fr24 import lookup_flight

    try:
        dep_date = _date.fromisoformat(departure_date)
    except ValueError:
        return RedirectResponse(
            url=f"/trips/{trip.id}?error=Invalid+departure+date&tab=flights",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        info = await lookup_flight(flight_number.strip().upper(), dep_date)
    except Exception as exc:
        return RedirectResponse(
            url=f"/trips/{trip.id}?error={quote_plus(str(exc))}&tab=flights",
            status_code=status.HTTP_302_FOUND,
        )

    data = FlightCreate(
        flight_number=flight_number.strip().upper(),
        airline=info.airline,
        departure_airport=info.departure_airport,
        arrival_airport=info.arrival_airport,
        departure_at=info.departure_at,
        arrival_at=info.arrival_at,
        is_return=is_return == "on",
    )
    await trip_service.add_flight(db, trip, data)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Flight+added&tab=flights",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{trip_id}/flights/{flight_id}/cancel")
async def cancel_flight(
    trip: OwnedTrip,
    flight_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await trip_service.cancel_flight(db, trip, flight_id)
    return RedirectResponse(
        url=f"/trips/{trip.id}?tab=flights",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{trip_id}/flights/{flight_id}/uncancel")
async def uncancel_flight(
    trip: OwnedTrip,
    flight_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await trip_service.uncancel_flight(db, trip, flight_id)
    return RedirectResponse(
        url=f"/trips/{trip.id}?tab=flights",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{trip_id}/flights/{flight_id}/reroutings")
async def add_rerouting(
    trip: OwnedTrip,
    flight_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    flight_number: Annotated[str, Form()],
    departure_date: Annotated[str, Form()],
):
    from datetime import date as _date
    from urllib.parse import quote_plus

    from src.trips.fr24 import lookup_flight

    parent = next((f for f in trip.flights if f.id == flight_id), None)
    if not parent:
        return RedirectResponse(
            url=f"/trips/{trip.id}?error=Flight+not+found&tab=flights",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        dep_date = _date.fromisoformat(departure_date)
    except ValueError:
        return RedirectResponse(
            url=f"/trips/{trip.id}?error=Invalid+departure+date&tab=flights",
            status_code=status.HTTP_302_FOUND,
        )

    try:
        info = await lookup_flight(flight_number.strip().upper(), dep_date)
    except Exception as exc:
        return RedirectResponse(
            url=f"/trips/{trip.id}?error={quote_plus(str(exc))}&tab=flights",
            status_code=status.HTTP_302_FOUND,
        )

    data = FlightCreate(
        flight_number=flight_number.strip().upper(),
        airline=info.airline,
        departure_airport=info.departure_airport,
        arrival_airport=info.arrival_airport,
        departure_at=info.departure_at,
        arrival_at=info.arrival_at,
        is_return=parent.is_return,
        rerouted_from_id=flight_id,
    )
    await trip_service.add_flight(db, trip, data)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Rerouting+flight+added&tab=flights",
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


@router.get("/{trip_id}/checkin", response_class=HTMLResponse)
async def checkin_page(
    request: Request,
    trip: OwnedTrip,
    user: CurrentUser,
):
    active_checkin = trip_service.compute_active_checkin(trip)
    bag_checkin_by_bag = (
        {bc.bag_id: bc for bc in active_checkin.bag_checkins} if active_checkin else {}
    )
    return templates.TemplateResponse(
        request=request,
        name="trips/checkin.html",
        context={
            "trip": trip,
            "user": user,
            "active_checkin": active_checkin,
            "bag_checkin_by_bag": bag_checkin_by_bag,
        },
    )


@router.post("/{trip_id}/checkin")
async def save_checkin(
    request: Request,
    trip: OwnedTrip,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    form = await request.form()
    checkin_data: dict[int, dict] = {}

    for tb in trip.trip_bags:
        bag_id = tb.bag_id
        checkin_status = form.get(f"status_{bag_id}")
        if not checkin_status:
            continue

        raw_lp = form.get(f"licence_plate_{bag_id}") or ""
        licence_plate = raw_lp.strip().upper()[:10] or None

        weight_kg = None
        raw_weight = form.get(f"weight_kg_{bag_id}") or ""
        try:
            if raw_weight.strip():
                weight_kg = float(raw_weight)
        except (ValueError, AttributeError):
            pass

        checkin_data[bag_id] = {
            "status": str(checkin_status),
            "licence_plate_number": licence_plate,
            "weight_kg": weight_kg,
        }

    active_checkin = trip_service.compute_active_checkin(trip)
    checkin = await trip_service.save_checkin(db, trip, active_checkin, checkin_data)

    for tb in trip.trip_bags:
        receipt_file = form.get(f"receipt_{tb.bag_id}")
        if receipt_file and hasattr(receipt_file, "filename") and receipt_file.filename:
            await trip_service.save_checkin_bag_receipt(db, checkin.id, tb.bag_id, receipt_file)

    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Check-in+saved&tab=bags",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/{trip_id}/collect", response_class=HTMLResponse)
async def collect_page(
    request: Request,
    trip: OwnedTrip,
    user: CurrentUser,
):
    active_checkin = trip_service.compute_active_checkin(trip)
    if not active_checkin:
        return RedirectResponse(
            url=f"/trips/{trip.id}?error=No+checked+bags+to+collect&tab=bags",
            status_code=status.HTTP_302_FOUND,
        )
    checked_in = [bc for bc in active_checkin.bag_checkins if bc.status == "checked_in"]
    return templates.TemplateResponse(
        request=request,
        name="trips/collect.html",
        context={
            "trip": trip,
            "user": user,
            "active_checkin": active_checkin,
            "checked_in": checked_in,
        },
    )


@router.post("/{trip_id}/collect")
async def save_collect(
    request: Request,
    trip: OwnedTrip,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    active_checkin = trip_service.compute_active_checkin(trip)
    if not active_checkin:
        return RedirectResponse(
            url=f"/trips/{trip.id}?error=No+checked+bags+to+collect&tab=bags",
            status_code=status.HTTP_302_FOUND,
        )
    form = await request.form()
    collected_ids = [int(v) for k, v in form.multi_items() if k == "collected_bag_id"]
    await trip_service.mark_checkin_bags_collected(db, active_checkin, collected_ids)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Bag+collection+confirmed&tab=bags",
        status_code=status.HTTP_302_FOUND,
    )
