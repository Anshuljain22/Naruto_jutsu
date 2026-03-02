import math

def get_distance(p1, p2):
    """Calculate Euclidean distance between two 2D points (x, y)"""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def get_angle(p1, p2, p3):
    """
    Calculates the angle between three points (p1, p2, p3) with p2 as the vertex.
    Returns angle in degrees.
    """
    # Calculate lengths of sides
    a = get_distance(p2, p3)
    b = get_distance(p1, p2)
    c = get_distance(p1, p3)

    if a == 0 or b == 0:
        return 0

    # Law of Cosines
    try:
        val = (a**2 + b**2 - c**2) / (2 * a * b)
        # Handle float precision issues
        if val > 1.0: val = 1.0
        if val < -1.0: val = -1.0
        
        angle = math.degrees(math.acos(val))
        return angle
    except Exception:
        return 0
