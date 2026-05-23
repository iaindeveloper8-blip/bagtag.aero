from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.bags import service as bag_service
from src.bags.models import Bag
from src.database import get_db


async def valid_bag(
    bag_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Bag:
    return await bag_service.get_bag(db, bag_id, user.id)


OwnedBag = Annotated[Bag, Depends(valid_bag)]
