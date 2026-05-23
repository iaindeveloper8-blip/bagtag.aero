import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fr24sdk import Client

from src.config import settings


@dataclass
class FlightInfo:
    departure_airport: str
    arrival_airport: str
    departure_at: datetime | None
    arrival_at: datetime | None
    airline: str | None


def _lookup_sync(flight_number: str, departure_date: date) -> FlightInfo:
    if not settings.FLIGHTRADAR24_API_KEY:
        raise RuntimeError("FLIGHTRADAR24_API_KEY is not configured")

    # API requires naive UTC datetimes in YYYY-MM-DDTHH:MM:SS format
    start = datetime(departure_date.year, departure_date.month, departure_date.day)
    end = start + timedelta(days=1)

    with Client(api_token=settings.FLIGHTRADAR24_API_KEY) as client:
        resp = client.flight_summary.get_full(
            flights=[flight_number.upper()],
            flight_datetime_from=start,
            flight_datetime_to=end,
            limit=1,
        )
        if not resp.data:
            raise ValueError(f"No flights found for {flight_number} on {departure_date}")

        f = resp.data[0]

        dep_iata = f.orig_iata
        arr_iata = f.dest_iata or f.dest_iata_actual
        if not dep_iata or not arr_iata:
            raise ValueError(f"Incomplete airport data returned for {flight_number}")

        def _parse_dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return None

        airline_name: str | None = None
        if f.operating_as:
            try:
                al = client.airlines.get_light(f.operating_as)
                airline_name = al.name
            except Exception:
                airline_name = f.operating_as

        return FlightInfo(
            departure_airport=dep_iata,
            arrival_airport=arr_iata,
            departure_at=_parse_dt(f.datetime_takeoff),
            arrival_at=_parse_dt(f.datetime_landed),
            airline=airline_name,
        )


async def lookup_flight(flight_number: str, departure_date: date) -> FlightInfo:
    return await asyncio.to_thread(_lookup_sync, flight_number, departure_date)
