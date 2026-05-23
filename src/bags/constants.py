from enum import StrEnum


class BagType(StrEnum):
    SUITCASE = "suitcase"
    BACKPACK = "backpack"
    DUFFEL = "duffel"
    GARMENT_BAG = "garment_bag"
    BRIEFCASE = "briefcase"
    TOTE = "tote"
    OTHER = "other"


class BagMaterial(StrEnum):
    HARD_ABS = "hard_abs"
    HARD_POLYCARBONATE = "hard_polycarbonate"
    HARD_ALUMINUM = "hard_aluminum"
    SOFT_NYLON = "soft_nylon"
    SOFT_POLYESTER = "soft_polyester"
    CANVAS = "canvas"
    LEATHER = "leather"
    OTHER = "other"


class HandleType(StrEnum):
    TOP_ONLY = "top_only"
    SIDE_ONLY = "side_only"
    TOP_AND_SIDE = "top_and_side"
    RETRACTABLE = "retractable"
    RETRACTABLE_AND_SIDE = "retractable_and_side"
    NONE = "none"


class WheelType(StrEnum):
    NONE = "none"
    TWO_WHEEL = "two_wheel"
    FOUR_WHEEL_SPINNER = "four_wheel_spinner"


class SizeCategory(StrEnum):
    PERSONAL_ITEM = "personal_item"
    CARRY_ON = "carry_on"
    CABIN_MAX = "cabin_max"
    CHECKED_SMALL = "checked_small"
    CHECKED_MEDIUM = "checked_medium"
    CHECKED_LARGE = "checked_large"
    OVERSIZED = "oversized"


class ClosingMechanism(StrEnum):
    ZIPPER_SINGLE = "zipper_single"
    ZIPPER_DOUBLE = "zipper_double"
    CLIPS_LATCHES = "clips_latches"
    COMBINATION = "combination"


class LockType(StrEnum):
    NONE = "none"
    KEY = "key"
    COMBINATION = "combination"
    TSA_KEY = "tsa_key"
    TSA_COMBINATION = "tsa_combination"


LABEL_MAP: dict[str, str] = {
    # BagType
    "suitcase": "Suitcase",
    "backpack": "Backpack",
    "duffel": "Duffel Bag",
    "garment_bag": "Garment Bag",
    "briefcase": "Briefcase",
    "tote": "Tote",
    # BagMaterial
    "hard_abs": "Hard Shell (ABS)",
    "hard_polycarbonate": "Hard Shell (Polycarbonate)",
    "hard_aluminum": "Hard Shell (Aluminium)",
    "soft_nylon": "Soft (Nylon)",
    "soft_polyester": "Soft (Polyester)",
    "canvas": "Canvas",
    "leather": "Leather",
    # HandleType
    "top_only": "Top handle only",
    "side_only": "Side handle only",
    "top_and_side": "Top & side handles",
    "retractable": "Retractable / telescoping",
    "retractable_and_side": "Retractable + side handle",
    # WheelType
    "two_wheel": "2-wheel",
    "four_wheel_spinner": "4-wheel spinner",
    # SizeCategory
    "personal_item": "Personal item",
    "carry_on": "Carry-on",
    "cabin_max": "Cabin max",
    "checked_small": "Checked — small",
    "checked_medium": "Checked — medium",
    "checked_large": "Checked — large",
    "oversized": "Oversized",
    # ClosingMechanism
    "zipper_single": "Single zipper",
    "zipper_double": "Double zipper",
    "clips_latches": "Clips / latches",
    "combination": "Combination",
    # LockType
    "tsa_key": "TSA key lock",
    "tsa_combination": "TSA combination lock",
    # Shared
    "none": "None",
    "other": "Other",
}
