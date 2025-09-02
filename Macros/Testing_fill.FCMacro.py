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

# Production settings
FUSE_FOR_PRODUCTION = True  # Set True when ready for final unified part

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
                    
                    # ADD HEXAGONAL MESH HOLES
                    import math
                    
                    # Hexagon parameters
                    hex_size = 6.0  # mm across flats
                    hex_spacing = 9.0  # mm center-to-center
                    clearance_from_split = 3.0  # mm clearance from Y=0 centerline
                    
                    # Get plate bounds
                    plate_bbox = plate_shape.BoundBox
                    
                    # Create hexagonal mesh
                    hex_holes = []
                    
                    # Calculate hex grid in X direction (chord)
                    x_start = plate_bbox.XMin + hex_spacing/2
                    x_end = plate_bbox.XMax + 2*hex_spacing  # Extend by 2 rows
                    
                    # Y positions - both sides of centerline with clearance
                    y_positions = []
                    
                    # Positive Y side - add one more row
                    y_pos = clearance_from_split + hex_spacing/2
                    while y_pos < plate_bbox.YMax + hex_spacing/4:  # Reduced margin for extra row
                        y_positions.append(y_pos)
                        y_pos += hex_spacing
                    
                    # Negative Y side - add one more row
                    y_neg = -clearance_from_split - hex_spacing/2
                    while y_neg > plate_bbox.YMin - hex_spacing/4:  # Reduced margin for extra row
                        y_positions.append(y_neg)
                        y_neg -= hex_spacing
                    
                    # Create hexagons at all grid positions
                    for x in [x_start + j*hex_spacing for j in range(int((x_end - x_start)/hex_spacing))]:
                        for y in y_positions:
                            if plate_bbox.XMin < x < plate_bbox.XMax and plate_bbox.YMin < y < plate_bbox.YMax:
                                # Create hexagon points
                                hex_points = []
                                for k in range(6):
                                    angle = k * math.pi / 3  # 60 degree increments
                                    hex_x = x + (hex_size/2) * math.cos(angle)
                                    hex_y = y + (hex_size/2) * math.sin(angle)
                                    hex_points.append(Base.Vector(hex_x, hex_y, z_pos))
                                
                                # Close the hexagon
                                hex_points.append(hex_points[0])
                                
                                # Create hexagon wire and face
                                hex_wire = Part.makePolygon(hex_points)
                                hex_face = Part.Face(hex_wire)
                                
                                # Extrude through plate thickness
                                hex_hole = hex_face.extrude(Base.Vector(0, 0, PLATE_THICKNESS + 2))
                                hex_hole.translate(Base.Vector(0, 0, -PLATE_THICKNESS/2 - 1))
                                hex_holes.append(hex_hole)
                    
                    # Cut all hexagonal holes from plate
                    if hex_holes:
                        hex_compound = Part.makeCompound(hex_holes)
                        plate_shape = plate_shape.cut(hex_compound)
                        print(f"   ✅ Added {len(hex_holes)} hexagonal holes to plate {i+1}")
                    
                    all_plates.append(plate_shape)
                    
                    # CREATE SEPARATE PLATE OBJECT
                    plate_obj = doc.addObject("Part::Feature", f"Horizontal_Plate_{i+1}")
                    plate_obj.Shape = plate_shape
                    plate_obj.ViewObject.ShapeColor = (0.2, 0.8, 0.2)  # Green for visibility
                    plate_obj.ViewObject.Transparency = 30
                    plate_objects.append(plate_obj)
                    
                    print(f"   ✅ Plate {i+1} created at Z={z_pos:.1f}mm")
                else:
                    print(f"   ❌ No closed wires found at Z={z_pos:.1f}mm")
            else:
                print(f"   ❌ Could not sort edges at Z={z_pos:.1f}mm")
        else:
            print(f"   ❌ No intersection edges at Z={z_pos:.1f}mm")
    except Exception as e:
        print(f"   ❌ Failed plate at Z={z_pos:.1f}mm: {e}")

print(f"   ✅ {len(all_plates)} horizontal plates created as separate objects")

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

print("DEBUG: About to test incremental changes")

# Test just the if statement
if all_plates:
    print(f"DEBUG: Found {len(all_plates)} plates to work with")
    
    # Test compound creation
    plates_compound = Part.makeCompound(all_plates)
    print(f"DEBUG: Created compound successfully")
    
    # Check shape validity before fusing
    print(f"DEBUG: Shell valid: {shell.Shape.isValid()}")
    print(f"DEBUG: Compound valid: {plates_compound.isValid()}")
    
    # Check individual plate validity
    for i, plate in enumerate(all_plates):
        print(f"DEBUG: Plate {i+1} valid: {plate.isValid()}")
    
    # Production fusion - only when ready
    if FUSE_FOR_PRODUCTION:
        print(f"DEBUG: PRODUCTION MODE - Starting sequential fusion...")
        print(f"       This will take 3-4 minutes for 616 hexagonal holes...")
        try:
            # Start with shell + first plate
            temp_shape = shell.Shape.fuse(all_plates[0])
            print(f"DEBUG: Fused plate 1 (124 holes) ✅")
            
            # Add second plate  
            temp_shape = temp_shape.fuse(all_plates[1])
            print(f"DEBUG: Fused plate 2 (234 holes) ✅")
            
            # Add third plate
            final_shape = temp_shape.fuse(all_plates[2])
            print(f"DEBUG: Sequential fusion completed - all 616 holes ✅")
            
            # Create production object
            production_obj = doc.addObject("Part::Feature", "Complete_Rudder_Structure")
            production_obj.Shape = final_shape
            production_obj.ViewObject.ShapeColor = (0.6, 0.4, 0.8)  # Purple for production
            print(f"DEBUG: Created unified production object")
            
        except Exception as e:
            print(f"DEBUG: Sequential fusion failed: {e}")
    else:
        print(f"DEBUG: DEVELOPMENT MODE - Skipping fusion (set FUSE_FOR_PRODUCTION=True when ready)")
        print(f"       Separate objects allow faster iteration during development")
    
else:
    print("DEBUG: No plates found")

print(f"   Original shell volume: {original_volume/1000:.1f} cm³")
print(f"   Plates volume: {plates_volume/1000:.1f} cm³")
if rim_volume > 0:
    print(f"   Rim volume: {rim_volume/1000:.1f} cm³")
print(f"   Total structure volume: {(original_volume + plates_volume + rim_volume)/1000:.1f} cm³")

doc.recompute()
FreeCADGui.ActiveDocument.ActiveView.fitAll()

print("\n" + "="*60)
print("COMPLETE")
print("="*60)
print("Created separate objects:")
print("- Shell_Only: Shell without plates (semi-transparent blue)")
print("- Horizontal_Plate_1, 2, 3: Three solid plates (green)")
if rim_volume > 0:
    print("- Centerline_Rim: Vertical rim at Y=0 (red)")
print("="*60)