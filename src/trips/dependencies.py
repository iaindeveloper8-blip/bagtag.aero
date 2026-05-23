from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.database import get_db
from src.trips import service as trip_service
from src.trips.models import Trip


async def valid_trip(
    trip_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Trip:
    return await trip_service.get_trip(db, trip_id, user.id)


OwnedTrip = Annotated[Trip, Depends(valid_trip)]
