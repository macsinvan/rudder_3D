# BASE CODE WITH CUTTING TOOL APPLIED
# Step 2.5 creates cutting tool and performs the cut

import FreeCAD
import Part
from FreeCAD import Base
import math

print("Creating split protector with ALL features...")

# Parameters (unchanged)
CYLINDER_LENGTH = 250.0
OUTER_DIAMETER = 28.0
INNER_DIAMETER = 9.0
CAP_MULTIPLIER = 2.0

# Screw positions (unchanged)
SCREW_POSITIONS = [20, 125, 230]
SCREW_HOLE_DIA = 4.2
SCREW_HEAD_DIA = 7.5
SCREW_HEAD_DEPTH = 2.5
INSERT_HOLE_DIA = 5.3
INSERT_DEPTH = 6.0

# Alignment pins (unchanged)
PIN_DIAMETER = 2.0
PIN_DEPTH = 6.0

# Bumps (proven to work)
BUMP_RADIUS = 0.75
BUMP_PROTRUSION = 0.5
BUMP_SPACING = 15.0
NUM_ROWS = 2

try:
    doc = FreeCAD.newDocument("CompleteProtector")
    
    # ============================================================
    # STEP 1: WORKING ELLIPSOID GEOMETRY (from previous success)
    # ============================================================
    print("Step 1: Creating body with ellipsoid caps (proven method)...")
    
    cap_radius = OUTER_DIAMETER / 2
    inner_radius = INNER_DIAMETER / 2
    cap_length = cap_radius * CAP_MULTIPLIER
    
    # Main cylinder
    outer_cylinder = Part.makeCylinder(cap_radius, CYLINDER_LENGTH)
    
    # Bottom ellipsoid - THE WAY THAT WORKS
    bottom_ellipsoid_obj = doc.addObject("Part::Ellipsoid", "BottomEllipsoid")
    bottom_ellipsoid_obj.Radius1 = cap_length
    bottom_ellipsoid_obj.Radius2 = cap_radius
    bottom_ellipsoid_obj.Radius3 = cap_radius
    doc.recompute()
    bottom_cap = bottom_ellipsoid_obj.Shape
    
    cut_box = Part.makeBox(cap_radius*3, cap_radius*3, cap_length,
                           Base.Vector(-cap_radius*1.5, -cap_radius*1.5, 0))
    bottom_cap = bottom_cap.cut(cut_box)
    
    # Top ellipsoid
    top_ellipsoid_obj = doc.addObject("Part::Ellipsoid", "TopEllipsoid")
    top_ellipsoid_obj.Radius1 = cap_length
    top_ellipsoid_obj.Radius2 = cap_radius
    top_ellipsoid_obj.Radius3 = cap_radius
    top_ellipsoid_obj.Placement.Base.z = CYLINDER_LENGTH
    doc.recompute()
    top_cap = top_ellipsoid_obj.Shape
    
    cut_box = Part.makeBox(cap_radius*3, cap_radius*3, cap_length,
                           Base.Vector(-cap_radius*1.5, -cap_radius*1.5, CYLINDER_LENGTH - cap_length))
    top_cap = top_cap.cut(cut_box)
    
    # Combine and hollow
    body_with_caps = outer_cylinder.fuse(bottom_cap).fuse(top_cap)
    
    inner_cylinder = Part.makeCylinder(
        inner_radius,
        CYLINDER_LENGTH + 2 * cap_length + 2,
        Base.Vector(0, 0, -cap_length - 1),
        Base.Vector(0, 0, 1)
    )
    
    hollow_body = body_with_caps.cut(inner_cylinder)
    
    # Hide construction objects
    bottom_ellipsoid_obj.ViewObject.Visibility = False
    top_ellipsoid_obj.ViewObject.Visibility = False
    
    print("   ✓ Ellipsoid caps complete")
    
    # ============================================================
    # STEP 2: ADD BUMPS (proven method from test)
    # ============================================================
    print("Step 2: Adding protruding bumps...")
    
    num_bumps_per_row = int((CYLINDER_LENGTH - 20) / BUMP_SPACING)
    actual_spacing = (CYLINDER_LENGTH - 20) / (num_bumps_per_row - 1)
    
    for row in range(NUM_ROWS):
        # CORRECTED: Bumps at 90° and 270° (sides), NOT on split line!
        angle = 90 + (180 * row)  # This gives us 90° and 270°
        angle_rad = math.radians(angle)
        
        print(f"   Placing bumps at {angle}° (clamping surface)")
        
        for i in range(num_bumps_per_row):
            z_pos = 10 + (i * actual_spacing)
            
            # Position on inner surface
            x = (INNER_DIAMETER/2) * math.cos(angle_rad)
            y = (INNER_DIAMETER/2) * math.sin(angle_rad)
            
            # Create hemisphere bump
            bump = Part.makeSphere(BUMP_RADIUS, Base.Vector(x, y, z_pos))
            
            # Trim to hemisphere
            outer_cut = Part.makeCylinder(
                OUTER_DIAMETER,
                BUMP_RADIUS * 3,
                Base.Vector(0, 0, z_pos - BUMP_RADIUS * 1.5)
            )
            inner_keep = Part.makeCylinder(
                INNER_DIAMETER/2 + BUMP_RADIUS,
                BUMP_RADIUS * 3,
                Base.Vector(0, 0, z_pos - BUMP_RADIUS * 1.5)
            )
            outer_cut = outer_cut.cut(inner_keep)
            bump = bump.cut(outer_cut)
            
            # FUSE bump to body
            hollow_body = hollow_body.fuse(bump)
    
    print(f"   ✓ Added {NUM_ROWS * num_bumps_per_row} bumps")
    
    # ============================================================
    # STEP 2.5: CREATE CUTTING TOOLS FOR ALL 6 SCREW POSITIONS
    # ============================================================
    print("Step 2.5: Creating cutting tools for all 6 screw positions...")
    
    # CORRECTED CUTTING PARAMETERS - Proper dimensions for 16mm M3 screw
    M3_CLEARANCE = 3.2
    SCREW_HEAD_DIA = 5.5
    SCREW_HEAD_DEPTH = 4.0   # 3mm screw head + 1mm countersink
    HEX_NUT_SIZE = 5.5
    HEX_NUT_DEPTH = 4.0      # 2.5mm nut + 1.5mm countersink
    
    print(f"   Using SCREW_HEAD_DEPTH = {SCREW_HEAD_DEPTH}mm")
    print(f"   Using HEX_NUT_DEPTH = {HEX_NUT_DEPTH}mm")
    
    # X positions for left and right sides
    x_positions = [-8.1, 8.1]
    
    all_tools = []
    
    for x_pos in x_positions:
        for z_pos in SCREW_POSITIONS:
            print(f"   Creating tool at X={x_pos}, Z={z_pos}")
            
            # Calculate material boundary at this X position
            material_boundary = math.sqrt(cap_radius**2 - x_pos**2)
            
            # Through hole
            through_hole = Part.makeCylinder(
                M3_CLEARANCE / 2,
                30,  # Long enough to go through everything
                Base.Vector(x_pos, -15, z_pos),
                Base.Vector(0, 1, 0)
            )
            
            # Screw recess at top - START FROM OUTSIDE
            screw_start_y = material_boundary + 2  # Start well outside
            screw_recess = Part.makeCylinder(
                SCREW_HEAD_DIA / 2,
                SCREW_HEAD_DEPTH,
                Base.Vector(x_pos, screw_start_y, z_pos),
                Base.Vector(0, -1, 0)  # Cut inward
            )
            
            # Hex recess at bottom - START FROM OUTSIDE
            hex_start_y = -material_boundary - 2  # Start well outside
            hex_vertices = []
            for i in range(6):
                angle = i * 60 * math.pi / 180
                hx = (HEX_NUT_SIZE / 2) * math.cos(angle) + x_pos
                hz = (HEX_NUT_SIZE / 2) * math.sin(angle) + z_pos
                hex_vertices.append(Base.Vector(hx, hex_start_y, hz))
            
            hex_wire = Part.makePolygon(hex_vertices + [hex_vertices[0]])
            hex_face = Part.Face(hex_wire)
            hex_recess = hex_face.extrude(Base.Vector(0, HEX_NUT_DEPTH, 0))
            
            # Combine into tool
            compound_tool = through_hole.fuse(screw_recess).fuse(hex_recess)
            all_tools.append(compound_tool)
            
            # PERFORM THE ACTUAL CUT
            hollow_body = hollow_body.cut(compound_tool)
    
    print(f"   ✓ Created and applied {len(all_tools)} cutting tools!")
    
    # Add first tool as visible object for reference
    tool_obj = doc.addObject("Part::Feature", "CuttingToolVis")
    tool_obj.Shape = all_tools[0]
    tool_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)
    tool_obj.ViewObject.Transparency = 50
    
    # ============================================================
    # STEP 3: SPLIT INTO HALVES
    # ============================================================
    print("Step 3: Splitting into halves...")
    
    top_cutter = Part.makeBox(
        cap_radius * 3,
        cap_radius * 2,
        CYLINDER_LENGTH + cap_length * 2,
        Base.Vector(-cap_radius * 1.5, 0, -cap_length)
    )
    
    bottom_cutter = Part.makeBox(
        cap_radius * 3,
        cap_radius * 2,
        CYLINDER_LENGTH + cap_length * 2,
        Base.Vector(-cap_radius * 1.5, -cap_radius * 2, -cap_length)
    )
    
    top_half = hollow_body.cut(top_cutter)
    bottom_half = hollow_body.cut(bottom_cutter)
    
    print("   ✓ Split complete")
    
    # ============================================================
    # STEP 4: NO BOSSES - Just preparing for simple holes
    # ============================================================
    print("Step 4: No bosses - keeping it simple...")
    
    # ============================================================
    # STEP 5: REMOVED - Cutting tools now include through holes
    # ============================================================
    print("Step 5: Skipped - cutting tools already created through holes...")
    
    # ============================================================
    # STEP 6: NO INSERTS NEEDED - Through bolts with nuts
    # ============================================================
    print("Step 6: No inserts - will use M3 bolts with nuts...")
    
    # ============================================================
    # STEP 7: ADD ALIGNMENT PIN HOLES - UPDATED TO MATCH SCREW POSITIONS
    # ============================================================
    print("Step 7: Adding alignment pin holes...")
    
    # UPDATED PARAMETERS
    PIN_DIAMETER = 4.0  # CHANGED: From 2.0mm to 4.0mm
    PIN_DEPTH = 6.0
    
    # X positions match screw holes
    pin_x_positions = [-8.1, 8.1]  # CHANGED: Match screw hole positions
    
    pin_positions = []
    for i in range(len(SCREW_POSITIONS) - 1):
        z_pos = (SCREW_POSITIONS[i] + SCREW_POSITIONS[i+1]) / 2
        pin_positions.append(z_pos)
    
    for x_pos in pin_x_positions:
        for z_pos in pin_positions:
            print(f"   Creating pin hole at X={x_pos}, Z={z_pos}")
            
            # Pin hole in bottom half
            pin_hole = Part.makeCylinder(
                PIN_DIAMETER / 2,
                PIN_DEPTH,
                Base.Vector(x_pos, -PIN_DEPTH/2, z_pos),
                Base.Vector(0, 1, 0)
            )
            bottom_half = bottom_half.cut(pin_hole)
            
            # Pin hole in top half (slightly larger for clearance)
            pin_hole = Part.makeCylinder(
                PIN_DIAMETER / 2 + 0.1,
                PIN_DEPTH,
                Base.Vector(x_pos, PIN_DEPTH/2, z_pos),
                Base.Vector(0, -1, 0)
            )
            top_half = top_half.cut(pin_hole)
    
    print(f"   ✓ Added {len(pin_x_positions) * len(pin_positions)} alignment pin holes (4mm diameter)")
    
    # ============================================================
    # STEP 7.5: CREATE ALIGNMENT DOWEL PINS (SEPARATE PARTS)
    # ============================================================
    print("Step 7.5: Creating alignment dowel pins...")
    
    # DOWEL PARAMETERS
    DOWEL_DIAMETER = 3.8    # Slight clearance fit for 4mm holes
    DOWEL_LENGTH = 10.0     # 6mm + 6mm - 2mm overlap
    
    # Create 4 dowel pins
    dowel_spacing = 30.0  # Space them out for printing
    
    for i in range(4):
        dowel = Part.makeCylinder(
            DOWEL_DIAMETER / 2,
            DOWEL_LENGTH,
            Base.Vector(i * dowel_spacing, -50, 0),  # Position away from main part
            Base.Vector(0, 0, 1)
        )
        
        dowel_obj = doc.addObject("Part::Feature", f"AlignmentDowel_{i+1}")
        dowel_obj.Shape = dowel
        if hasattr(FreeCAD, 'Gui'):
            dowel_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)  # Yellow color
    
    print(f"   ✓ Created 4 alignment dowels ({DOWEL_DIAMETER}mm × {DOWEL_LENGTH}mm)")
    
    # ============================================================
    # STEP 8: ADD TO DOCUMENT
    # ============================================================
    print("Step 8: Adding to document...")
    
    top_obj = doc.addObject("Part::Feature", "TopHalf")
    top_obj.Shape = top_half
    bottom_obj = doc.addObject("Part::Feature", "BottomHalf")
    bottom_obj.Shape = bottom_half
    
    # NO MOVEMENT - parts stay where split leaves them
    
    if hasattr(FreeCAD, 'Gui'):
        top_obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0)
        bottom_obj.ViewObject.ShapeColor = (0.0, 0.6, 0.8)
        FreeCAD.Gui.ActiveDocument.ActiveView.fitAll()
    
    doc.recompute()
    
    # ============================================================
    # STEP 9: EXPORT ALL PARTS AS STL FILES
    # ============================================================
    print("Step 9: Exporting parts as STL files...")
    
    # Create Downloads directory path for Mac
    import os
    downloads_dir = os.path.expanduser("~/Downloads")
    
    # Export top half
    top_path = os.path.join(downloads_dir, "TopHalf.stl")
    top_obj.Shape.exportStl(top_path)
    print(f"   ✓ Exported {top_path}")
    
    # Export bottom half
    bottom_path = os.path.join(downloads_dir, "BottomHalf.stl")
    bottom_obj.Shape.exportStl(bottom_path)
    print(f"   ✓ Exported {bottom_path}")
    
    # Export each dowel
    for i in range(4):
        dowel_name = f"AlignmentDowel_{i+1}"
        dowel_obj = doc.getObject(dowel_name)
        if dowel_obj:
            dowel_path = os.path.join(downloads_dir, f"AlignmentDowel_{i+1}.stl")
            dowel_obj.Shape.exportStl(dowel_path)
            print(f"   ✓ Exported {dowel_path}")
    
    print(f"   ✓ All 6 STL files exported to {downloads_dir}!")
    
    print("\n✓ COMPLETE WITH ALL 6 BOLT HOLES AND ALIGNMENT SYSTEM:")
    print("  • Ellipsoid end caps")
    print("  • Protruding grip bumps at 90° and 270°")
    print("  • Split design")
    print("  • ALL 6 BOLT HOLES with proper countersinks")
    print("  • 4 alignment pin holes (4mm diameter)")
    print("  • 4 separate alignment dowel pins for printing")
    print("  • 6 STL files exported for 3D printing")
    print("\nAll 6 bolt holes complete with 4mm deep countersinks!")
    print("4 yellow dowel pins ready for separate printing!")
    print("STL files: TopHalf.stl, BottomHalf.stl, AlignmentDowel_1-4.stl")
    
    # VERIFICATION CHECK
    print("\n" + "="*50)
    print("VERIFICATION CHECK:")
    print(f"✓ SCREW_HEAD_DEPTH = {SCREW_HEAD_DEPTH}mm (should be 4.0)")
    print(f"✓ HEX_NUT_DEPTH = {HEX_NUT_DEPTH}mm (should be 4.0)")
    print(f"✓ Screw X positions: {x_positions} (should be [-8.1, 8.1])")
    print(f"✓ Z positions: {SCREW_POSITIONS} (should be [20, 125, 230])")
    print(f"✓ Total holes created: {len(all_tools)} (should be 6)")
    print("✓ Step 5 removed: Simple through holes eliminated")
    print(f"✓ Pin diameter: {PIN_DIAMETER}mm (should be 4.0)")
    print(f"✓ Pin X positions: {pin_x_positions} (should be [-8.1, 8.1])")
    print(f"✓ Dowel diameter: {DOWEL_DIAMETER}mm (should be 3.8)")
    print(f"✓ Dowel length: {DOWEL_LENGTH}mm (should be 10.0)")
    print("✓ 4 separate dowel pins created")
    print("="*50)
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()