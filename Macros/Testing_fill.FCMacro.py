"""
FreeCAD Macro to check the shell thickness of imported foil
Measures wall thickness at multiple points to verify it meets requirements
"""

import sys
from pathlib import Path
import FreeCAD
import Part
from FreeCAD import Base

# Add project root to path for imports
project_root = Path.home() / "Rudder_Code"
if project_root.exists():
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "helpers"))

from step_save_load import load_step

# Get or create document
doc = FreeCAD.ActiveDocument
if doc is None:
    doc = FreeCAD.newDocument("ShellCheck")

# ====================
# IMPORT FOIL
# ====================

step_file = Path.home() / "Rudder_Code" / "boats" / "MackenSea" / "output" / "cut_foil" / "MackenSea_Shell_Foil.step"

print("="*60)
print("SHELL THICKNESS VERIFICATION")
print("="*60)

# Check if already imported
foil = None
for obj in doc.Objects:
    if "Part__Feature" in obj.Name or "Foil" in obj.Name:
        foil = obj
        print("Using existing imported foil")
        break

if not foil:
    print(f"Importing: {step_file.name}")
    doc, imported_objects = load_step(str(step_file), doc.Name, verbose=False)
    if imported_objects:
        foil = imported_objects[0]
        foil.Label = "Imported_Foil"
    else:
        print("ERROR: Failed to import foil")
        sys.exit(1)

# ====================
# ANALYZE SHELL
# ====================

shape = foil.Shape
bbox = shape.BoundBox

print(f"\nFoil dimensions:")
print(f"  Height: {bbox.ZLength:.1f}mm")
print(f"  Chord: {bbox.XLength:.1f}mm") 
print(f"  Width: {bbox.YLength:.1f}mm")

# Check if it's a shell by looking at faces
faces = shape.Faces
print(f"\nNumber of faces: {len(faces)}")

# Method 1: Check volume vs surface area ratio
volume = shape.Volume / 1000  # Convert to cm³
area = shape.Area / 100  # Convert to cm²

print(f"\nVolume: {volume:.1f} cm³")
print(f"Surface area: {area:.1f} cm²")

# For a thin shell, volume/area ratio approximates average thickness
estimated_thickness = (volume / area) * 10  # Convert to mm
print(f"Estimated average thickness: {estimated_thickness:.2f}mm")

# Method 2: Sample thickness at multiple points
print("\n" + "="*60)
print("SAMPLING WALL THICKNESS AT MULTIPLE POINTS")
print("="*60)

# Create rays from outside to inside at various points
sample_points = []
thickness_measurements = []

# Sample at different heights and positions
for z in [-1000, -800, -600, -400, -200]:  # Different heights
    for x in [50, 150, 250, 350]:  # Different chord positions
        # Create a horizontal ray through the foil
        ray_start = Base.Vector(x, 100, z)  # Start outside
        ray_end = Base.Vector(x, -100, z)   # End on other side
        
        # Find intersections with shape
        ray = Part.makeLine(ray_start, ray_end)
        try:
            intersections = shape.section(ray)
            if intersections.Edges:
                # Get intersection points
                points = []
                for edge in intersections.Edges:
                    for vertex in edge.Vertexes:
                        points.append(vertex.Point)
                
                # If we have pairs of points, calculate thickness
                if len(points) >= 2:
                    # Sort by Y coordinate
                    points.sort(key=lambda p: p.y, reverse=True)
                    
                    # Calculate thickness between outer pairs
                    if len(points) >= 2:
                        thickness = abs(points[0].y - points[1].y)
                        thickness_measurements.append(thickness)
                        
                        if len(thickness_measurements) <= 10:  # Show first 10
                            print(f"  At X={x:.0f}, Z={z:.0f}: {thickness:.2f}mm")
                        
        except Exception as e:
            pass  # Skip failed measurements

if thickness_measurements:
    avg_thickness = sum(thickness_measurements) / len(thickness_measurements)
    min_thickness = min(thickness_measurements)
    max_thickness = max(thickness_measurements)
    
    print(f"\nMeasurement summary ({len(thickness_measurements)} samples):")
    print(f"  Average thickness: {avg_thickness:.2f}mm")
    print(f"  Minimum thickness: {min_thickness:.2f}mm")
    print(f"  Maximum thickness: {max_thickness:.2f}mm")
    
    # Check if it meets requirements
    target_thickness = 3.0
    tolerance = 0.5
    
    print(f"\n" + "="*60)
    print("VERIFICATION RESULT")
    print(f"="*60)
    print(f"Target thickness: {target_thickness}mm ± {tolerance}mm")
    
    if abs(avg_thickness - target_thickness) <= tolerance:
        print("✅ Shell thickness is within acceptable range")
        print("   No modification needed")
    else:
        print("❌ Shell thickness needs adjustment")
        print(f"   Current: {avg_thickness:.2f}mm")
        print(f"   Target: {target_thickness}mm")
        print(f"   Difference: {avg_thickness - target_thickness:+.2f}mm")
        
        if avg_thickness < target_thickness:
            print("\n   ACTION: Need to THICKEN the shell")
        else:
            print("\n   ACTION: Shell is too thick (unusual)")
        
        print("\n⚠️  STOPPING - Shell thickness requirement not met")
        print("   Fix thickness before proceeding")
        sys.exit(1)
else:
    print("\n⚠️  Could not measure thickness directly")
    print(f"   Based on volume/area ratio: ~{estimated_thickness:.2f}mm")

# Method 3: Check for inner/outer surface
print("\n" + "="*60)
print("CHECKING FOR INNER/OUTER SURFACES")
print("="*60)

# Check if shape is a solid or shell
if shape.Solids:
    print(f"Shape contains {len(shape.Solids)} solid(s)")
    if len(shape.Shells) > 1:
        print("Multiple shells detected - likely hollow")
    else:
        print("Single solid - may need hollowing")
else:
    print("No solids detected - appears to be surface/shell")

# Visual aids
if True:  # Set to False to skip visualization
    # Add a cutting plane to see cross-section
    cut_plane = Part.makePlane(
        500, 200,
        Base.Vector(-50, 0, -600),
        Base.Vector(1, 0, 0)
    )
    
    plane_obj = doc.addObject("Part::Feature", "Section_Plane")
    plane_obj.Shape = cut_plane
    plane_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
    plane_obj.ViewObject.Transparency = 90
    
    print("\nAdded section plane for visual inspection")

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
print("="*60)

doc.recompute()