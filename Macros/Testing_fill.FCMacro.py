"""
FreeCAD Macro to add complete internal structure to shell
Adds both horizontal plates and vertical centerline rim in one operation
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

# Parameters for horizontal plates
SECTION_HEIGHT = 268.8  # mm - height of each printed section
PLATE_THICKNESS = 8.0   # mm - plates at section boundaries
FLOW_HOLE_DIAMETER = 15.0  # mm - holes for resin flow
WALL_THICKNESS = 3.0  # mm - shell wall thickness

# Parameters for vertical rim
RIM_THICKNESS = 8.0     # mm - same as horizontal plates
RIM_WIDTH = 30.0        # mm - width of rim from shell wall inward

# File paths
SHELL_STEP = Path.home() / "Rudder_Code" / "boats" / "MackenSea" / "output" / "cut_foil" / "MackenSea_Shell_Foil.step"

# Get or create document
doc = FreeCAD.ActiveDocument
if doc is None:
    doc = FreeCAD.newDocument("CompleteStructure")

print("="*60)
print("ADDING COMPLETE INTERNAL STRUCTURE")
print("="*60)

# =====================================
# STEP 1: IMPORT SHELL
# =====================================

print(f"\n1. Importing shell from: {SHELL_STEP.name}")
doc, imported_objects = load_step(str(SHELL_STEP), doc.Name, verbose=False)

if not imported_objects:
    print("ERROR: Failed to import shell")
    sys.exit(1)

shell = imported_objects[0]
shell.Label = "Original_Shell"
bbox = shell.Shape.BoundBox

print(f"   Shell height: {bbox.ZLength:.1f}mm")
print(f"   Shell chord: {bbox.XLength:.1f}mm")
print(f"   Shell width: {bbox.YLength:.1f}mm")

# =====================================
# STEP 2: ADD 3 HORIZONTAL PLATES
# =====================================

print(f"\n2. Adding 3 horizontal plates at cut positions")

# Calculate 3 internal cut positions (not at ends)
cut_positions = []
for i in range(1, 4):  # Skip 0 (bottom) and 4 (top)
    z_pos = bbox.ZMin + i * SECTION_HEIGHT
    cut_positions.append(z_pos)

print(f"   Cut positions: {[f'{p:.1f}' for p in cut_positions]}")

# Create 3 internal plates AS SEPARATE OBJECTS
all_plates = []
plate_objects = []  # Store plate objects
teardrop_objects = []  # Store teardrop debug objects

for i, z_pos in enumerate(cut_positions):
    try:
        # Create a horizontal plane at z_pos
        plane = Part.makePlane(
            bbox.XLength + 200,  # Large enough to cover shell
            bbox.YLength + 200,
            Base.Vector(bbox.XMin - 100, bbox.YMin - 100, z_pos),
            Base.Vector(0, 0, 1)  # Normal pointing up
        )
        
        # Get cross-section edges where plane cuts shell
        section_edges = shell.Shape.section(plane)
        
        if section_edges.Edges:
            # Sort edges into wires
            sorted_edge_groups = Part.sortEdges(section_edges.Edges)
            
            if sorted_edge_groups:
                # Convert sorted edge groups to wires
                wires = []
                for edge_group in sorted_edge_groups:
                    try:
                        wire = Part.Wire(edge_group)
                        if wire.isClosed():
                            wires.append(wire)
                    except:
                        pass
                
                if wires:
                    # Select the outer wire (largest by bounding box diagonal)
                    outer_wire = max(wires, key=lambda w: w.BoundBox.DiagonalLength)
                    
                    # Create face from outer wire
                    face = Part.Face(outer_wire)
                    
                    # Extrude face to create solid plate
                    plate_shape = face.extrude(Base.Vector(0, 0, -PLATE_THICKNESS))
                    
                    # Center the plate on z_pos
                    plate_shape.translate(Base.Vector(0, 0, PLATE_THICKNESS/2))
                    
                    # ADD SINGLE TEARDROP HOLE (DEBUG VERSION)
                    import math
                    
                    # Get plate dimensions for sizing
                    plate_bbox = plate_shape.BoundBox
                    plate_width = plate_bbox.YLength  # Y is the width
                    plate_length = plate_bbox.XLength  # X is the length
                    
                    print(f"   Plate {i+1} dimensions: {plate_length:.1f}mm x {plate_width:.1f}mm")
                    
                    # TEARDROP POSITIONING FOR SPLIT AT Y=0
                    # Foil will be split at Y=0, so we place teardrop on positive Y half
                    half_width = (plate_width / 2)  - WALL_THICKNESS# Width of each half after split, accounting for wall
                    clearance_from_split = 3.0  # mm clearance from Y=0
                    
                    # Available space on positive half: from Y=3mm to Y=half_width
                    available_width = half_width - clearance_from_split
                    
                    # Size teardrop to fit in available space with margins
                    # Leave margins for multiple teardrops with 3mm spacing
                    margin = 3.0  # mm margin from outer edge
                    usable_width = available_width - margin
                    
                    # Teardrop radius should allow for clean printing
                    radius = min(usable_width * 0.4, FLOW_HOLE_DIAMETER / 2)  # Use 40% of space or standard hole size
                    
                    print(f"   Half plate width: {half_width:.1f}mm")
                    print(f"   Available width (3mm from split): {available_width:.1f}mm") 
                    print(f"   Teardrop radius: {radius:.1f}mm (diameter: {radius*2:.1f}mm)")
                    
                    # Position teardrop on positive Y half
                    # Center it in the available space
                    center_x = (plate_bbox.XMin + plate_bbox.XMax) / 2
                    center_y = clearance_from_split + available_width / 2  # Center in available space on positive half
                    center_z = z_pos
                    
                    print(f"   Teardrop center Y position: {center_y:.1f}mm (from Y=0)")
                    
                    # Create teardrop outline points IN XY PLANE
                    # TIP POINTS AWAY FROM CENTERLINE (in +Y direction)
                    points = []
                    
                    # Generate arc points for bottom (semicircle closest to centerline)
                    num_arc_points = 16
                    for j in range(num_arc_points + 1):
                        angle = math.pi + (math.pi * float(j) / num_arc_points)  # π to 2π (bottom half)
                        x = center_x + radius * math.cos(angle)
                        y = center_y + radius * math.sin(angle)
                        z = center_z
                        points.append(Base.Vector(x, y, z))
                    
                    # Add top point (teardrop tip pointing away from centerline)
                    tip_distance = radius * 1.5
                    points.append(Base.Vector(center_x, center_y + tip_distance, center_z))
                    
                    # Close the polygon
                    points.append(points[0])
                    
                    # Create teardrop wire and face
                    teardrop_wire = Part.makePolygon(points)
                    teardrop_face = Part.Face(teardrop_wire)
                    
                    # Extrude teardrop
                    teardrop_solid = teardrop_face.extrude(Base.Vector(0, 0, PLATE_THICKNESS + 2))
                    teardrop_solid.translate(Base.Vector(0, 0, -PLATE_THICKNESS/2 - 1))
                    
                    # CREATE SEPARATE TEARDROP OBJECT FOR DEBUGGING
                    teardrop_obj = doc.addObject("Part::Feature", f"Teardrop_Debug_{i+1}")
                    teardrop_obj.Shape = teardrop_solid
                    teardrop_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)  # Red for visibility
                    teardrop_obj.ViewObject.Transparency = 20
                    teardrop_objects.append(teardrop_obj)
                    
                    # COMMENT OUT THE CUT FOR NOW - JUST CREATE PLATE WITHOUT HOLE
                    # plate_shape = plate_shape.cut(teardrop_solid)
                    
                    all_plates.append(plate_shape)
                    
                    # CREATE SEPARATE PLATE OBJECT
                    plate_obj = doc.addObject("Part::Feature", f"Horizontal_Plate_{i+1}")
                    plate_obj.Shape = plate_shape
                    plate_obj.ViewObject.ShapeColor = (0.2, 0.8, 0.2)  # Green for visibility
                    plate_obj.ViewObject.Transparency = 30
                    plate_objects.append(plate_obj)
                    
                    print(f"   ✅ Plate {i+1} created at Z={z_pos:.1f}mm with DEBUG teardrop")
                else:
                    print(f"   ❌ No closed wires found at Z={z_pos:.1f}mm")
            else:
                print(f"   ❌ Could not sort edges at Z={z_pos:.1f}mm")
        else:
            print(f"   ❌ No intersection edges at Z={z_pos:.1f}mm")
    except Exception as e:
        print(f"   ❌ Failed plate at Z={z_pos:.1f}mm: {e}")

# KEEP SHELL SEPARATE - DON'T FUSE WITH PLATES
print(f"   ✅ {len(all_plates)} horizontal plates created as separate objects")
print(f"   ✅ {len(teardrop_objects)} teardrop debug objects created")

# =====================================
# STEP 3: ADD VERTICAL CENTERLINE RIM
# =====================================

print(f"\n3. Adding vertical centerline rim")
print(f"   Position: Y=0 (centerline)")
print(f"   Thickness: {RIM_THICKNESS}mm")
print(f"   Rim width: {RIM_WIDTH}mm")

# Create a large box at Y=0 to intersect with shell
rim_box = Part.makeBox(
    bbox.XLength + 100,
    RIM_THICKNESS,
    bbox.ZLength + 100,
    Base.Vector(
        bbox.XMin - 50,
        -RIM_THICKNESS/2,  # Centered at Y=0
        bbox.ZMin - 50
    )
)

# Intersect with shell to get rim shape (USE ORIGINAL SHELL, NOT shell_with_plates)
rim_full = shell.Shape.common(rim_box)

if rim_full.isNull() or rim_full.Volume == 0:
    print("   ❌ Failed to create rim intersection")
else:
    # Create cutout for center (leaving rim around edges)
    rim_bbox = rim_full.BoundBox
    
    cutout_box = Part.makeBox(
        rim_bbox.XLength - 2*RIM_WIDTH,
        RIM_THICKNESS + 2,
        rim_bbox.ZLength - 2*RIM_WIDTH,
        Base.Vector(
            rim_bbox.XMin + RIM_WIDTH,
            -RIM_THICKNESS/2 - 1,
            rim_bbox.ZMin + RIM_WIDTH
        )
    )
    
    # Cut center from rim to create frame
    rim_frame = rim_full.cut(cutout_box)
    
    # NO CROSS-MEMBERS - just use the rim frame as-is
    
    print(f"   ✅ Rim created: Volume = {rim_frame.Volume/1000:.1f} cm³")
    
    # Create rim as separate object for visualization
    rim_obj = doc.addObject("Part::Feature", "Centerline_Rim")
    rim_obj.Shape = rim_frame
    rim_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red for visibility
    rim_obj.ViewObject.Transparency = 30
    
    print(f"   ✅ Vertical rim created as separate object")

# =====================================
# STEP 4: CREATE FINAL OBJECTS
# =====================================

print(f"\n4. Creating final objects")

# Create shell object (WITHOUT PLATES FUSED)
shell_only_obj = doc.addObject("Part::Feature", "Shell_Only")
shell_only_obj.Shape = shell.Shape
shell_only_obj.ViewObject.ShapeColor = (0.2, 0.6, 0.8)
shell_only_obj.ViewObject.Transparency = 50  # Make semi-transparent to see plates

# Hide original shell
shell.ViewObject.Visibility = False

# Calculate statistics
original_volume = shell.Shape.Volume
plates_volume = sum([plate.Volume for plate in all_plates])
if 'rim_frame' in locals():
    rim_volume = rim_frame.Volume
else:
    rim_volume = 0

print(f"   Original shell volume: {original_volume/1000:.1f} cm³")
print(f"   Plates volume: {plates_volume/1000:.1f} cm³")
if rim_volume > 0:
    print(f"   Rim volume: {rim_volume/1000:.1f} cm³")
print(f"   Total structure volume: {(original_volume + plates_volume + rim_volume)/1000:.1f} cm³")

doc.recompute()
FreeCADGui.ActiveDocument.ActiveView.fitAll()

print("\n" + "="*60)
print("COMPLETE - DEBUG MODE")
print("="*60)
print("Created separate objects:")
print("- Shell_Only: Shell without plates (semi-transparent blue)")
print("- Horizontal_Plate_1, 2, 3: Three SOLID plates (green)")
print("- Teardrop_Debug_1, 2, 3: Three teardrop objects (red)")
if rim_volume > 0:
    print("- Centerline_Rim: Vertical rim at Y=0 (red)")
print("\nTeardrops are separate objects for size/position verification")
print("Once correct, uncomment the cut operation to create holes")
print("="*60)