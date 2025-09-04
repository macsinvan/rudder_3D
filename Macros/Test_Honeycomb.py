#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FreeCAD Macro: Honeycomb Perforated Plate
Creates a flat plate with honeycomb perforations using Draft Arrays
Version: 2.0 - Fixed honeycomb pattern geometry
"""

import FreeCAD
import FreeCADGui
import Part
import Draft
import math
from FreeCAD import Base, Vector

# Version tracking
MACRO_VERSION = "2.0"
print(f"=== Honeycomb Plate Macro v{MACRO_VERSION} ===")
print("Changes: Fixed honeycomb geometry, using make_ortho_array")

doc = FreeCAD.activeDocument()
if doc is None:
    doc = FreeCAD.newDocument()

# PARAMETERS - Edit these values
LENGTH_X = 400.0      # Plate length in X (mm)
WIDTH_Y = 100.0       # Plate width in Y (mm)  
THICKNESS_Z = 6.0     # Plate thickness in Z (mm)
HEX_RADIUS = 5.0      # Hexagon circumradius (mm)
WALL_THICKNESS = 2.0  # Wall between holes (mm)

print("\nCreating honeycomb perforated plate...")
print(f"Plate dimensions: {LENGTH_X} x {WIDTH_Y} x {THICKNESS_Z} mm")
print(f"Hexagon radius: {HEX_RADIUS} mm, Wall thickness: {WALL_THICKNESS} mm")

# Step 1: Create the base plate
plate = Part.makeBox(LENGTH_X, WIDTH_Y, THICKNESS_Z)
plate_obj = doc.addObject("Part::Feature", "BasePlate")
plate_obj.Shape = plate

# Step 2: Create a single hexagon cylinder
vertices = []
for i in range(6):
    angle = i * math.pi / 3.0
    x = HEX_RADIUS * math.cos(angle)
    y = HEX_RADIUS * math.sin(angle)
    vertices.append(Vector(x, y, 0))
vertices.append(vertices[0])  # Close polygon

hex_wire = Part.makePolygon(vertices)
hex_face = Part.Face(hex_wire)
hex_cylinder = hex_face.extrude(Vector(0, 0, THICKNESS_Z + 2))

# Step 3: Calculate proper honeycomb spacing
# For regular hexagon: width = radius * sqrt(3)
hex_width = HEX_RADIUS * math.sqrt(3)
hex_height = HEX_RADIUS * 2

# Honeycomb pattern spacing
x_spacing = hex_width + WALL_THICKNESS
# For honeycomb, vertical spacing between row centers is 1.5 * radius
y_spacing = HEX_RADIUS * 1.5 + WALL_THICKNESS

print(f"\nHexagon geometry:")
print(f"  Hex width: {hex_width:.2f} mm")
print(f"  X spacing: {x_spacing:.2f} mm")
print(f"  Y spacing: {y_spacing:.2f} mm")

# Calculate how many hexagons fit
margin = HEX_RADIUS + WALL_THICKNESS
n_x = int((LENGTH_X - 2 * margin) / x_spacing) + 1
n_y = int((WIDTH_Y - 2 * margin) / y_spacing) + 1

print(f"\nArray configuration:")
print(f"  Hexagons per row: {n_x}")
print(f"  Number of rows: {n_y}")
print(f"  Total hexagons: ~{n_x * n_y}")

# Step 4: Create arrays for even and odd rows
all_cutters = []

# Process each row individually for proper honeycomb pattern
for row in range(n_y):
    # Determine if this is an even or odd row
    is_odd_row = (row % 2 == 1)
    
    # Calculate base position for this row
    y_position = margin + row * y_spacing
    
    if is_odd_row:
        # Odd rows: offset by half spacing, may have one less hexagon
        x_start = margin + x_spacing / 2
        hexagons_in_row = n_x - 1 if (x_start + (n_x - 1) * x_spacing + HEX_RADIUS > LENGTH_X) else n_x
    else:
        # Even rows: start at normal position
        x_start = margin
        hexagons_in_row = n_x
    
    if hexagons_in_row <= 0:
        continue
        
    # Create hexagon for this row
    row_hex = doc.addObject("Part::Feature", f"HexRow{row}")
    row_cylinder = hex_cylinder.copy()
    row_cylinder.Placement.Base = Vector(x_start, y_position, -1)
    row_hex.Shape = row_cylinder
    
    # Create array for this row
    if hexagons_in_row > 1:
        row_array = Draft.make_ortho_array(
            row_hex,
            v_x=Vector(x_spacing, 0, 0),
            v_y=Vector(0, 0, 0),
            v_z=Vector(0, 0, 0),
            n_x=hexagons_in_row,
            n_y=1,
            n_z=1,
            use_link=False
        )
        row_array.Fuse = True
        all_cutters.append(row_array)
    else:
        all_cutters.append(row_hex)
    
    print(f"  Row {row}: {'Odd' if is_odd_row else 'Even'}, {hexagons_in_row} hexagons, X start: {x_start:.1f}")

doc.recompute()

# Step 5: Perform boolean cut
print("\nPerforming boolean cuts...")
result = plate

for i, cutter in enumerate(all_cutters):
    if hasattr(cutter, 'Shape'):
        try:
            result = result.cut(cutter.Shape)
            print(f"  Cut row {i} completed")
        except Exception as e:
            print(f"  Warning: Could not cut row {i}: {e}")

# Step 6: Create final object
final = doc.addObject("Part::Feature", "HoneycombPlate")
final.Shape = result

# Hide construction objects
plate_obj.ViewObject.Visibility = False
for cutter in all_cutters:
    if hasattr(cutter, 'ViewObject'):
        cutter.ViewObject.Visibility = False

# Set color
final.ViewObject.ShapeColor = (0.7, 0.7, 0.85)
final.ViewObject.DisplayMode = "Shaded"

doc.recompute()

# Fit view
FreeCADGui.ActiveDocument.ActiveView.fitAll()

print("\n=== Honeycomb plate created successfully! ===")
print(f"Macro version: {MACRO_VERSION}")
print(f"Final plate: {LENGTH_X} x {WIDTH_Y} x {THICKNESS_Z} mm")
print(f"Total rows processed: {len(all_cutters)}")