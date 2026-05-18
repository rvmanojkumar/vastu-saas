DIRECTION_MAP = {
    "n": "N",
    "north": "N",

    "ne": "NE",
    "north-east": "NE",
    "northeast": "NE",

    "e": "E",
    "east": "E",

    "se": "SE",
    "south-east": "SE",
    "southeast": "SE",

    "s": "S",
    "south": "S",

    "sw": "SW",
    "south-west": "SW",
    "southwest": "SW",

    "w": "W",
    "west": "W",

    "nw": "NW",
    "north-west": "NW",
    "northwest": "NW",

    "center": "CENTER",
    "c": "CENTER"
}


def normalize_direction(direction: str) -> str:
    if not direction:
        return ""

    key = direction.strip().lower()
    return DIRECTION_MAP.get(key, direction.upper())