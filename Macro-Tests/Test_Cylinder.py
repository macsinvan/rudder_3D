# FreeCAD Macro for Test Cylinder - Foam Filling Tests
# Version: 1.1 Compatible
# Description: Creates a parametric solid cylinder for testing 3D printing 
#              and marine foam filling techniques with automatic STL export

import FreeCAD
import FreeCADGui
import Part
import Mesh
import os
from FreeCAD import Base

# Clear console for clean output
FreeCAD.Console.PrintMessage("Creating Test Cylinder for Foam Filling...\n")

# ==============================================================================
# PARAMETERS - Modify these values for different test cylinders
# ==============================================================================

# Cylinder dimensions (in mm)
cylinder_diameter = 50.0  # Diameter of the cylinder
cylinder_height = 200.0   # Height of the cylinder

# Optional parameters for hollow version testing
create_hollow = False     # Set to True to create a hollow cylinder
wall_thickness = 3.0      # Wall thickness if hollow (in mm)

# Optional foam injection hole parameters
add_injection_hole = False  # Set to True to add a foam injection hole
injection_hole_diameter = 5.0  # Diameter of injection hole (in mm)
injection_hole_height = 50.0  # Height from bottom for injection hole (in mm)

# STL Export settings
auto_export_stl = True  # Automatically export to STL after creation
stl_mesh_tolerance = 0.1  # Mesh tolerance in mm (lower = higher quality)

# ==============================================================================
# MAIN SCRIPT - Creates the cylinder
# ==============================================================================

def create_test_cylinder():
    """Create a parametric test cylinder for foam filling experiments"""
    
    # Create a new document if none exists
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument("FoamTestCylinder")
    
    doc = FreeCAD.ActiveDocument
    
    # Calculate radius from diameter
    cylinder_radius = cylinder_diameter / 2.0
    
    # Create the main cylinder
    FreeCAD.Console.PrintMessage(f"Creating cylinder: Diameter={cylinder_diameter}mm, Height={cylinder_height}mm\n")
    
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
    
    # Add injection hole if requested
    if add_injection_hole:
        hole_radius = injection_hole_diameter / 2.0
        
        # Create horizontal hole for foam injection
        hole_cylinder = Part.makeCylinder(
            hole_radius,
            cylinder_radius + 10,  # Make sure it goes through the wall
            Base.Vector(-cylinder_radius - 5, 0, injection_hole_height),
            Base.Vector(1, 0, 0)  # Horizontal direction
        )
        
        # Cut the hole from the main shape
        main_shape = main_shape.cut(hole_cylinder)
        FreeCAD.Console.PrintMessage(f"Added injection hole: {injection_hole_diameter}mm diameter at {injection_hole_height}mm height\n")
        
        # Optional: Add air escape hole at top
        if create_hollow:
            escape_hole = Part.makeCylinder(
                2.0,  # 2mm escape hole
                wall_thickness + 5,
                Base.Vector(0, 0, cylinder_height - wall_thickness - 2),
                Base.Vector(0, 0, 1)
            )
            main_shape = main_shape.cut(escape_hole)
            FreeCAD.Console.PrintMessage("Added 2mm air escape hole at top\n")
    
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
    
    if add_injection_hole:
        cylinder_obj.addProperty("App::PropertyLength", "InjectionHoleDiameter", "Foam", "Diameter of foam injection hole")
        cylinder_obj.InjectionHoleDiameter = injection_hole_diameter
        
        cylinder_obj.addProperty("App::PropertyLength", "InjectionHoleHeight", "Foam", "Height of injection hole from bottom")
        cylinder_obj.InjectionHoleHeight = injection_hole_height
    
    # Recompute and fit view
    doc.recompute()
    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    
    # Print summary
    FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
    FreeCAD.Console.PrintMessage("Test Cylinder Created Successfully!\n")
    FreeCAD.Console.PrintMessage(f"Type: {'Hollow' if create_hollow else 'Solid'}\n")
    FreeCAD.Console.PrintMessage(f"Dimensions: {cylinder_diameter}mm dia x {cylinder_height}mm height\n")
    
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
        FreeCAD.Console.PrintMessage("RECOMMENDED BAMBU STUDIO SETTINGS:\n")
        FreeCAD.Console.PrintMessage("For Foam Filling:\n")
        FreeCAD.Console.PrintMessage("  • Infill: 0-5% (Lightning or Lines)\n")
        FreeCAD.Console.PrintMessage("  • Wall Loops: 2-3\n")
        FreeCAD.Console.PrintMessage("  • Top/Bottom Layers: 3\n")
        FreeCAD.Console.PrintMessage("  • Layer Height: 0.2-0.3mm\n")
        FreeCAD.Console.PrintMessage("  • DISABLE 'Ensure vertical shell thickness'\n")
        FreeCAD.Console.PrintMessage("  • Set 'Minimum sparse infill area' to 1000mm²\n")
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
        FreeCAD.Console.PrintMessage("\nFor foam injection after printing:\n")
        FreeCAD.Console.PrintMessage("  1. Drill 5mm hole at 50mm height if not included\n")
        FreeCAD.Console.PrintMessage("  2. Fill to ~75% with marine expanding foam\n")
        FreeCAD.Console.PrintMessage("  3. Allow foam to expand and cure\n")
else:
    FreeCAD.Console.PrintMessage("\nManual STL export required:\n")
    FreeCAD.Console.PrintMessage("File → Export → Select STL format\n")

# Optional: Create multiple test cylinders with different parameters
# Uncomment the following to create a set of test pieces

"""
# Example: Create multiple test pieces with STL export
test_configs = [
    {"dia": 30, "height": 100, "hollow": False, "name": "Small_Solid"},
]

for i, config in enumerate(test_configs):
    cylinder_diameter = config["dia"]
    cylinder_height = config["height"]
    create_hollow = config["Solid"]
    
    cylinder = create_test_cylinder()
    cylinder.Placement.Base.x = i * 60  # Space them out
    cylinder.Label = config["name"]
    
    # Export each test piece
    export_to_stl(cylinder, f"TestCylinder_{config['name']}.stl")
"""