#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
~/Rudder_Code/helpers/hex_array_helper.py
Honeycomb Array Helper Module
Pure geometry functions for creating honeycomb patterns
No FreeCAD document operations - just shape generation
"""

import Part
import math
from FreeCAD import Vector

# Module version
MODULE_VERSION = "1.0"

def create_honeycomb_geometry(length, width, thickness, hex_radius, wall_thickness):
    """
    Creates honeycomb perforated plate geometry (pure logic, no FreeCAD document operations)
    
    Parameters:
    -----------
    length : float
        Plate length in X direction (mm)
    width : float
        Plate width in Y direction (mm)
    thickness : float
        Plate thickness in Z direction (mm)
    hex_radius : float
        Circumradius of hexagon holes (mm)
    wall_thickness : float
        Minimum wall thickness between hexagons (mm)
    
    Returns:
    --------
    Part.Shape : The perforated plate shape
    dict : Information about the operation (holes created, rows, etc.)
    """
    print(f"\n=== Creating Honeycomb Geometry ===")
    print(f"Plate: {length} x {width} x {thickness} mm")
    print(f"Hex radius: {hex_radius} mm, Wall: {wall_thickness} mm")
    
    # Create base plate
    base_plate = Part.makeBox(length, width, thickness)
    
    # Create hexagon template
    vertices = []
    for i in range(6):
        angle = i * math.pi / 3.0
        x = hex_radius * math.cos(angle)
        y = hex_radius * math.sin(angle)
        vertices.append(Vector(x, y, 0))
    vertices.append(vertices[0])
    
    hex_wire = Part.makePolygon(vertices)
    hex_face = Part.Face(hex_wire)
    hex_template = hex_face.extrude(Vector(0, 0, thickness + 2))
    
    # Calculate honeycomb spacing
    hex_width = hex_radius * math.sqrt(3)
    x_spacing = hex_width + wall_thickness
    y_spacing = hex_radius * 1.5 + wall_thickness
    
    # Calculate array bounds
    margin = hex_radius + wall_thickness
    n_x = int((length - 2 * margin) / x_spacing) + 1
    n_y = int((width - 2 * margin) / y_spacing) + 1
    
    print(f"Array: {n_x} hexagons per row, {n_y} rows")
    
    # Create all hexagon cutters
    all_hexagons = []
    total_hexagons = 0
    
    for row in range(n_y):
        is_odd_row = (row % 2 == 1)
        y_position = margin + row * y_spacing
        
        if is_odd_row:
            x_start = margin + x_spacing / 2
            hexagons_in_row = n_x - 1 if (x_start + (n_x - 1) * x_spacing + hex_radius > length) else n_x
        else:
            x_start = margin
            hexagons_in_row = n_x
        
        if hexagons_in_row <= 0:
            continue
        
        # Create hexagons for this row
        for col in range(hexagons_in_row):
            hex_copy = hex_template.copy()
            x_position = x_start + col * x_spacing
            hex_copy.Placement.Base = Vector(x_position, y_position, -1)
            all_hexagons.append(hex_copy)
            total_hexagons += 1
    
    print(f"Total hexagons created: {total_hexagons}")
    
    # Perform boolean cuts
    print("Performing boolean operations...")
    result = base_plate
    
    # Combine all hexagons into one compound for faster cutting
    if all_hexagons:
        hex_compound = Part.makeCompound(all_hexagons)
        result = result.cut(hex_compound)
    
    # Prepare info dictionary
    info = {
        'module_version': MODULE_VERSION,
        'total_hexagons': total_hexagons,
        'rows': n_y,
        'hexagons_per_row': n_x,
        'x_spacing': x_spacing,
        'y_spacing': y_spacing,
        'hex_width': hex_width
    }
    
    return result, info


def create_honeycomb_structure(length, width, thickness, hex_radius, wall_thickness, base_fraction=0.1):
    """
    Creates honeycomb structure (solid hexagonal pillars with base plate) for use as boolean cutter
    
    Parameters:
    -----------
    length : float
        Structure length in X direction (mm)
    width : float
        Structure width in Y direction (mm)
    thickness : float
        Total thickness - pillars extend (1-base_fraction) of this height (mm)
    hex_radius : float
        Circumradius of hexagon pillars (mm)
    wall_thickness : float
        Gap between hexagon pillars (mm)
    base_fraction : float
        Fraction of thickness used for base plate (default 0.1 = 10%)
    
    Returns:
    --------
    Part.Shape : The honeycomb structure shape
    dict : Information about the structure
    """
    # Calculate base and pillar heights from thickness
    base_thickness = thickness * base_fraction
    pillar_height = thickness - base_thickness
    
    print(f"\n=== Creating Honeycomb Structure ===")
    print(f"Structure: {length} x {width} x {thickness} mm total")
    print(f"Hex radius: {hex_radius} mm, Gap: {wall_thickness} mm")
    print(f"Base plate: {base_thickness:.2f} mm, Pillars: {pillar_height:.2f} mm")
    
    # Create base plate to connect all pillars
    base_plate = Part.makeBox(length, width, base_thickness)
    
    # Create hexagon template for pillars
    vertices = []
    for i in range(6):
        angle = i * math.pi / 3.0
        x = hex_radius * math.cos(angle)
        y = hex_radius * math.sin(angle)
        vertices.append(Vector(x, y, 0))
    vertices.append(vertices[0])
    
    hex_wire = Part.makePolygon(vertices)
    hex_face = Part.Face(hex_wire)
    # Pillars start at base thickness and extend upward
    hex_pillar = hex_face.extrude(Vector(0, 0, pillar_height))
    
    # Calculate honeycomb spacing (same as perforated plate)
    hex_width = hex_radius * math.sqrt(3)
    x_spacing = hex_width + wall_thickness
    y_spacing = hex_radius * 1.5 + wall_thickness
    
    # Calculate array bounds
    margin = hex_radius + wall_thickness
    n_x = int((length - 2 * margin) / x_spacing) + 1
    n_y = int((width - 2 * margin) / y_spacing) + 1
    
    print(f"Array: {n_x} pillars per row, {n_y} rows")
    
    # Create all hexagon pillars
    all_pillars = []
    total_pillars = 0
    
    for row in range(n_y):
        is_odd_row = (row % 2 == 1)
        y_position = margin + row * y_spacing
        
        if is_odd_row:
            x_start = margin + x_spacing / 2
            pillars_in_row = n_x - 1 if (x_start + (n_x - 1) * x_spacing + hex_radius > length) else n_x
        else:
            x_start = margin
            pillars_in_row = n_x
        
        if pillars_in_row <= 0:
            continue
        
        # Create pillars for this row
        for col in range(pillars_in_row):
            pillar_copy = hex_pillar.copy()
            x_position = x_start + col * x_spacing
            # Position pillars on top of base plate
            pillar_copy.Placement.Base = Vector(x_position, y_position, base_thickness)
            all_pillars.append(pillar_copy)
            total_pillars += 1
    
    print(f"Total pillars created: {total_pillars}")
    
    # Fuse all pillars with base plate
    print("Fusing structure...")
    
    if all_pillars:
        # First create compound of all pillars for efficiency
        pillars_compound = Part.makeCompound(all_pillars)
        # Fuse with base plate
        result = base_plate.fuse(pillars_compound)
        # Remove any internal faces
        result = result.removeSplitter()
    else:
        result = base_plate
    
    # Prepare info dictionary
    info = {
        'module_version': MODULE_VERSION,
        'total_pillars': total_pillars,
        'rows': n_y,
        'pillars_per_row': n_x,
        'x_spacing': x_spacing,
        'y_spacing': y_spacing,
        'hex_width': hex_width,
        'pillar_height': pillar_height,
        'base_thickness': base_thickness,
        'total_thickness': thickness
    }
    
    return result, info


# Additional helper functions can be added here
def calculate_honeycomb_spacing(hex_radius, wall_thickness):
    """
    Calculate spacing parameters for honeycomb pattern
    
    Returns:
    --------
    tuple : (hex_width, x_spacing, y_spacing)
    """
    hex_width = hex_radius * math.sqrt(3)
    x_spacing = hex_width + wall_thickness
    y_spacing = hex_radius * 1.5 + wall_thickness
    return hex_width, x_spacing, y_spacing


def estimate_hexagon_count(length, width, hex_radius, wall_thickness):
    """
    Estimate number of hexagons without creating geometry
    
    Returns:
    --------
    dict : Estimated counts and array configuration
    """
    hex_width, x_spacing, y_spacing = calculate_honeycomb_spacing(hex_radius, wall_thickness)
    margin = hex_radius + wall_thickness
    
    n_x = int((length - 2 * margin) / x_spacing) + 1
    n_y = int((width - 2 * margin) / y_spacing) + 1
    
    # Approximate total (odd rows have one less)
    total_estimate = n_x * n_y - (n_y // 2)
    
    return {
        'cols_per_row': n_x,
        'rows': n_y,
        'total_estimate': total_estimate,
        'x_spacing': x_spacing,
        'y_spacing': y_spacing
    }