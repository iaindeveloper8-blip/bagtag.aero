from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.packing.exceptions import (
    CannotEditDefaultTemplate,
    PackingListItemNotFound,
    PackingListNotFound,
    TemplateItemNotFound,
    TemplateNotFound,
)
from src.packing.models import (
    PackingList,
    PackingListItem,
    PackingTemplate,
    PackingTemplateItem,
)
from src.packing.schemas import (
    PackingListItemCreate,
    PackingTemplateCreate,
    PackingTemplateItemCreate,
    PackingTemplateUpdate,
)


async def get_templates(db: AsyncSession, user_id: int) -> list[PackingTemplate]:
    result = await db.execute(
        select(PackingTemplate)
        .where(
            (PackingTemplate.is_default == True)  # noqa: E712
            | (PackingTemplate.user_id == user_id)
        )
        .options(selectinload(PackingTemplate.items))
        .order_by(PackingTemplate.is_default.desc(), PackingTemplate.name)
    )
    return list(result.scalars().all())


async def get_template(db: AsyncSession, template_id: int) -> PackingTemplate:
    result = await db.execute(
        select(PackingTemplate)
        .where(PackingTemplate.id == template_id)
        .options(selectinload(PackingTemplate.items))
    )
    template = result.scalar_one_or_none()
    if not template:
        raise TemplateNotFound()
    return template


async def create_template(
    db: AsyncSession, user_id: int, data: PackingTemplateCreate
) -> PackingTemplate:
    template = PackingTemplate(user_id=user_id, is_default=False, **data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(
    db: AsyncSession, template: PackingTemplate, data: PackingTemplateUpdate
) -> PackingTemplate:
    if template.is_default:
        raise CannotEditDefaultTemplate()
    for field, value in data.model_dump().items():
        setattr(template, field, value)
    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(db: AsyncSession, template: PackingTemplate) -> None:
    if template.is_default:
        raise CannotEditDefaultTemplate()
    await db.delete(template)
    await db.commit()


async def add_template_item(
    db: AsyncSession, template: PackingTemplate, data: PackingTemplateItemCreate
) -> PackingTemplateItem:
    if template.is_default:
        raise CannotEditDefaultTemplate()
    item = PackingTemplateItem(template_id=template.id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_template_item(db: AsyncSession, template: PackingTemplate, item_id: int) -> None:
    if template.is_default:
        raise CannotEditDefaultTemplate()
    item = next((i for i in template.items if i.id == item_id), None)
    if not item:
        raise TemplateItemNotFound()
    await db.delete(item)
    await db.commit()


async def clone_template(
    db: AsyncSession, template: PackingTemplate, user_id: int
) -> PackingTemplate:
    cloned = PackingTemplate(
        user_id=user_id,
        name=f"{template.name} (copy)",
        trip_type=template.trip_type,
        description=template.description,
        is_default=False,
    )
    db.add(cloned)
    await db.flush()
    for item in template.items:
        cloned_item = PackingTemplateItem(
            template_id=cloned.id,
            name=item.name,
            category=item.category,
            quantity=item.quantity,
            notes=item.notes,
            affiliate_url=item.affiliate_url,
        )
        db.add(cloned_item)
    await db.commit()
    await db.refresh(cloned)
    return cloned


async def get_packing_list(db: AsyncSession, trip_id: int) -> PackingList:
    result = await db.execute(
        select(PackingList)
        .where(PackingList.trip_id == trip_id)
        .options(selectinload(PackingList.items).selectinload(PackingListItem.bag))
        .execution_options(populate_existing=True)
    )
    pl = result.scalar_one_or_none()
    if not pl:
        raise PackingListNotFound()
    return pl


async def add_list_item(
    db: AsyncSession, packing_list: PackingList, data: PackingListItemCreate
) -> PackingListItem:
    item = PackingListItem(packing_list_id=packing_list.id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_list_item(
    db: AsyncSession,
    packing_list: PackingList,
    item_id: int,
    data: PackingListItemCreate,
) -> PackingListItem:
    item = next((i for i in packing_list.items if i.id == item_id), None)
    if not item:
        raise PackingListItemNotFound()
    item.name = data.name
    item.category = data.category
    item.quantity = data.quantity
    item.notes = data.notes
    item.bag_id = data.bag_id
    await db.commit()
    await db.refresh(item)
    return item


async def toggle_item_packed(
    db: AsyncSession, packing_list: PackingList, item_id: int
) -> PackingListItem:
    item = next((i for i in packing_list.items if i.id == item_id), None)
    if not item:
        raise PackingListItemNotFound()
    item.is_packed = not item.is_packed
    await db.commit()
    await db.refresh(item)
    return item


async def delete_list_item(db: AsyncSession, packing_list: PackingList, item_id: int) -> None:
    item = next((i for i in packing_list.items if i.id == item_id), None)
    if not item:
        raise PackingListItemNotFound()
    await db.delete(item)
    await db.commit()


async def clone_template_to_list(
    db: AsyncSession, template: PackingTemplate, packing_list: PackingList
) -> list[PackingListItem]:
    new_items = []
    for titem in template.items:
        item = PackingListItem(
            packing_list_id=packing_list.id,
            name=titem.name,
            category=titem.category,
            quantity=titem.quantity,
            notes=titem.notes,
            affiliate_url=titem.affiliate_url,
        )
        db.add(item)
        new_items.append(item)
    await db.commit()
    return new_items
