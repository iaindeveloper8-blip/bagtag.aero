from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Bag(Base):
    __tablename__ = "bag"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    purchased_at: Mapped[date | None] = mapped_column(Date)
    purchase_price: Mapped[float | None] = mapped_column(Float)
    volume_liters: Mapped[float | None] = mapped_column(Float)
    tare_weight_kg: Mapped[float | None] = mapped_column(Float)

    # IATA Baggage Identification Chart fields
    color: Mapped[str | None] = mapped_column(String(2))  # BagColor code, e.g. "BK"
    bag_type: Mapped[str | None] = mapped_column(String(2))  # BagType code, e.g. "25"
    material: Mapped[str | None] = mapped_column(String(1))  # BagMaterial code; None = soft
    is_cabin_size: Mapped[bool] = mapped_column(Boolean, default=False)  # K
    has_combination_lock: Mapped[bool] = mapped_column(Boolean, default=False)  # C
    has_retractable_handle: Mapped[bool] = mapped_column(Boolean, default=False)  # H
    has_closing_straps: Mapped[bool] = mapped_column(Boolean, default=False)  # S
    has_wheels: Mapped[bool] = mapped_column(Boolean, default=False)  # W

    notes: Mapped[str | None] = mapped_column(Text)
    public_token: Mapped[str | None] = mapped_column(
        String(12), unique=True, nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="bags")  # type: ignore[name-defined]  # noqa: F821
    images: Mapped[list["BagImage"]] = relationship(
        "BagImage",
        back_populates="bag",
        cascade="all, delete-orphan",
        order_by="BagImage.uploaded_at",
    )
    trip_bags: Mapped[list["TripBag"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TripBag", back_populates="bag", passive_deletes=True
    )
    updates: Mapped[list["BagUpdate"]] = relationship(
        "BagUpdate",
        back_populates="bag",
        cascade="all, delete-orphan",
        order_by="BagUpdate.created_at.desc()",
    )

    @property
    def iata_code(self) -> str | None:
        if not self.color or not self.bag_type:
            return None
        code = self.color + self.bag_type
        if self.material:
            code += self.material
        if self.is_cabin_size:
            code += "K"
        external = ""
        if self.has_combination_lock:
            external += "C"
        if self.has_retractable_handle:
            external += "H"
        if self.has_closing_straps:
            external += "S"
        if self.has_wheels:
            external += "W"
        code += external or "X"
        return code

    @property
    def primary_image(self) -> "BagImage | None":
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None


class BagImage(Base):
    __tablename__ = "bag_image"

    id: Mapped[int] = mapped_column(primary_key=True)
    bag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bag.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    bag: Mapped["Bag"] = relationship("Bag", back_populates="images")


class BagUpdate(Base):
    __tablename__ = "bag_update"

    id: Mapped[int] = mapped_column(primary_key=True)
    bag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bag.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    bag: Mapped["Bag"] = relationship("Bag", back_populates="updates")
