from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import OptionalUser
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
    current_user: OptionalUser,
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
    is_owner = current_user is not None and current_user.id == bag.user_id
    return templates.TemplateResponse(
        request=request,
        name="public/bag.html",
        context={"bag": bag, "flights": flights, "LABEL_MAP": LABEL_MAP, "is_owner": is_owner},
    )


@router.post("/{token}/updates")
async def submit_bag_update(
    token: str,
    current_user: OptionalUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    comment: Annotated[str, Form()],
    finder_name: Annotated[str | None, Form()] = None,
    latitude: Annotated[str | None, Form()] = None,
    longitude: Annotated[str | None, Form()] = None,
):
    try:
        bag = await bag_service.get_public_bag(db, token)
    except BagNotFound:
        return RedirectResponse(url=f"/b/{token}", status_code=status.HTTP_302_FOUND)

    is_owner = current_user is not None and current_user.id == bag.user_id
    resolved_name = "Verified Owner" if is_owner else (finder_name or "").strip()
    if not resolved_name:
        return RedirectResponse(
            url=f"/b/{token}?error=Please+provide+your+name",
            status_code=status.HTTP_302_FOUND,
        )

    data = BagUpdateCreate(
        finder_name=resolved_name,
        comment=comment.strip(),
        latitude=float(latitude) if latitude and latitude.strip() else None,
        longitude=float(longitude) if longitude and longitude.strip() else None,
    )
    bag_update = await bag_service.create_bag_update(db, bag.id, data)

    location_str = ""
    if data.latitude is not None and data.longitude is not None:
        location_str = " (location shared)"

    message = (
        f'{resolved_name} left an update on your bag "{bag.name}"{location_str}: '
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
