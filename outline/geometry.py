"""
outline/geometry.py
Geometry utilities for outline processing.
"""
from typing import List, Tuple


def close_loop(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Ensure the list of points forms a closed loop by appending the first point
    at the end if it isn’t already closed.

    :param points: List of (x, z) points defining a polyline
    :return: New list where first == last
    """
    if not points:
        return []
    if points[0] == points[-1]:
        return points.copy()
    return points + [points[0]]


def slice_chords(points: List[Tuple[float, float]], z_levels: List[float]) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Generate chord line segment endpoints by intersecting the outline polyline
    (sequence of (x,z) points, assumed closed) with horizontal lines at each z in z_levels.

    :param points: closed polyline as list of (x,z) tuples
    :param z_levels: list of Z values where chords are desired
    :return: list of ((x1,z),(x2,z)) for each intersection with exactly two crossing points
    """
    chords: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    # Ensure loop is closed
    loop = close_loop(points)
    for z in z_levels:
        intersects: List[Tuple[float, float]] = []
        for i in range(len(loop) - 1):
            x1, z1 = loop[i]
            x2, z2 = loop[i+1]
            # Check if segment crosses horizontal line at z (exclusive of endpoints)
            if (z1 - z) * (z2 - z) < 0:
                t = (z - z1) / (z2 - z1)
                x = x1 + t * (x2 - x1)
                intersects.append((x, z))
        if len(intersects) == 2:
            chords.append((intersects[0], intersects[1]))
    return chords
