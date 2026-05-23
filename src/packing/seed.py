"""Seed default packing list templates. Idempotent — safe to run on every startup."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.packing.models import PackingTemplate, PackingTemplateItem

_AFFILIATE_TAG = "bagtagaero-20"


def _amz(asin: str) -> str:
    return f"https://www.amazon.com/dp/{asin}?tag={_AFFILIATE_TAG}"


_DEFAULT_TEMPLATES: list[dict] = [
    {
        "name": "Weekend Getaway",
        "trip_type": "weekend",
        "description": "Everything you need for a 2–3 night break.",
        "items": [
            {
                "name": "Casual T-shirts (×3)",
                "category": "clothing",
                "qty": 1,
                "asin": "B07NFSZG97",
            },
            {"name": "Jeans / trousers", "category": "clothing", "qty": 1, "asin": "B084CXRCNH"},
            {"name": "Underwear (×3)", "category": "clothing", "qty": 1, "asin": "B07CZMKG6S"},
            {"name": "Socks (×3 pairs)", "category": "clothing", "qty": 1, "asin": "B00LFEFSAG"},
            {
                "name": "Light jacket / hoodie",
                "category": "clothing",
                "qty": 1,
                "asin": "B08PWHBZCT",
            },
            {"name": "Comfortable shoes", "category": "footwear", "qty": 1, "asin": "B07D24JFMK"},
            {
                "name": "Flip-flops / sandals",
                "category": "footwear",
                "qty": 1,
                "asin": "B01N4G3LLG",
            },
            {
                "name": "Toothbrush & toothpaste",
                "category": "toiletries",
                "qty": 1,
                "asin": "B08BVVXM3N",
            },
            {"name": "Deodorant", "category": "toiletries", "qty": 1, "asin": "B09FTXHFCK"},
            {
                "name": "Travel shampoo & conditioner",
                "category": "toiletries",
                "qty": 1,
                "asin": "B08KGY9W4T",
            },
            {
                "name": "Phone charger & cable",
                "category": "electronics",
                "qty": 1,
                "asin": "B09M7Z6ZLV",
            },
            {
                "name": "Portable power bank",
                "category": "electronics",
                "qty": 1,
                "asin": "B09KLB9J5Y",
            },
            {"name": "Passport / ID", "category": "documents", "qty": 1, "asin": None},
            {"name": "Travel wallet", "category": "documents", "qty": 1, "asin": "B08N38J5MJ"},
            {"name": "Sunglasses", "category": "accessories", "qty": 1, "asin": "B0BHJMZN4L"},
        ],
    },
    {
        "name": "Business Trip",
        "trip_type": "business",
        "description": "Polished essentials for a 3–5 day work trip.",
        "items": [
            {"name": "Dress shirts (×3)", "category": "clothing", "qty": 1, "asin": "B07HDB8QNR"},
            {"name": "Suit jacket", "category": "clothing", "qty": 1, "asin": "B08G1NMY3K"},
            {"name": "Dress trousers (×2)", "category": "clothing", "qty": 1, "asin": "B07WKTNFPZ"},
            {"name": "Ties (×2)", "category": "accessories", "qty": 1, "asin": "B0884ZZDKL"},
            {"name": "Underwear (×5)", "category": "clothing", "qty": 1, "asin": "B07CZMKG6S"},
            {"name": "Socks (×5 pairs)", "category": "clothing", "qty": 1, "asin": "B00LFEFSAG"},
            {"name": "Dress shoes", "category": "footwear", "qty": 1, "asin": "B07HX16YBK"},
            {"name": "Casual shoes", "category": "footwear", "qty": 1, "asin": "B07D24JFMK"},
            {"name": "Laptop & charger", "category": "electronics", "qty": 1, "asin": "B09V3KXJPB"},
            {
                "name": "Laptop bag / sleeve",
                "category": "electronics",
                "qty": 1,
                "asin": "B07YMXKNDQ",
            },
            {
                "name": "Universal travel adapter",
                "category": "electronics",
                "qty": 1,
                "asin": "B07PGT7SQG",
            },
            {
                "name": "Noise-cancelling headphones",
                "category": "electronics",
                "qty": 1,
                "asin": "B0CH2NZF8T",
            },
            {"name": "Business cards", "category": "documents", "qty": 1, "asin": None},
            {"name": "Passport / ID", "category": "documents", "qty": 1, "asin": None},
            {"name": "Grooming kit", "category": "toiletries", "qty": 1, "asin": "B07X6DWG8F"},
            {
                "name": "Toothbrush & toothpaste",
                "category": "toiletries",
                "qty": 1,
                "asin": "B08BVVXM3N",
            },
            {"name": "Notebook & pen", "category": "accessories", "qty": 1, "asin": "B06ZXWX7X8"},
        ],
    },
    {
        "name": "Beach Holiday",
        "trip_type": "beach",
        "description": "Sun, sea, and sand — covered for 7–10 days.",
        "items": [
            {"name": "Swimwear (×2)", "category": "clothing", "qty": 1, "asin": "B08P4ZG2QK"},
            {
                "name": "Beach cover-up / sarong",
                "category": "clothing",
                "qty": 1,
                "asin": "B08NXWBZH7",
            },
            {
                "name": "Light summer dresses / shirts",
                "category": "clothing",
                "qty": 3,
                "asin": "B09KKNZX5F",
            },
            {"name": "Shorts (×3)", "category": "clothing", "qty": 1, "asin": "B09BZ3N2P7"},
            {"name": "Underwear (×7)", "category": "clothing", "qty": 1, "asin": "B07CZMKG6S"},
            {"name": "Socks (×3 pairs)", "category": "clothing", "qty": 1, "asin": "B00LFEFSAG"},
            {"name": "Flip-flops", "category": "footwear", "qty": 1, "asin": "B01N4G3LLG"},
            {"name": "Casual sandals", "category": "footwear", "qty": 1, "asin": "B091GRLPGZ"},
            {"name": "SPF 50 sunscreen", "category": "toiletries", "qty": 2, "asin": "B004QHZWWU"},
            {"name": "After-sun lotion", "category": "toiletries", "qty": 1, "asin": "B00WLNTK6E"},
            {"name": "Insect repellent", "category": "toiletries", "qty": 1, "asin": "B00BMLM4OO"},
            {
                "name": "Sunglasses (UV400)",
                "category": "accessories",
                "qty": 1,
                "asin": "B0BHJMZN4L",
            },
            {"name": "Sun hat", "category": "accessories", "qty": 1, "asin": "B00XXAYPKE"},
            {"name": "Beach bag", "category": "accessories", "qty": 1, "asin": "B07ZGM3YDL"},
            {
                "name": "Waterproof phone pouch",
                "category": "electronics",
                "qty": 1,
                "asin": "B07V9YBFV1",
            },
            {"name": "Passport / ID", "category": "documents", "qty": 1, "asin": None},
            {"name": "Travel insurance docs", "category": "documents", "qty": 1, "asin": None},
            {"name": "Antihistamines", "category": "medications", "qty": 1, "asin": "B004NO3MEM"},
            {
                "name": "Motion sickness tablets",
                "category": "medications",
                "qty": 1,
                "asin": "B000BN8F2E",
            },
        ],
    },
    {
        "name": "City Break",
        "trip_type": "city_break",
        "description": "Smart-casual essentials for 3–4 days of city exploration.",
        "items": [
            {
                "name": "Smart-casual tops (×4)",
                "category": "clothing",
                "qty": 1,
                "asin": "B09KKNZX5F",
            },
            {"name": "Jeans / chinos", "category": "clothing", "qty": 2, "asin": "B084CXRCNH"},
            {
                "name": "Light waterproof jacket",
                "category": "clothing",
                "qty": 1,
                "asin": "B08PWHBZCT",
            },
            {"name": "Underwear (×4)", "category": "clothing", "qty": 1, "asin": "B07CZMKG6S"},
            {"name": "Socks (×4 pairs)", "category": "clothing", "qty": 1, "asin": "B00LFEFSAG"},
            {
                "name": "Comfortable walking shoes",
                "category": "footwear",
                "qty": 1,
                "asin": "B07D24JFMK",
            },
            {"name": "Smart shoes / boots", "category": "footwear", "qty": 1, "asin": "B07HX16YBK"},
            {"name": "Day backpack", "category": "accessories", "qty": 1, "asin": "B077MXKN5M"},
            {"name": "Sunglasses", "category": "accessories", "qty": 1, "asin": "B0BHJMZN4L"},
            {
                "name": "Umbrella (compact)",
                "category": "accessories",
                "qty": 1,
                "asin": "B01MQJATUI",
            },
            {
                "name": "Travel toiletry bag",
                "category": "toiletries",
                "qty": 1,
                "asin": "B07NZB4VQ8",
            },
            {
                "name": "Phone charger & cable",
                "category": "electronics",
                "qty": 1,
                "asin": "B09M7Z6ZLV",
            },
            {
                "name": "Portable power bank",
                "category": "electronics",
                "qty": 1,
                "asin": "B09KLB9J5Y",
            },
            {"name": "Earphones", "category": "electronics", "qty": 1, "asin": "B09JQMJHXY"},
            {"name": "Passport / ID", "category": "documents", "qty": 1, "asin": None},
            {"name": "Travel card / cash", "category": "documents", "qty": 1, "asin": None},
            {
                "name": "Travel guide / maps",
                "category": "entertainment",
                "qty": 1,
                "asin": "B07RLTPCBN",
            },
        ],
    },
    {
        "name": "Hiking & Adventure",
        "trip_type": "hiking",
        "description": "Gear and essentials for 5–7 days on the trail.",
        "items": [
            {
                "name": "Moisture-wicking base layers (×3)",
                "category": "clothing",
                "qty": 1,
                "asin": "B08BQKNST7",
            },
            {
                "name": "Hiking trousers (×2)",
                "category": "clothing",
                "qty": 1,
                "asin": "B07WKTNFPZ",
            },
            {"name": "Fleece mid-layer", "category": "clothing", "qty": 1, "asin": "B09BXNBPTL"},
            {
                "name": "Waterproof outer shell jacket",
                "category": "clothing",
                "qty": 1,
                "asin": "B089VBKW3N",
            },
            {
                "name": "Merino wool socks (×5 pairs)",
                "category": "clothing",
                "qty": 1,
                "asin": "B01ARFPM5S",
            },
            {"name": "Thermal underwear", "category": "clothing", "qty": 1, "asin": "B00X2N2QG2"},
            {
                "name": "Hiking boots (waterproof)",
                "category": "footwear",
                "qty": 1,
                "asin": "B0796GKKVS",
            },
            {
                "name": "Camp sandals / shoes",
                "category": "footwear",
                "qty": 1,
                "asin": "B091GRLPGZ",
            },
            {"name": "Trekking poles", "category": "accessories", "qty": 1, "asin": "B07BW74X5W"},
            {
                "name": "Headlamp + spare batteries",
                "category": "electronics",
                "qty": 1,
                "asin": "B01NAACHH2",
            },
            {
                "name": "GPS device / watch",
                "category": "electronics",
                "qty": 1,
                "asin": "B09TVBQ39X",
            },
            {
                "name": "Portable water filter",
                "category": "accessories",
                "qty": 1,
                "asin": "B00B8Z3WT4",
            },
            {"name": "First aid kit", "category": "medications", "qty": 1, "asin": "B0756ZV9JX"},
            {"name": "Blister plasters", "category": "medications", "qty": 1, "asin": "B00JM3XFN6"},
            {"name": "Sunscreen SPF 50", "category": "toiletries", "qty": 1, "asin": "B004QHZWWU"},
            {
                "name": "Insect repellent (DEET)",
                "category": "toiletries",
                "qty": 1,
                "asin": "B00BMLM4OO",
            },
            {
                "name": "Biodegradable soap",
                "category": "toiletries",
                "qty": 1,
                "asin": "B00CEGGBS4",
            },
            {"name": "Passport / ID", "category": "documents", "qty": 1, "asin": None},
            {
                "name": "Trail map / guidebook",
                "category": "documents",
                "qty": 1,
                "asin": "B07RLTPCBN",
            },
            {
                "name": "Emergency whistle",
                "category": "accessories",
                "qty": 1,
                "asin": "B00H35CWRQ",
            },
        ],
    },
]


async def seed_default_templates(db: AsyncSession) -> None:
    result = await db.execute(
        select(PackingTemplate).where(PackingTemplate.is_default == True)  # noqa: E712
    )
    if result.scalars().first() is not None:
        return

    for tdata in _DEFAULT_TEMPLATES:
        tmpl = PackingTemplate(
            user_id=None,
            name=tdata["name"],
            trip_type=tdata["trip_type"],
            description=tdata["description"],
            is_default=True,
        )
        db.add(tmpl)
        await db.flush()

        for item in tdata["items"]:
            asin = item.get("asin")
            db.add(
                PackingTemplateItem(
                    template_id=tmpl.id,
                    name=item["name"],
                    category=item["category"],
                    quantity=item.get("qty", 1),
                    affiliate_url=_amz(asin) if asin else None,
                )
            )

    await db.commit()
