"""
Compute NACA-4 foil thickness distribution (half-thickness).
"""

import math
from typing import List

def naca4_thickness(x: float, chord: float, t_pct: float) -> float:
    """
    NACA-4 max thickness location function.
    
    :param x: distance from leading edge [0..chord]
    :param chord: chord length
    :param t_pct: max thickness as % (e.g. 12.0 for NACA 0012)
    :return: half-thickness at x
    """
    # Clamp strictly at leading and trailing edges
    if x <= 0.0 or abs(x - chord) < 1e-8:
        return 0.0
    t = t_pct / 100.0
    xi = x / chord
    return 5 * t * chord * (
        0.2969 * math.sqrt(xi)
        - 0.1260 * xi
        - 0.3516 * xi**2
        + 0.2843 * xi**3
        - 0.1015 * xi**4
    )

def naca4_coordinates(chord: float, t_pct: float, num_pts: int = 50) -> List[tuple[float,float]]:
    """
    Generate full-foil coordinate list (upper, lower) for a zero camber NACA-00xx at discrete x.
    Returns list of (x, +yt) then (x, -yt).
    """
    pts = []
    for i in range(num_pts + 1):
        x = chord * 0.5 * (1 - math.cos(math.pi * i / num_pts))
        yt = naca4_thickness(x, chord, t_pct)
        pts.append((x, yt))
    for i in range(num_pts, -1, -1):
        x = chord * 0.5 * (1 - math.cos(math.pi * i / num_pts))
        yt = naca4_thickness(x, chord, t_pct)
        pts.append((x, -yt))
    return pts
