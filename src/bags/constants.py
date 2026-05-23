from enum import StrEnum


class BagColor(StrEnum):
    WHITE = "WT"
    BLACK = "BK"
    GREY = "GY"
    BLUE = "BU"
    PURPLE = "PU"
    RED = "RD"
    YELLOW = "YW"
    BEIGE = "BE"
    BROWN = "BN"
    GREEN = "GN"
    MULTI = "MC"
    PATTERN = "PR"


class BagType(StrEnum):
    # Without zippers (01–12)
    HORIZONTAL_HARD_SHELL = "01"
    UPRIGHT = "02"
    HORIZONTAL_NON_EXPANDABLE = "03"
    HORIZONTAL_EXPANDABLE = "05"
    BRIEFCASE = "06"
    DOCUMENT_CASE = "07"
    MILITARY = "08"
    PLASTIC_LAUNDRY = "09"
    BOX = "10"
    STORAGE_CONTAINER = "12"
    # With zippers (20–29)
    GARMENT_BAG = "20"
    UPRIGHT_SOFT = "22"
    HORIZONTAL_SUITCASE = "23"
    DUFFEL_SPORT = "25"
    LAPTOP_OVERNIGHT = "26"
    EXPANDABLE_UPRIGHT = "27"
    MATTED_WOVEN = "28"
    BACKPACK = "29"


class BagMaterial(StrEnum):
    """Material modifier letter; absent from the code means soft (IATA default)."""
    DUAL = "D"
    LEATHER = "L"
    METAL = "M"
    RIGID = "R"
    TWEED = "T"


LABEL_MAP: dict[str, str] = {
    # BagColor
    "WT": "White",
    "BK": "Black",
    "GY": "Grey",
    "BU": "Blue",
    "PU": "Purple",
    "RD": "Red",
    "YW": "Yellow",
    "BE": "Beige",
    "BN": "Brown",
    "GN": "Green",
    "MC": "Multi-Coloured",
    "PR": "Pattern",
    # BagType — without zippers
    "01": "Horizontal design hard shell",
    "02": "Upright design",
    "03": "Horizontal design suitcase (non-expandable)",
    "05": "Horizontal design suitcase (expandable)",
    "06": "Briefcase",
    "07": "Document case",
    "08": "Military style bag",
    "09": "Plastic / laundry bag",
    "10": "Box",
    "12": "Storage container",
    # BagType — with zippers
    "20": "Garment bag / suit carrier",
    "22": "Upright design (soft material)",
    "23": "Horizontal design suitcase",
    "25": "Duffel / sport bag",
    "26": "Laptop / overnight bag",
    "27": "Expandable upright",
    "28": "Matted woven bag",
    "29": "Backpack / rucksack",
    # BagMaterial
    "D": "Dual soft/hard",
    "L": "Leather",
    "M": "Metal",
    "R": "Rigid (hard shell)",
    "T": "Tweed",
}
