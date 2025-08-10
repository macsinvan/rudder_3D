import FreeCAD as App
import Part
from FreeCAD import Vector

__all__ = ["make_wedge_debug_block"]

def make_wedge_debug_block(start: float, width: float, length_out: float, plate_thickness: float) -> Part.Shape:
    """
    Simple rectangular block to validate tine Z placement.

    - Visible thickness across Y = 2 * plate_thickness
    - Placement along Z uses -(start + width)
    """
    box = Part.makeBox(length_out, 2.0 * plate_thickness, width)
    box.Placement.Base = Vector(0.0, -plate_thickness, -(start + width))
    return box
