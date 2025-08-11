# stock/cylinder.py

import Part
from FreeCAD import Vector
from typing import Dict, Any, List, Tuple

__all__ = ["build_cylinder"]


def build_cylinder(row_dict: Dict[str, Any]) -> Tuple[List[Part.Shape], str]:
    """
    Move-only refactor of the 'cylinder' branch from stock/stock2d.py.
    Behavior is IDENTICAL to the original inline code:
      - Builds a straight cylinder between CSV 'start' and 'end'
      - Uses 'diameter_start' for the radius (as before)
      - Prints the same debug line
      - Returns ([shape], summary)
    """
    label = row_dict.get('label', '')

    z0 = -float(row_dict['start'])
    z1 = -float(row_dict['end'])
    base_z = min(z0, z1)
    height = abs(z1 - z0)
    d = float(row_dict['diameter_start'])

    cyl = Part.makeCylinder(d / 2.0, height, Vector(0, 0, base_z))

    summary = f"Cylinder '{label}' h={height} d={d}"
    print(f"  ✓ Cylinder: label='{label}', d={d}, z0={z0}, z1={z1}, base={base_z}, h={height}")

    return [cyl], summary