from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
    checkins: Mapped[list["TripCheckin"]] = relationship(
        "TripCheckin",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripCheckin.created_at.desc()",
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
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    rerouted_from_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("flight.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    trip: Mapped["Trip"] = relationship("Trip", back_populates="flights")
    reroutings: Mapped[list["Flight"]] = relationship(
        "Flight",
        back_populates="rerouted_from",
        foreign_keys=[rerouted_from_id],
    )
    rerouted_from: Mapped["Flight | None"] = relationship(
        "Flight",
        back_populates="reroutings",
        foreign_keys=[rerouted_from_id],
        remote_side=[id],
    )


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


class TripCheckin(Base):
    __tablename__ = "trip_checkin"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trip.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    trip: Mapped["Trip"] = relationship("Trip", back_populates="checkins")
    bag_checkins: Mapped[list["TripCheckinBag"]] = relationship(
        "TripCheckinBag", back_populates="checkin", cascade="all, delete-orphan"
    )


class TripCheckinBag(Base):
    __tablename__ = "trip_checkin_bag"
    __table_args__ = (UniqueConstraint("checkin_id", "bag_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    checkin_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trip_checkin.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bag.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "carry_on" | "checked_in"
    licence_plate_number: Mapped[str | None] = mapped_column(String(10))
    weight_kg: Mapped[float | None] = mapped_column(Float)
    receipt_filename: Mapped[str | None] = mapped_column(String(200))
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime)

    checkin: Mapped["TripCheckin"] = relationship("TripCheckin", back_populates="bag_checkins")
    bag: Mapped["Bag"] = relationship("Bag")  # type: ignore[name-defined]  # noqa: F821
