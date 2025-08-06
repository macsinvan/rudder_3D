"""
outline/stock/stock2d.py
Draw 2D stock profiles in FreeCAD document.
"""

from FreeCAD import Vector
import Part
import csv
import os

def load_stock_csv():
    """
    Load stock dimensions from stock_sample.csv located in the same directory.

    Returns:
        tuple: (length, diameter)
    """
    csv_path = os.path.join(os.path.dirname(__file__), 'stock_sample.csv')
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            length = float(row['length'])
            diameter = float(row['diameter'])
            return length, diameter

def draw_simple_stock_2d(length: float, diameter: float, center=Vector(0, 0, 0)):
    """
    Draws a filled 2D circle representing the rudder stock.

    Args:
        length (float): (Not used in 2D, but kept for compatibility.)
        diameter (float): Diameter of the circle.
        center (Vector): Center position of the circle.

    Returns:
        Part.Shape: A filled face shape that can be extruded.
    """
    radius = diameter / 2
    circle_edge = Part.makeCircle(radius, center)
    circle_wire = Part.Wire([circle_edge])
    circle_face = Part.Face(circle_wire)
    return circle_face

def extrude_stock_3d(circle: Part.Shape, length: float) -> Part.Shape:
    """
    Extrudes the given 2D circle shape into a 3D cylinder.

    Args:
    circle_edge = Part.makeCircle(radius, center)
    circle_face = Part.Face(circle_edge)
    return circle_face

    Returns:
        Part.Shape: The 3D extruded solid.
    """
    vec = Vector(0, 0, length)
    return circle.extrude(vec)