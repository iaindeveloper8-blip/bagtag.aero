from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Trip(Base):
    __tablename__ = "trip"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    trip_type: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    departure_date: Mapped[date | None] = mapped_column(Date)
    return_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="trips")  # type: ignore[name-defined]  # noqa: F821
    flights: Mapped[list["Flight"]] = relationship(
        "Flight",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="Flight.departure_at",
    )
    trip_bags: Mapped[list["TripBag"]] = relationship(
        "TripBag", back_populates="trip", cascade="all, delete-orphan"
    )
    packing_list: Mapped["PackingList | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "PackingList", back_populates="trip", cascade="all, delete-orphan", uselist=False
    )


class Flight(Base):
    __tablename__ = "flight"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trip.id", ondelete="CASCADE"), nullable=False, index=True
    )
    flight_number: Mapped[str | None] = mapped_column(String(20))
    airline: Mapped[str | None] = mapped_column(String(100))
    departure_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    arrival_airport: Mapped[str] = mapped_column(String(10), nullable=False)
    departure_at: Mapped[datetime | None] = mapped_column(DateTime)
    arrival_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_return: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    trip: Mapped["Trip"] = relationship("Trip", back_populates="flights")


class TripBag(Base):
    __tablename__ = "trip_bag"

    trip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trip.id", ondelete="CASCADE"), primary_key=True
    )
    bag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bag.id", ondelete="CASCADE"), primary_key=True
    )

    trip: Mapped["Trip"] = relationship("Trip", back_populates="trip_bags")
    bag: Mapped["Bag"] = relationship("Bag", back_populates="trip_bags")  # type: ignore[name-defined]  # noqa: F821
