from enum import StrEnum


class ItemCategory(StrEnum):
    CLOTHING = "clothing"
    FOOTWEAR = "footwear"
    TOILETRIES = "toiletries"
    ELECTRONICS = "electronics"
    DOCUMENTS = "documents"
    MEDICATIONS = "medications"
    ACCESSORIES = "accessories"
    ENTERTAINMENT = "entertainment"
    FOOD_DRINK = "food_drink"
    OTHER = "other"


CATEGORY_LABELS: dict[str, str] = {
    "clothing": "Clothing",
    "footwear": "Footwear",
    "toiletries": "Toiletries",
    "electronics": "Electronics",
    "documents": "Documents & Travel",
    "medications": "Health & Medications",
    "accessories": "Accessories",
    "entertainment": "Entertainment",
    "food_drink": "Food & Drink",
    "other": "Other",
}

CATEGORY_ICONS: dict[str, str] = {
    "clothing": "bi-shirt",
    "footwear": "bi-boot",
    "toiletries": "bi-droplet",
    "electronics": "bi-phone",
    "documents": "bi-passport",
    "medications": "bi-capsule",
    "accessories": "bi-bag",
    "entertainment": "bi-headphones",
    "food_drink": "bi-cup-straw",
    "other": "bi-three-dots",
}
