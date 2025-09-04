#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FreeCAD Macro: Honeycomb Perforated Plate
Creates a flat plate with honeycomb perforations using Draft Arrays
Version: 3.2 - Unified parameters for both functions
"""

import Part
import math
from FreeCAD import Vector

# Version tracking
MACRO_VERSION = "3.2"

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
        'version': MACRO_VERSION,
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
        'version': MACRO_VERSION,
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


def apply_to_freecad_document(shape, info, doc=None):
    """
    Applies the generated geometry to a FreeCAD document
    
    Parameters:
    -----------
    shape : Part.Shape
        The shape to add to the document
    info : dict
        Information about the geometry
    doc : FreeCAD.Document, optional
        Document to use (creates new if None)
    
    Returns:
    --------
    FreeCAD object : The created document object
    """
    import FreeCAD
    import FreeCADGui
    
    if doc is None:
        doc = FreeCAD.activeDocument()
        if doc is None:
            doc = FreeCAD.newDocument("HoneycombPlate")
    
    # Create the FreeCAD object
    obj = doc.addObject("Part::Feature", "HoneycombPlate")
    obj.Shape = shape
    
    # Set visual properties if available
    if hasattr(obj, 'ViewObject'):
        obj.ViewObject.ShapeColor = (0.7, 0.7, 0.85)
        obj.ViewObject.DisplayMode = "Shaded"
    
    # Add custom properties to store parameters
    obj.addProperty("App::PropertyString", "GeneratorVersion", "Honeycomb", "Version of generator used")
    obj.GeneratorVersion = info['version']
    
    if 'total_hexagons' in info:
        obj.addProperty("App::PropertyInteger", "TotalHexagons", "Honeycomb", "Total number of hexagon holes")
        obj.TotalHexagons = info['total_hexagons']
    elif 'total_pillars' in info:
        obj.addProperty("App::PropertyInteger", "TotalPillars", "Honeycomb", "Total number of hexagon pillars")
        obj.TotalPillars = info['total_pillars']
    
    obj.addProperty("App::PropertyInteger", "Rows", "Honeycomb", "Number of rows")
    obj.Rows = info['rows']
    
    doc.recompute()
    
    # Fit view if GUI is available
    if FreeCADGui:
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
    
    return obj


# ============ MAIN EXECUTION ============
if __name__ == "__main__":
    import FreeCAD
    import FreeCADGui
    
    print(f"=== Honeycomb Plate Macro v{MACRO_VERSION} ===")
    print("Changes: Unified parameters - same params dict works for both functions")
    
    # PARAMETERS - These will eventually come from UI or external config
    params = {
        'length': 400.0,        # X dimension (mm)
        'width': 100.0,         # Y dimension (mm)
        'thickness': 60.0,       # Z dimension - plate thickness OR total structure height (mm)
        'hex_radius': 5.0,      # Hexagon radius (mm)
        'wall_thickness': 2.0   # Wall between holes/pillars (mm)
    }
    
    # Choose which geometry to create
    CREATE_STRUCTURE = True  # Set to True for honeycomb structure, False for perforated plate
    
    # Both functions now use the same parameters:
    # - For perforated plate: thickness = plate thickness
    # - For honeycomb structure: thickness = total height (10% base, 90% pillars)
    
    if CREATE_STRUCTURE:
        # Generate honeycomb structure (solid pillars with base)
        shape, info = create_honeycomb_structure(
            **params  # Use all the same parameters
        )
        print("\nCreated honeycomb structure for boolean cutting")
    else:
        # Generate perforated plate (plate with holes)
        shape, info = create_honeycomb_geometry(
            **params  # Use all the same parameters
        )
        print("\nCreated perforated plate")
    
    # Apply to FreeCAD document (UI operations)
    plate_object = apply_to_freecad_document(shape, info)
    
    print("\n=== Operation completed successfully! ===")
    if CREATE_STRUCTURE:
        print(f"Total pillars: {info['total_pillars']}")
        print(f"Configuration: {info['rows']} rows, up to {info['pillars_per_row']} per row")
        print(f"Total thickness: {info['total_thickness']}mm (base: {info['base_thickness']:.2f}mm, pillars: {info['pillar_height']:.2f}mm)")
    else:
        print(f"Total hexagons: {info['total_hexagons']}")
        print(f"Configuration: {info['rows']} rows, up to {info['hexagons_per_row']} per row")