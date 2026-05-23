from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.database import get_db
from src.packing import service as packing_service
from src.packing.exceptions import TemplateNotFound
from src.packing.models import PackingTemplate


async def valid_template(
    template_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PackingTemplate:
    return await packing_service.get_template(db, template_id)


async def valid_owned_template(
    template_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PackingTemplate:
    template = await packing_service.get_template(db, template_id)
    if not template.is_default and template.user_id != user.id:
        raise TemplateNotFound()
    return template


AnyTemplate = Annotated[PackingTemplate, Depends(valid_template)]
OwnedTemplate = Annotated[PackingTemplate, Depends(valid_owned_template)]
