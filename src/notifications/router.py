from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.database import get_db
from src.notifications import service as notification_service

router = APIRouter(tags=["notifications"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def list_notifications(
    request: Request,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    notifications = await notification_service.get_notifications(db, user.id)
    await notification_service.mark_all_read(db, user.id)
    return templates.TemplateResponse(
        request=request,
        name="notifications/index.html",
        context={"notifications": notifications, "user": user},
    )


@router.get("/unread-count")
async def unread_count(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    count = await notification_service.get_unread_count(db, user.id)
    return JSONResponse({"count": count})


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await notification_service.mark_read(db, user.id, notification_id)
    return RedirectResponse(url="/notifications", status_code=302)
