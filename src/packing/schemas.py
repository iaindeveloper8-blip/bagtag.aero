from pydantic import BaseModel, Field

from src.packing.constants import ItemCategory
from src.trips.constants import TripType


class PackingTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trip_type: TripType | None = None
    description: str | None = None


class PackingTemplateUpdate(PackingTemplateCreate):
    pass


class PackingTemplateItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: ItemCategory = ItemCategory.OTHER
    quantity: int = Field(default=1, ge=1)
    notes: str | None = Field(default=None, max_length=500)


class PackingListItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: ItemCategory = ItemCategory.OTHER
    quantity: int = Field(default=1, ge=1)
    notes: str | None = Field(default=None, max_length=500)
    bag_id: int | None = None
