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
    bag_type: Mapped[str | None] = mapped_column(String(50))
    color_primary: Mapped[str | None] = mapped_column(String(50))
    color_secondary: Mapped[str | None] = mapped_column(String(50))
    material: Mapped[str | None] = mapped_column(String(50))
    handle_type: Mapped[str | None] = mapped_column(String(50))
    wheel_type: Mapped[str | None] = mapped_column(String(50))
    size_category: Mapped[str | None] = mapped_column(String(50))
    closing_mechanism: Mapped[str | None] = mapped_column(String(50))
    lock_type: Mapped[str | None] = mapped_column(String(50))
    has_straps: Mapped[bool] = mapped_column(Boolean, default=False)
    strap_color: Mapped[str | None] = mapped_column(String(50))
    has_ribbons: Mapped[bool] = mapped_column(Boolean, default=False)
    ribbon_description: Mapped[str | None] = mapped_column(String(200))
    has_name_tag: Mapped[bool] = mapped_column(Boolean, default=False)
    external_pockets: Mapped[int | None] = mapped_column(Integer)
    distinguishing_marks: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

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
    trip_bags: Mapped[list["TripBag"]] = relationship("TripBag", back_populates="bag")  # type: ignore[name-defined]  # noqa: F821

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
