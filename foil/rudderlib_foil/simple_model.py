"""
Create a simple 3D box for testing.
"""
import Part
from FreeCAD import Vector

def create_test_box(length: float, width: float, height: float):
    """
    Return a Part box solid with the given dimensions.
    """
    return Part.makeBox(length, width, height)
