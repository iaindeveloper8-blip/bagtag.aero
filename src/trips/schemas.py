from datetime import date, datetime

from pydantic import BaseModel, Field

from src.trips.constants import TripType


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trip_type: TripType | None = None
    description: str | None = None
    departure_date: date | None = None
    return_date: date | None = None


class TripUpdate(TripCreate):
    pass


class FlightCreate(BaseModel):
    flight_number: str | None = Field(default=None, max_length=20)
    airline: str | None = Field(default=None, max_length=100)
    departure_airport: str = Field(min_length=3, max_length=10)
    arrival_airport: str = Field(min_length=3, max_length=10)
    departure_at: datetime | None = None
    arrival_at: datetime | None = None
    is_return: bool = False
    notes: str | None = None


class FlightUpdate(FlightCreate):
    pass
