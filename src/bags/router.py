from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.bags import service as bag_service
from src.bags.constants import (
    LABEL_MAP,
    BagColor,
    BagMaterial,
    BagType,
)
from src.bags.dependencies import OwnedBag
from src.bags.schemas import BagCreate, BagUpdate
from src.database import get_db

router = APIRouter(tags=["bags"])
templates = Jinja2Templates(directory="templates")

_ENUM_CONTEXT = {
    "BagColor": BagColor,
    "BagType": BagType,
    "BagMaterial": BagMaterial,
    "LABEL_MAP": LABEL_MAP,
}


@router.get("/", response_class=HTMLResponse)
async def list_bags(
    request: Request,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    bags = await bag_service.get_bags(db, user.id)
    return templates.TemplateResponse(
        request=request,
        name="bags/index.html",
        context={"bags": bags, "user": user, **_ENUM_CONTEXT},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_bag_form(request: Request, user: CurrentUser):
    return templates.TemplateResponse(
        request=request,
        name="bags/form.html",
        context={"bag": None, "user": user, **_ENUM_CONTEXT},
    )


@router.post("/new")
async def create_bag(
    request: Request,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    brand: Annotated[str | None, Form()] = None,
    model: Annotated[str | None, Form()] = None,
    purchased_at: Annotated[str | None, Form()] = None,
    purchase_price: Annotated[str | None, Form()] = None,
    volume_liters: Annotated[str | None, Form()] = None,
    tare_weight_kg: Annotated[str | None, Form()] = None,
    color: Annotated[str | None, Form()] = None,
    bag_type: Annotated[str | None, Form()] = None,
    material: Annotated[str | None, Form()] = None,
    is_cabin_size: Annotated[str | None, Form()] = None,
    has_combination_lock: Annotated[str | None, Form()] = None,
    has_retractable_handle: Annotated[str | None, Form()] = None,
    has_closing_straps: Annotated[str | None, Form()] = None,
    has_wheels: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
):
    data = BagCreate(
        name=name,
        brand=brand or None,
        model=model or None,
        purchased_at=_parse_date(purchased_at),
        purchase_price=_parse_float(purchase_price),
        volume_liters=_parse_float(volume_liters),
        tare_weight_kg=_parse_float(tare_weight_kg),
        color=color or None,
        bag_type=bag_type or None,
        material=material or None,
        is_cabin_size=is_cabin_size == "on",
        has_combination_lock=has_combination_lock == "on",
        has_retractable_handle=has_retractable_handle == "on",
        has_closing_straps=has_closing_straps == "on",
        has_wheels=has_wheels == "on",
        notes=notes or None,
    )
    bag = await bag_service.create_bag(db, user.id, data)
    return RedirectResponse(
        url=f"/bags/{bag.id}?success=Bag+added+successfully",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/{bag_id}", response_class=HTMLResponse)
async def bag_detail(request: Request, bag: OwnedBag, user: CurrentUser):
    return templates.TemplateResponse(
        request=request,
        name="bags/detail.html",
        context={"bag": bag, "user": user, **_ENUM_CONTEXT},
    )


@router.get("/{bag_id}/edit", response_class=HTMLResponse)
async def edit_bag_form(request: Request, bag: OwnedBag, user: CurrentUser):
    return templates.TemplateResponse(
        request=request,
        name="bags/form.html",
        context={"bag": bag, "user": user, **_ENUM_CONTEXT},
    )


@router.post("/{bag_id}/edit")
async def update_bag(
    bag: OwnedBag,
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str, Form()],
    brand: Annotated[str | None, Form()] = None,
    model: Annotated[str | None, Form()] = None,
    purchased_at: Annotated[str | None, Form()] = None,
    purchase_price: Annotated[str | None, Form()] = None,
    volume_liters: Annotated[str | None, Form()] = None,
    tare_weight_kg: Annotated[str | None, Form()] = None,
    color: Annotated[str | None, Form()] = None,
    bag_type: Annotated[str | None, Form()] = None,
    material: Annotated[str | None, Form()] = None,
    is_cabin_size: Annotated[str | None, Form()] = None,
    has_combination_lock: Annotated[str | None, Form()] = None,
    has_retractable_handle: Annotated[str | None, Form()] = None,
    has_closing_straps: Annotated[str | None, Form()] = None,
    has_wheels: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
):
    data = BagUpdate(
        name=name,
        brand=brand or None,
        model=model or None,
        purchased_at=_parse_date(purchased_at),
        purchase_price=_parse_float(purchase_price),
        volume_liters=_parse_float(volume_liters),
        tare_weight_kg=_parse_float(tare_weight_kg),
        color=color or None,
        bag_type=bag_type or None,
        material=material or None,
        is_cabin_size=is_cabin_size == "on",
        has_combination_lock=has_combination_lock == "on",
        has_retractable_handle=has_retractable_handle == "on",
        has_closing_straps=has_closing_straps == "on",
        has_wheels=has_wheels == "on",
        notes=notes or None,
    )
    await bag_service.update_bag(db, bag, data)
    return RedirectResponse(
        url=f"/bags/{bag.id}?success=Bag+updated",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{bag_id}/regenerate-token")
async def regenerate_token(
    bag: OwnedBag,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await bag_service.regenerate_public_token(db, bag)
    return RedirectResponse(
        url=f"/bags/{bag.id}?success=Public+link+regenerated",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{bag_id}/delete")
async def delete_bag(
    bag: OwnedBag,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await bag_service.delete_bag(db, bag)
    return RedirectResponse(
        url="/bags?success=Bag+deleted",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{bag_id}/images")
async def upload_image(
    bag: OwnedBag,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    description: Annotated[str | None, Form()] = None,
):
    await bag_service.add_image(db, bag, file, description or None)
    return RedirectResponse(
        url=f"/bags/{bag.id}?success=Image+uploaded",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{bag_id}/images/{image_id}/delete")
async def delete_image(
    bag: OwnedBag,
    image_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await bag_service.delete_image(db, bag, image_id)
    return RedirectResponse(
        url=f"/bags/{bag.id}?success=Image+removed",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{bag_id}/images/{image_id}/set-primary")
async def set_primary_image(
    bag: OwnedBag,
    image_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await bag_service.set_primary_image(db, bag, image_id)
    return RedirectResponse(
        url=f"/bags/{bag.id}?success=Primary+image+updated",
        status_code=status.HTTP_302_FOUND,
    )


def _parse_float(v: str | None) -> float | None:
    try:
        return float(v) if v and v.strip() else None
    except ValueError:
        return None


def _parse_date(v: str | None):
    from datetime import date as _date

    try:
        return _date.fromisoformat(v) if v and v.strip() else None
    except ValueError:
        return None
