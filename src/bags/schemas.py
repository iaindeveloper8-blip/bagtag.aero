from datetime import date

from pydantic import BaseModel, Field

from src.bags.constants import BagColor, BagMaterial, BagType


class BagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    purchased_at: date | None = None
    purchase_price: float | None = Field(default=None, ge=0)
    volume_liters: float | None = Field(default=None, ge=0)
    tare_weight_kg: float | None = Field(default=None, ge=0)

    # IATA Baggage Identification Chart
    color: BagColor | None = None
    bag_type: BagType | None = None
    material: BagMaterial | None = None  # None = soft (IATA default)
    is_cabin_size: bool = False  # K
    has_combination_lock: bool = False  # C
    has_retractable_handle: bool = False  # H
    has_closing_straps: bool = False  # S
    has_wheels: bool = False  # W

    notes: str | None = None


class BagUpdate(BagCreate):
    pass
