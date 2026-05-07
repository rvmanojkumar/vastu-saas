import math

# =========================
# DIRECTION CONSTANTS
# =========================

DIRECTIONS_16 = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW"
]

DIRECTIONS_32 = [
    "N", "NbE", "NNE", "NEbN",
    "NE", "NEbE", "ENE", "EbN",
    "E", "EbS", "ESE", "SEbE",
    "SE", "SEbS", "SSE", "SbE",
    "S", "SbW", "SSW", "SWbS",
    "SW", "SWbW", "WSW", "WbS",
    "W", "WbN", "WNW", "NWbW",
    "NW", "NWbN", "NNW", "NbW"
]

# =========================
# CENTROID
# =========================

def polygon_centroid(points):
    area = 0
    cx = 0
    cy = 0
    n = len(points)

    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]

        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross

    area *= 0.5

    if area == 0:
        return None

    cx /= (6 * area)
    cy /= (6 * area)

    return (cx, cy)

# =========================
# ANGLE
# =========================

def calculate_angle(center, point):
    dx = point[0] - center[0]
    dy = center[1] - point[1]  # screen coordinate fix

    angle = math.degrees(math.atan2(dy, dx))
    return (angle + 360) % 360

# =========================
# ROTATION
# =========================

def apply_rotation(angle, starting_degree):
    return (angle - starting_degree) % 360

# =========================
# DIRECTION MAPPING
# =========================

def get_direction_16(angle):
    sector_size = 360 / 16
    index = int(angle // sector_size)
    return DIRECTIONS_16[index]


def get_direction_32(angle):
    sector_size = 360 / 32
    index = int(angle // sector_size)
    return DIRECTIONS_32[index]

# =========================
# BRAHMASTHAN
# =========================

def is_brahmasthan(center, point, tolerance=20):
    """
    tolerance = pixel distance from center
    """
    dx = abs(point[0] - center[0])
    dy = abs(point[1] - center[1])

    return dx < tolerance and dy < tolerance

# =========================
# MAIN ENGINE
# =========================

def analyze_point(polygon_points, point, starting_degree=0):
    """
    polygon_points: [(x,y), ...]
    point: (x,y)
    """

    center = polygon_centroid(polygon_points)

    if not center:
        return {"error": "Invalid polygon"}

    # Brahmasthan check
    if is_brahmasthan(center, point):
        return {
            "zone": "Brahmasthan",
            "direction_16": None,
            "direction_32": None,
            "center": center
        }

    angle = calculate_angle(center, point)
    adjusted = apply_rotation(angle, starting_degree)

    return {
        "zone": "Directional",
        "direction_16": get_direction_16(adjusted),
        "direction_32": get_direction_32(adjusted),
        "angle": round(adjusted, 2),
        "center": center
    }