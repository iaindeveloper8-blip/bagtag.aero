from datetime import date

from pydantic import BaseModel, Field

from src.bags.constants import (
    BagMaterial,
    BagType,
    ClosingMechanism,
    HandleType,
    LockType,
    SizeCategory,
    WheelType,
)


class BagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    purchased_at: date | None = None
    purchase_price: float | None = Field(default=None, ge=0)
    volume_liters: float | None = Field(default=None, ge=0)
    tare_weight_kg: float | None = Field(default=None, ge=0)
    bag_type: BagType | None = None
    color_primary: str | None = Field(default=None, max_length=50)
    color_secondary: str | None = Field(default=None, max_length=50)
    material: BagMaterial | None = None
    handle_type: HandleType | None = None
    wheel_type: WheelType | None = None
    size_category: SizeCategory | None = None
    closing_mechanism: ClosingMechanism | None = None
    lock_type: LockType | None = None
    has_straps: bool = False
    strap_color: str | None = Field(default=None, max_length=50)
    has_ribbons: bool = False
    ribbon_description: str | None = Field(default=None, max_length=200)
    has_name_tag: bool = False
    external_pockets: int | None = Field(default=None, ge=0)
    distinguishing_marks: str | None = None
    notes: str | None = None


class BagUpdate(BagCreate):
    pass
