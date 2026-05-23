from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.bags import service as bag_service
from src.bags.constants import LABEL_MAP
from src.bags.exceptions import BagNotFound
from src.bags.schemas import BagUpdateCreate
from src.database import get_db
from src.notifications import service as notification_service

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="templates")


@router.get("/{token}", response_class=HTMLResponse)
async def public_bag(
    request: Request,
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        bag = await bag_service.get_public_bag(db, token)
    except BagNotFound:
        return templates.TemplateResponse(
            request=request,
            name="public/not_found.html",
            status_code=404,
            context={},
        )
    flights = await bag_service.get_relevant_flights(db, bag.id)
    return templates.TemplateResponse(
        request=request,
        name="public/bag.html",
        context={"bag": bag, "flights": flights, "LABEL_MAP": LABEL_MAP},
    )


@router.post("/{token}/updates")
async def submit_bag_update(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    finder_name: Annotated[str, Form()],
    comment: Annotated[str, Form()],
    latitude: Annotated[str | None, Form()] = None,
    longitude: Annotated[str | None, Form()] = None,
):
    try:
        bag = await bag_service.get_public_bag(db, token)
    except BagNotFound:
        return RedirectResponse(url=f"/b/{token}", status_code=status.HTTP_302_FOUND)

    data = BagUpdateCreate(
        finder_name=finder_name.strip(),
        comment=comment.strip(),
        latitude=float(latitude) if latitude and latitude.strip() else None,
        longitude=float(longitude) if longitude and longitude.strip() else None,
    )
    bag_update = await bag_service.create_bag_update(db, bag.id, data)

    location_str = ""
    if data.latitude is not None and data.longitude is not None:
        location_str = " (location shared)"

    message = (
        f'{finder_name} left an update on your bag "{bag.name}"{location_str}: '
        f"{comment[:100]}{'…' if len(comment) > 100 else ''}"
    )
    await notification_service.create_notification(
        db,
        user_id=bag.user_id,
        bag_update_id=bag_update.id,
        message=message,
    )

    return RedirectResponse(
        url=f"/b/{token}?success=Update+submitted+—+thank+you",
        status_code=status.HTTP_302_FOUND,
    )
