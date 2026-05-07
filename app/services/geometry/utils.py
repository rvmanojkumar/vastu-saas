def calculate_center_from_coords(coords):
    """
    coords = [{x: , y: }, ...] OR [(x,y), ...]
    """

    if not coords:
        return None

    if isinstance(coords[0], dict):
        xs = [p["x"] for p in coords]
        ys = [p["y"] for p in coords]
    else:
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]

    return (sum(xs) / len(xs), sum(ys) / len(ys))