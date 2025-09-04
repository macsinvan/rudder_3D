#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FreeCAD Macro: Honeycomb Plate GUI
Light GUI wrapper for honeycomb geometry generation
Uses hex_array_helper module for all geometry logic
Version: 4.0 - Modularized architecture
"""

import FreeCAD
import FreeCADGui
import sys
import os

# Add helpers directory to path to import helper
macro_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(macro_dir)  # Go up one level from Macros
helpers_dir = os.path.join(parent_dir, 'helpers')

# Add helpers directory to path
if helpers_dir not in sys.path:
    sys.path.append(helpers_dir)

# Import the geometry helper module
try:
    from hex_array_helper import create_honeycomb_geometry, create_honeycomb_structure
    print(f"Successfully imported hex_array_helper module from: {helpers_dir}")
except ImportError as e:
    print(f"Error importing hex_array_helper: {e}")
    print(f"Looking in: {helpers_dir}")
    print(f"Make sure hex_array_helper.py is in: {helpers_dir}")
    raise

# GUI version tracking
GUI_VERSION = "4.0"


def apply_to_freecad_document(shape, info, doc=None, object_name="HoneycombObject"):
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
    object_name : str
        Name for the created object
    
    Returns:
    --------
    FreeCAD object : The created document object
    """
    if doc is None:
        doc = FreeCAD.activeDocument()
        if doc is None:
            doc = FreeCAD.newDocument("HoneycombPlate")
    
    # Create the FreeCAD object
    obj = doc.addObject("Part::Feature", object_name)
    obj.Shape = shape
    
    # Set visual properties if available
    if hasattr(obj, 'ViewObject'):
        obj.ViewObject.ShapeColor = (0.7, 0.7, 0.85)
        obj.ViewObject.DisplayMode = "Shaded"
    
    # Add custom properties to store parameters
    obj.addProperty("App::PropertyString", "GeneratorVersion", "Honeycomb", "Version of generator used")
    obj.GeneratorVersion = f"GUI: {GUI_VERSION}, Module: {info.get('module_version', 'unknown')}"
    
    if 'total_hexagons' in info:
        obj.addProperty("App::PropertyInteger", "TotalHexagons", "Honeycomb", "Total number of hexagon holes")
        obj.TotalHexagons = info['total_hexagons']
    elif 'total_pillars' in info:
        obj.addProperty("App::PropertyInteger", "TotalPillars", "Honeycomb", "Total number of hexagon pillars")
        obj.TotalPillars = info['total_pillars']
    
    obj.addProperty("App::PropertyInteger", "Rows", "Honeycomb", "Number of rows")
    obj.Rows = info['rows']
    
    # Add spacing info
    if 'x_spacing' in info:
        obj.addProperty("App::PropertyFloat", "XSpacing", "Honeycomb", "Horizontal spacing")
        obj.XSpacing = info['x_spacing']
    
    if 'y_spacing' in info:
        obj.addProperty("App::PropertyFloat", "YSpacing", "Honeycomb", "Vertical spacing")
        obj.YSpacing = info['y_spacing']
    
    doc.recompute()
    
    # Fit view if GUI is available
    try:
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
    except:
        pass  # No GUI available
    
    return obj


def create_honeycomb_plate(params, create_structure=False):
    """
    Main function to create honeycomb geometry with given parameters
    
    Parameters:
    -----------
    params : dict
        Dictionary with keys: length, width, thickness, hex_radius, wall_thickness
    create_structure : bool
        If True, creates pillars; if False, creates perforated plate
    
    Returns:
    --------
    FreeCAD object : The created object in the document
    """
    print(f"\n=== Honeycomb Plate GUI v{GUI_VERSION} ===")
    print(f"Creating: {'Honeycomb Structure' if create_structure else 'Perforated Plate'}")
    print(f"Parameters: {params}")
    
    if create_structure:
        # Generate honeycomb structure (solid pillars with base)
        shape, info = create_honeycomb_structure(**params)
        object_name = "HoneycombStructure"
    else:
        # Generate perforated plate (plate with holes)
        shape, info = create_honeycomb_geometry(**params)
        object_name = "PerforatedPlate"
    
    # Apply to FreeCAD document
    obj = apply_to_freecad_document(shape, info, object_name=object_name)
    
    print("\n=== Operation completed successfully! ===")
    if create_structure:
        print(f"Total pillars: {info.get('total_pillars', 'N/A')}")
        if 'total_thickness' in info:
            print(f"Total thickness: {info['total_thickness']}mm")
            print(f"  Base: {info.get('base_thickness', 0):.2f}mm")
            print(f"  Pillars: {info.get('pillar_height', 0):.2f}mm")
    else:
        print(f"Total hexagon holes: {info.get('total_hexagons', 'N/A')}")
    
    print(f"Configuration: {info.get('rows', 0)} rows")
    
    return obj


# ============ MAIN EXECUTION ============
if __name__ == "__main__":
    
    # Default parameters
    params = {
        'length': 400.0,        # X dimension (mm)
        'width': 100.0,         # Y dimension (mm)
        'thickness': 6.0,       # Z dimension - plate thickness OR total structure height
        'hex_radius': 5.0,      # Hexagon radius (mm)
        'wall_thickness': 2.0   # Wall between holes/pillars (mm)
    }
    
    # User configuration
    CREATE_STRUCTURE = False  # Set to True for pillars, False for perforated plate
    
    # Create the honeycomb geometry
    result = create_honeycomb_plate(params, create_structure=CREATE_STRUCTURE)
    
    print(f"\nCreated object: {result.Name}")
    print(f"Shape volume: {result.Shape.Volume:.2f} mm³")
    print(f"Shape area: {result.Shape.Area:.2f} mm²")