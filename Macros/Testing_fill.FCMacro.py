"""
FreeCAD Macro to add horizontal plates to the shell foil
ONLY 5 plates at the section cut positions, 8mm thick
"""

import sys
from pathlib import Path
import FreeCAD
import Part
from FreeCAD import Base

# Add project root to path
project_root = Path.home() / "Rudder_Code"
if project_root.exists():
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "helpers"))

from step_save_load import load_step

# Parameters
SECTION_HEIGHT = 268.8  # mm - height of each printed section
PLATE_THICKNESS = 8.0   # mm - plates at section boundaries (4mm each side after cut)
FLOW_HOLE_DIAMETER = 15.0  # mm - holes for resin flow

# File paths
SHELL_STEP = Path.home() / "Rudder_Code" / "boats" / "MackenSea" / "output" / "cut_foil" / "MackenSea_Shell_Foil.step"

# Get or create document
doc = FreeCAD.ActiveDocument
if doc is None:
    doc = FreeCAD.newDocument("ShellPlates")

print("="*60)
print("ADDING 3 INTERNAL PLATES AT CUT POSITIONS")
print("="*60)

# Import shell
print(f"Importing shell from: {SHELL_STEP.name}")
doc, imported_objects = load_step(str(SHELL_STEP), doc.Name, verbose=False)

if not imported_objects:
    print("ERROR: Failed to import shell")
    sys.exit(1)

shell = imported_objects[0]
shell.Label = "Shell_Foil"
bbox = shell.Shape.BoundBox

print(f"Shell height: {bbox.ZLength:.1f}mm")

# Calculate 3 internal cut positions (not at ends)
cut_positions = []
for i in range(1, 4):  # Skip 0 (bottom) and 4 (top)
    z_pos = bbox.ZMin + i * SECTION_HEIGHT
    cut_positions.append(z_pos)

print(f"\n3 Internal cut positions:")
for i, pos in enumerate(cut_positions):
    print(f"  Position {i+1}: Z = {pos:.1f}mm")

# Create 3 internal plates
all_plates = []

for i, z_pos in enumerate(cut_positions):
    print(f"\nCreating plate {i+1} at Z={z_pos:.1f}mm...")
    
    # Create plate box
    plate_box = Part.makeBox(
        bbox.XLength + 100,
        bbox.YLength + 100,
        PLATE_THICKNESS,
        Base.Vector(
            bbox.XMin - 50,
            bbox.YMin - 50,
            z_pos - PLATE_THICKNESS/2
        )
    )
    
    # Intersect with shell to get internal plate
    try:
        plate_shape = shell.Shape.common(plate_box)
        
        if not plate_shape.isNull() and plate_shape.Volume > 0:
            # Add flow holes - simple pattern
            pbbox = plate_shape.BoundBox
            
            # Create 4-6 flow holes along the chord
            num_holes = 4
            for j in range(num_holes):
                x = pbbox.XMin + (j + 1) * pbbox.XLength / (num_holes + 1)
                y = pbbox.YMin + pbbox.YLength / 2
                
                hole = Part.makeCylinder(
                    FLOW_HOLE_DIAMETER/2,
                    PLATE_THICKNESS + 2,
                    Base.Vector(x, y, z_pos - PLATE_THICKNESS/2 - 1),
                    Base.Vector(0, 0, 1)
                )
                plate_shape = plate_shape.cut(hole)
            
            all_plates.append(plate_shape)
            print(f"  ✅ Plate created with {num_holes} flow holes")
    except Exception as e:
        print(f"  ❌ Failed: {e}")

print(f"\nCreated {len(all_plates)} plates total")

# Combine shell with plates
print("\nCombining shell with 3 internal plates...")
combined_shape = shell.Shape

for i, plate in enumerate(all_plates):
    print(f"  Adding plate {i+1}...")
    combined_shape = combined_shape.fuse(plate)

# Create final object
final = doc.addObject("Part::Feature", "Shell_With_3_Plates")
final.Shape = combined_shape
final.ViewObject.ShapeColor = (0.2, 0.6, 0.8)

# Hide original shell
shell.ViewObject.Visibility = False

doc.recompute()
FreeCADGui.ActiveDocument.ActiveView.fitAll()

print("\n" + "="*60)
print("COMPLETE")
print("="*60)
print(f"Shell with {len(all_plates)} plates at cut positions")
print("Ready for sectioning")