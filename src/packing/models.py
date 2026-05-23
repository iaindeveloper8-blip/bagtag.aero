from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class PackingTemplate(Base):
    __tablename__ = "packing_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    trip_type: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    user: Mapped["User | None"] = relationship("User", back_populates="packing_templates")  # type: ignore[name-defined]  # noqa: F821
    items: Mapped[list["PackingTemplateItem"]] = relationship(
        "PackingTemplateItem",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="PackingTemplateItem.category, PackingTemplateItem.name",
    )


class PackingTemplateItem(Base):
    __tablename__ = "packing_template_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("packing_template.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))
    affiliate_url: Mapped[str | None] = mapped_column(String(500))

    template: Mapped["PackingTemplate"] = relationship("PackingTemplate", back_populates="items")


class PackingList(Base):
    __tablename__ = "packing_list"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trip.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="Packing List")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    trip: Mapped["Trip"] = relationship("Trip", back_populates="packing_list")  # type: ignore[name-defined]  # noqa: F821
    items: Mapped[list["PackingListItem"]] = relationship(
        "PackingListItem",
        back_populates="packing_list",
        cascade="all, delete-orphan",
        order_by="PackingListItem.category, PackingListItem.name",
    )


class PackingListItem(Base):
    __tablename__ = "packing_list_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    packing_list_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("packing_list.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))
    is_packed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bag_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("bag.id", ondelete="SET NULL"))
    # Preserved from default template item — never set by user directly
    affiliate_url: Mapped[str | None] = mapped_column(String(500))

    packing_list: Mapped["PackingList"] = relationship("PackingList", back_populates="items")
    bag: Mapped["Bag | None"] = relationship("Bag")  # type: ignore[name-defined]  # noqa: F821
