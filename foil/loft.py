# File: foil/loft.py
"""
Lofting and trimming utilities using FreeCAD Part.
"""
import Part
from typing import List


def loft_faces(faces: List[Part.Face], solid: bool = True) -> Part.Shape:
    """
    Loft a series of faces into a surface or solid.

    :param faces: list of Part.Face sections
    :param solid: if True, build a solid, else a shell
    :return: lofted Part.Shape
    """
    return Part.makeLoft(faces, solid)


def cut_solid(solid: Part.Shape, cutter: Part.Shape) -> Part.Shape:
    """
    Perform boolean cut between solid and cutter shape.

    :param solid: the main Part.Shape (solid)
    :param cutter: the cutting Part.Shape
    :return: new Part.Shape after subtraction
    """
    return solid.cut(cutter)
