# FreeCAD Macro for Simple Test Cylinder - Foam Filling Tests
# Version: 2.0 - Simplified
# Description: Creates a simple parametric cylinder for 3D printing and foam filling tests

import FreeCAD
import FreeCADGui
import Part
import Mesh
import os
from FreeCAD import Base

# Clear console for clean output
FreeCAD.Console.PrintMessage("Creating Test Cylinder...\n")

# ==============================================================================
# PARAMETERS - Modify these values for different test cylinders
# ==============================================================================

# Cylinder dimensions (in mm)
cylinder_diameter = 50.0  # Diameter of the cylinder
cylinder_height = 50.0    # Height of the cylinder

# Optional parameters for hollow version
create_hollow = False     # Set to True to create a hollow cylinder
wall_thickness = 3.0      # Wall thickness if hollow (in mm)

# STL Export settings
auto_export_stl = True    # Automatically export to STL after creation
stl_mesh_tolerance = 0.1  # Mesh tolerance in mm (lower = higher quality)

# ==============================================================================
# MAIN SCRIPT - Creates the cylinder
# ==============================================================================

def create_test_cylinder():
    """Create a parametric test cylinder for foam filling experiments"""
    
    # Create a new document if none exists
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument("TestCylinder")
    
    doc = FreeCAD.ActiveDocument
    
    # Calculate radius from diameter
    cylinder_radius = cylinder_diameter / 2.0
    
    # Create the main cylinder
    FreeCAD.Console.PrintMessage(f"Creating cylinder: {cylinder_diameter}mm dia x {cylinder_height}mm height\n")
    
    if create_hollow:
        # Create hollow cylinder using two cylinders and boolean cut
        outer_cylinder = Part.makeCylinder(
            cylinder_radius, 
            cylinder_height,
            Base.Vector(0, 0, 0),
            Base.Vector(0, 0, 1)
        )
        
        inner_radius = cylinder_radius - wall_thickness
        if inner_radius > 0:
            inner_cylinder = Part.makeCylinder(
                inner_radius,
                cylinder_height - wall_thickness,  # Leave bottom closed
                Base.Vector(0, 0, wall_thickness),
                Base.Vector(0, 0, 1)
            )
            
            # Boolean cut to create hollow cylinder
            main_shape = outer_cylinder.cut(inner_cylinder)
            FreeCAD.Console.PrintMessage(f"Created hollow cylinder with {wall_thickness}mm wall thickness\n")
        else:
            main_shape = outer_cylinder
            FreeCAD.Console.PrintMessage("Warning: Wall thickness too large for hollow cylinder\n")
    else:
        # Create solid cylinder
        main_shape = Part.makeCylinder(
            cylinder_radius,
            cylinder_height,
            Base.Vector(0, 0, 0),
            Base.Vector(0, 0, 1)
        )
        FreeCAD.Console.PrintMessage("Created solid cylinder\n")
    
    # Create the FreeCAD object
    cylinder_obj = doc.addObject("Part::Feature", "TestCylinder")
    cylinder_obj.Shape = main_shape
    
    # Add custom properties for parametric control
    cylinder_obj.addProperty("App::PropertyLength", "Diameter", "Dimensions", "Cylinder diameter")
    cylinder_obj.Diameter = cylinder_diameter
    
    cylinder_obj.addProperty("App::PropertyLength", "Height", "Dimensions", "Cylinder height")
    cylinder_obj.Height = cylinder_height
    
    if create_hollow:
        cylinder_obj.addProperty("App::PropertyLength", "WallThickness", "Dimensions", "Wall thickness for hollow cylinder")
        cylinder_obj.WallThickness = wall_thickness
    
    # Calculate volume
    volume_cm3 = main_shape.Volume / 1000
    
    # Recompute and fit view
    doc.recompute()
    
    # Try to fit view if GUI is available
    try:
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
        FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
    except:
        pass  # GUI commands not available in console mode
    
    # Print summary
    FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
    FreeCAD.Console.PrintMessage("CYLINDER CREATED SUCCESSFULLY!\n")
    FreeCAD.Console.PrintMessage(f"Type: {'Hollow' if create_hollow else 'Solid'}\n")
    FreeCAD.Console.PrintMessage(f"Dimensions: {cylinder_diameter}mm dia x {cylinder_height}mm height\n")
    FreeCAD.Console.PrintMessage(f"Volume: {volume_cm3:.1f} cm³\n")
    
    if create_hollow:
        internal_volume = 3.14159 * (cylinder_radius - wall_thickness)**2 * (cylinder_height - wall_thickness)
        FreeCAD.Console.PrintMessage(f"Internal volume for foam: {internal_volume/1000:.1f} cm³\n")
    
    FreeCAD.Console.PrintMessage("="*50 + "\n")
    
    return cylinder_obj

# ==============================================================================
# STL EXPORT FUNCTION
# ==============================================================================

def export_to_stl(obj, filename=None):
    """Export the object to STL file for 3D printing"""
    
    if filename is None:
        # Generate default filename based on parameters
        if create_hollow:
            filename = f"TestCylinder_D{int(cylinder_diameter)}_H{int(cylinder_height)}_Hollow_W{wall_thickness}.stl"
        else:
            filename = f"TestCylinder_D{int(cylinder_diameter)}_H{int(cylinder_height)}_Solid.stl"
    
    # Get Downloads folder path
    downloads_path = os.path.expanduser("~/Downloads")
    
    # Create full path
    full_path = os.path.join(downloads_path, filename)
    
    try:
        # Create mesh from shape with specified tolerance
        mesh_obj = Mesh.Mesh(obj.Shape.tessellate(stl_mesh_tolerance))
        
        # Export to STL
        mesh_obj.write(full_path)
        
        FreeCAD.Console.PrintMessage(f"\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage(f"STL EXPORT SUCCESSFUL!\n")
        FreeCAD.Console.PrintMessage(f"File: {filename}\n")
        FreeCAD.Console.PrintMessage(f"Location: {full_path}\n")
        
        # Check file size
        if os.path.exists(full_path):
            file_size = os.path.getsize(full_path) / 1024
            FreeCAD.Console.PrintMessage(f"File size: {file_size:.1f} KB\n")
        
        # Print slicer recommendations
        FreeCAD.Console.PrintMessage("\n" + "-"*50 + "\n")
        FreeCAD.Console.PrintMessage("RECOMMENDED BAMBU STUDIO SETTINGS:\n\n")
        FreeCAD.Console.PrintMessage("For Foam Filling (drill hole after printing):\n")
        FreeCAD.Console.PrintMessage("  • Infill Pattern: GYROID (best for foam flow)\n")
        FreeCAD.Console.PrintMessage("  • Infill Density: 5-10%\n")
        FreeCAD.Console.PrintMessage("  • Wall Loops: 2-3\n")
        FreeCAD.Console.PrintMessage("  • Top/Bottom Layers: 3-4\n")
        FreeCAD.Console.PrintMessage("  • Layer Height: 0.2-0.3mm\n")
        FreeCAD.Console.PrintMessage("\nWhy Gyroid is Best:\n")
        FreeCAD.Console.PrintMessage("  • Continuous 3D channels in all directions\n")
        FreeCAD.Console.PrintMessage("  • No dead ends - foam flows everywhere\n")
        FreeCAD.Console.PrintMessage("  • Strong isotropic structure\n")
        FreeCAD.Console.PrintMessage("  • Perfect for liquid/foam distribution\n")
        FreeCAD.Console.PrintMessage("\nPost-Processing:\n")
        FreeCAD.Console.PrintMessage("  1. Drill 5mm hole at top center\n")
        FreeCAD.Console.PrintMessage("  2. Drill depth: 35-40mm\n")
        FreeCAD.Console.PrintMessage("  3. Inject marine foam - it will flow through gyroid channels\n")
        FreeCAD.Console.PrintMessage("  4. Fill to ~75% capacity (foam expands)\n")
        FreeCAD.Console.PrintMessage("  5. Allow 24 hours to cure\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        return full_path
    
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error exporting STL: {str(e)}\n")
        FreeCAD.Console.PrintMessage("Try File → Export and select STL format manually\n")
        return None

# ==============================================================================
# EXECUTE THE SCRIPT
# ==============================================================================

# Run the cylinder creation
test_cylinder = create_test_cylinder()

# Auto-export to STL if enabled
if auto_export_stl:
    stl_path = export_to_stl(test_cylinder)
    if stl_path:
        FreeCAD.Console.PrintMessage("\nReady for 3D printing!\n")
        FreeCAD.Console.PrintMessage("Import the STL file into Bambu Studio to begin slicing.\n")
else:
    FreeCAD.Console.PrintMessage("\nManual STL export required:\n")
    FreeCAD.Console.PrintMessage("File → Export → Select STL format\n")

# Optional: Create multiple test cylinders with different parameters
# Uncomment and modify the following to create a batch of test pieces

"""
# Example: Create multiple test pieces
test_configs = [
    {"dia": 30, "height": 30, "name": "Small"},
    {"dia": 50, "height": 50, "name": "Medium"},
    {"dia": 70, "height": 70, "name": "Large"},
]

for i, config in enumerate(test_configs):
    cylinder_diameter = config["dia"]
    cylinder_height = config["height"]
    
    cylinder = create_test_cylinder()
    cylinder.Placement.Base.x = i * (config["dia"] + 10)  # Space them out
    cylinder.Label = f"TestCylinder_{config['name']}"
    
    # Export each test piece
    export_to_stl(cylinder, f"TestCylinder_{config['name']}.stl")
"""