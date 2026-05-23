from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.bags import service as bag_service
from src.bags.constants import (
    LABEL_MAP,
    BagMaterial,
    BagType,
    ClosingMechanism,
    HandleType,
    LockType,
    SizeCategory,
    WheelType,
)
from src.bags.dependencies import OwnedBag
from src.bags.schemas import BagCreate, BagUpdate
from src.database import get_db

router = APIRouter(tags=["bags"])
templates = Jinja2Templates(directory="templates")

_ENUM_CONTEXT = {
    "BagType": BagType,
    "BagMaterial": BagMaterial,
    "HandleType": HandleType,
    "WheelType": WheelType,
    "SizeCategory": SizeCategory,
    "ClosingMechanism": ClosingMechanism,
    "LockType": LockType,
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
        context={"bags": bags, "user": user},
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
    bag_type: Annotated[str | None, Form()] = None,
    color_primary: Annotated[str | None, Form()] = None,
    color_secondary: Annotated[str | None, Form()] = None,
    material: Annotated[str | None, Form()] = None,
    handle_type: Annotated[str | None, Form()] = None,
    wheel_type: Annotated[str | None, Form()] = None,
    size_category: Annotated[str | None, Form()] = None,
    closing_mechanism: Annotated[str | None, Form()] = None,
    lock_type: Annotated[str | None, Form()] = None,
    has_straps: Annotated[str | None, Form()] = None,
    strap_color: Annotated[str | None, Form()] = None,
    has_ribbons: Annotated[str | None, Form()] = None,
    ribbon_description: Annotated[str | None, Form()] = None,
    has_name_tag: Annotated[str | None, Form()] = None,
    external_pockets: Annotated[str | None, Form()] = None,
    distinguishing_marks: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
):
    def _parse_float(v: str | None) -> float | None:
        try:
            return float(v) if v and v.strip() else None
        except ValueError:
            return None

    def _parse_int(v: str | None) -> int | None:
        try:
            return int(v) if v and v.strip() else None
        except ValueError:
            return None

    from datetime import date as _date

    def _parse_date(v: str | None):
        try:
            return _date.fromisoformat(v) if v and v.strip() else None
        except ValueError:
            return None

    data = BagCreate(
        name=name,
        brand=brand or None,
        model=model or None,
        purchased_at=_parse_date(purchased_at),
        purchase_price=_parse_float(purchase_price),
        volume_liters=_parse_float(volume_liters),
        tare_weight_kg=_parse_float(tare_weight_kg),
        bag_type=bag_type or None,
        color_primary=color_primary or None,
        color_secondary=color_secondary or None,
        material=material or None,
        handle_type=handle_type or None,
        wheel_type=wheel_type or None,
        size_category=size_category or None,
        closing_mechanism=closing_mechanism or None,
        lock_type=lock_type or None,
        has_straps=has_straps == "on",
        strap_color=strap_color or None,
        has_ribbons=has_ribbons == "on",
        ribbon_description=ribbon_description or None,
        has_name_tag=has_name_tag == "on",
        external_pockets=_parse_int(external_pockets),
        distinguishing_marks=distinguishing_marks or None,
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
    bag_type: Annotated[str | None, Form()] = None,
    color_primary: Annotated[str | None, Form()] = None,
    color_secondary: Annotated[str | None, Form()] = None,
    material: Annotated[str | None, Form()] = None,
    handle_type: Annotated[str | None, Form()] = None,
    wheel_type: Annotated[str | None, Form()] = None,
    size_category: Annotated[str | None, Form()] = None,
    closing_mechanism: Annotated[str | None, Form()] = None,
    lock_type: Annotated[str | None, Form()] = None,
    has_straps: Annotated[str | None, Form()] = None,
    strap_color: Annotated[str | None, Form()] = None,
    has_ribbons: Annotated[str | None, Form()] = None,
    ribbon_description: Annotated[str | None, Form()] = None,
    has_name_tag: Annotated[str | None, Form()] = None,
    external_pockets: Annotated[str | None, Form()] = None,
    distinguishing_marks: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
):
    def _parse_float(v: str | None) -> float | None:
        try:
            return float(v) if v and v.strip() else None
        except ValueError:
            return None

    def _parse_int(v: str | None) -> int | None:
        try:
            return int(v) if v and v.strip() else None
        except ValueError:
            return None

    from datetime import date as _date

    def _parse_date(v: str | None):
        try:
            return _date.fromisoformat(v) if v and v.strip() else None
        except ValueError:
            return None

    data = BagUpdate(
        name=name,
        brand=brand or None,
        model=model or None,
        purchased_at=_parse_date(purchased_at),
        purchase_price=_parse_float(purchase_price),
        volume_liters=_parse_float(volume_liters),
        tare_weight_kg=_parse_float(tare_weight_kg),
        bag_type=bag_type or None,
        color_primary=color_primary or None,
        color_secondary=color_secondary or None,
        material=material or None,
        handle_type=handle_type or None,
        wheel_type=wheel_type or None,
        size_category=size_category or None,
        closing_mechanism=closing_mechanism or None,
        lock_type=lock_type or None,
        has_straps=has_straps == "on",
        strap_color=strap_color or None,
        has_ribbons=has_ribbons == "on",
        ribbon_description=ribbon_description or None,
        has_name_tag=has_name_tag == "on",
        external_pockets=_parse_int(external_pockets),
        distinguishing_marks=distinguishing_marks or None,
        notes=notes or None,
    )
    await bag_service.update_bag(db, bag, data)
    return RedirectResponse(
        url=f"/bags/{bag.id}?success=Bag+updated",
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
