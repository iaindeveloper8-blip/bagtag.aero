from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.database import get_db
from src.packing import service as packing_service
from src.packing.constants import CATEGORY_ICONS, CATEGORY_LABELS, ItemCategory
from src.packing.dependencies import AnyTemplate, OwnedTemplate
from src.packing.exceptions import CannotEditDefaultTemplate
from src.packing.schemas import (
    PackingListItemCreate,
    PackingTemplateCreate,
    PackingTemplateItemCreate,
    PackingTemplateUpdate,
)
from src.trips.constants import TRIP_TYPE_LABELS, TripType
from src.trips.dependencies import OwnedTrip

router = APIRouter(tags=["packing"])
templates = Jinja2Templates(directory="templates")

_CATEGORY_CONTEXT = {
    "ItemCategory": ItemCategory,
    "CATEGORY_LABELS": CATEGORY_LABELS,
    "CATEGORY_ICONS": CATEGORY_ICONS,
}


# ── Template management ─────────────────────────────────────────────────────


@router.get("/templates", response_class=HTMLResponse)
async def list_templates(
    request: Request,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    all_templates = await packing_service.get_templates(db, user.id)
    default_templates = [t for t in all_templates if t.is_default]
    user_templates = [t for t in all_templates if not t.is_default]
    return templates.TemplateResponse(
        request=request,
        name="packing/templates.html",
        context={
            "user": user,
            "default_templates": default_templates,
            "user_templates": user_templates,
            "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS,
        },
    )


@router.get("/templates/new", response_class=HTMLResponse)
async def new_template_form(request: Request, user: CurrentUser):
    return templates.TemplateResponse(
        request=request,
        name="packing/template_form.html",
        context={
            "user": user,
            "template": None,
            "TripType": TripType,
            "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS,
        },
    )


@router.post("/templates/new")
async def create_template(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    trip_type: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
):
    data = PackingTemplateCreate(
        name=name,
        trip_type=trip_type or None,
        description=description or None,
    )
    tmpl = await packing_service.create_template(db, user.id, data)
    return RedirectResponse(
        url=f"/packing/templates/{tmpl.id}?success=Template+created",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/templates/{template_id}", response_class=HTMLResponse)
async def template_detail(
    request: Request,
    template: AnyTemplate,
    user: CurrentUser,
):
    return templates.TemplateResponse(
        request=request,
        name="packing/template_detail.html",
        context={
            "user": user,
            "template": template,
            "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS,
            **_CATEGORY_CONTEXT,
        },
    )


@router.get("/templates/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_form(
    request: Request,
    template: OwnedTemplate,
    user: CurrentUser,
):
    if template.is_default:
        return RedirectResponse(
            url=f"/packing/templates/{template.id}?error=Default+templates+cannot+be+edited",
            status_code=status.HTTP_302_FOUND,
        )
    return templates.TemplateResponse(
        request=request,
        name="packing/template_form.html",
        context={
            "user": user,
            "template": template,
            "TripType": TripType,
            "TRIP_TYPE_LABELS": TRIP_TYPE_LABELS,
        },
    )


@router.post("/templates/{template_id}/edit")
async def update_template(
    template: OwnedTemplate,
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    trip_type: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
):
    data = PackingTemplateUpdate(
        name=name,
        trip_type=trip_type or None,
        description=description or None,
    )
    try:
        await packing_service.update_template(db, template, data)
    except CannotEditDefaultTemplate:
        return RedirectResponse(
            url=f"/packing/templates/{template.id}?error=Default+templates+cannot+be+edited",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        url=f"/packing/templates/{template.id}?success=Template+updated",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/templates/{template_id}/delete")
async def delete_template(
    template: OwnedTemplate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        await packing_service.delete_template(db, template)
    except CannotEditDefaultTemplate:
        return RedirectResponse(
            url=f"/packing/templates/{template.id}?error=Default+templates+cannot+be+deleted",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        url="/packing/templates?success=Template+deleted",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/templates/{template_id}/clone")
async def clone_template(
    template: AnyTemplate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    cloned = await packing_service.clone_template(db, template, user.id)
    return RedirectResponse(
        url=f"/packing/templates/{cloned.id}?success=Template+cloned.+You+can+now+edit+it.",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/templates/{template_id}/items")
async def add_template_item(
    template: OwnedTemplate,
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    category: Annotated[str, Form()] = "other",
    quantity: Annotated[str, Form()] = "1",
    notes: Annotated[str | None, Form()] = None,
):
    data = PackingTemplateItemCreate(
        name=name,
        category=category,
        quantity=int(quantity) if quantity.isdigit() else 1,
        notes=notes or None,
    )
    try:
        await packing_service.add_template_item(db, template, data)
    except CannotEditDefaultTemplate:
        return RedirectResponse(
            url=f"/packing/templates/{template.id}?error=Clone+this+template+first+to+add+items",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        url=f"/packing/templates/{template.id}?success=Item+added",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/templates/{template_id}/items/{item_id}/delete")
async def delete_template_item(
    template: OwnedTemplate,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        await packing_service.delete_template_item(db, template, item_id)
    except CannotEditDefaultTemplate:
        return RedirectResponse(
            url=f"/packing/templates/{template.id}?error=Default+template+items+cannot+be+deleted",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        url=f"/packing/templates/{template.id}?success=Item+removed",
        status_code=status.HTTP_302_FOUND,
    )


# ── Trip packing list ────────────────────────────────────────────────────────


@router.post("/trips/{trip_id}/items")
async def add_packing_item(
    trip: OwnedTrip,
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    category: Annotated[str, Form()] = "other",
    quantity: Annotated[str, Form()] = "1",
    notes: Annotated[str | None, Form()] = None,
    bag_id: Annotated[str | None, Form()] = None,
):
    packing_list = await packing_service.get_packing_list(db, trip.id)
    data = PackingListItemCreate(
        name=name,
        category=category,
        quantity=int(quantity) if quantity.isdigit() else 1,
        notes=notes or None,
        bag_id=int(bag_id) if bag_id and bag_id.isdigit() else None,
    )
    await packing_service.add_list_item(db, packing_list, data)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Item+added&tab=packing",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/trips/{trip_id}/items/{item_id}/toggle")
async def toggle_packed(
    trip: OwnedTrip,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    packing_list = await packing_service.get_packing_list(db, trip.id)
    item = await packing_service.toggle_item_packed(db, packing_list, item_id)
    return JSONResponse({"is_packed": item.is_packed})


@router.post("/trips/{trip_id}/items/{item_id}/assign-bag")
async def assign_item_bag(
    trip: OwnedTrip,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    bag_id: Annotated[str | None, Form()] = None,
):
    packing_list = await packing_service.get_packing_list(db, trip.id)
    item = next((i for i in packing_list.items if i.id == item_id), None)
    if item:
        item.bag_id = int(bag_id) if bag_id and bag_id.isdigit() else None
        await db.commit()
    return RedirectResponse(
        url=f"/trips/{trip.id}?tab=packing",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/trips/{trip_id}/items/{item_id}/delete")
async def delete_packing_item(
    trip: OwnedTrip,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    packing_list = await packing_service.get_packing_list(db, trip.id)
    await packing_service.delete_list_item(db, packing_list, item_id)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Item+removed&tab=packing",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/trips/{trip_id}/clone-template")
async def clone_template_to_trip(
    trip: OwnedTrip,
    db: Annotated[AsyncSession, Depends(get_db)],
    template_id: Annotated[int, Form()],
):
    template = await packing_service.get_template(db, template_id)
    packing_list = await packing_service.get_packing_list(db, trip.id)
    await packing_service.clone_template_to_list(db, template, packing_list)
    return RedirectResponse(
        url=f"/trips/{trip.id}?success=Template+items+added&tab=packing",
        status_code=status.HTTP_302_FOUND,
    )
