from enum import StrEnum


class TripType(StrEnum):
    WEEKEND = "weekend"
    BUSINESS = "business"
    BEACH = "beach"
    CITY_BREAK = "city_break"
    HIKING = "hiking"
    LONG_HAUL = "long_haul"
    CRUISE = "cruise"
    OTHER = "other"


TRIP_TYPE_LABELS: dict[str, str] = {
    "weekend": "Weekend Getaway",
    "business": "Business Trip",
    "beach": "Beach Holiday",
    "city_break": "City Break",
    "hiking": "Hiking / Adventure",
    "long_haul": "Long-haul Holiday",
    "cruise": "Cruise",
    "other": "Other",
}
