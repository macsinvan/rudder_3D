"""
# File: outline/offset.py
Geometry utilities for offsetting 2D wires using FreeCAD Part.
"""
import Part


def offset_wire(wire: Part.Wire, distance: float) -> Part.Wire:
    """
    Offset the given 2D wire by the specified distance.

    :param wire: FreeCAD Part.Wire in the X-Z plane
    :param distance: offset distance (positive for outward, negative for inward)
    :return: a new Part.Wire offset by the distance
    """
    # FreeCAD's makeOffset2D works in the XY plane; the wire should lie in X-Z plane
    return wire.makeOffset2D(distance)
