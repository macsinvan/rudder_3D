"""
FreeCAD Script: Cap - WITH RATCHET MECHANISM
Compression ring with ratchet teeth on exterior, matching grooves in sphere
Like a cable tie - slides in easily, locks on pullback
"""

import FreeCAD as App
import Part
import math

# ============================================================================
# PARAMETERS
# ============================================================================

# Primary design parameters
LINE_DIA = 12.0                    # Line diameter (mm)
SPHERE_RATIO = 2.5                 # Sphere = 2.5 × Line diameter
TAPER_ANGLE = 3.5                  # Taper angle in degrees
GAP_WIDTH = 2.0                    # Gap width for compression (mm)
WALL_THICKNESS = 3.0               # Ring wall thickness (mm)

# Ridge parameters (inward ridges on interior)
RIDGE_HEIGHT = 1.0                 # Ridge protrusion height inward (mm)
RIDGE_SPACING = 3.0                # Ridge spacing along Z (mm)
RIDGE_WIDTH = 1.5                  # Base width of ridge (mm)

# Ratchet parameters (NEW - outward teeth on exterior)
RATCHET_TOOTH_HEIGHT = 0.75        # Tooth protrusion outward (mm)
RATCHET_TOOTH_SPACING = 2.5        # Distance between teeth (mm)
RATCHET_TOOTH_WIDTH = 2.0          # Width of tooth (mm)
RATCHET_RAMP_ANGLE = 30.0          # Shallow entry angle (degrees)
RATCHET_CATCH_ANGLE = 75.0         # Steep locking angle (degrees)

# Calculated dimensions
SPHERE_OUTER_DIA = LINE_DIA * SPHERE_RATIO      # 30.0mm
FERRULE_LENGTH = SPHERE_OUTER_DIA / 2.0         # 15.0mm
HOLE_DIA = LINE_DIA + 0.5                       # 12.5mm

# Taper calculation
taper_rad = math.radians(TAPER_ANGLE)
radius_increase_bottom = FERRULE_LENGTH * math.tan(taper_rad)
radius_decrease_top = FERRULE_LENGTH * math.tan(taper_rad)

# Ring dimensions
RING_NARROW_DIA = LINE_DIA + (2 * WALL_THICKNESS)
RING_WIDE_DIA = RING_NARROW_DIA + (2 * radius_increase_bottom)

# Top cutout narrows from Z=0 upward
TOP_CUTOUT_NARROW_DIA = RING_NARROW_DIA - (2 * radius_decrease_top)

# Visualization
LINE_LENGTH = 100.0

# ============================================================================
# CREATE COMPONENTS
# ============================================================================

def create_line():
    """Create the mooring line as a cylinder"""
    print(f"Creating line: {LINE_DIA}mm diameter")
    
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("CapRatchet")
    
    line_start = App.Vector(0, 0, -LINE_LENGTH/2)
    line_direction = App.Vector(0, 0, 1)
    
    line_cylinder = Part.makeCylinder(
        LINE_DIA / 2.0,
        LINE_LENGTH,
        line_start,
        line_direction
    )
    
    line_obj = doc.addObject("Part::Feature", "Line")
    line_obj.Shape = line_cylinder
    line_obj.ViewObject.ShapeColor = (0.6, 0.4, 0.2)
    
    return line_obj


def create_ratchet_tooth_ring(z_position, outer_radius):
    """Create a single ratchet tooth ring protruding OUTWARD - asymmetric sawtooth"""
    
    # Asymmetric triangle: shallow ramp down (easy entry), steep face up (locks)
    # Peak is 70% down from top = gentle ramp for insertion
    
    peak_offset = RATCHET_TOOTH_WIDTH * 0.7  # 70% down = gentle ramp
    
    # Base top (starting point)
    base_top = App.Vector(outer_radius, 0, z_position)
    # Peak protruding outward, 70% down
    peak = App.Vector(outer_radius + RATCHET_TOOTH_HEIGHT, 0, z_position - peak_offset)
    # Base bottom
    base_bottom = App.Vector(outer_radius, 0, z_position - RATCHET_TOOTH_WIDTH)
    
    # Create wire
    edge1 = Part.LineSegment(base_top, peak).toShape()
    edge2 = Part.LineSegment(peak, base_bottom).toShape()
    edge3 = Part.LineSegment(base_bottom, base_top).toShape()
    
    wire = Part.Wire([edge1, edge2, edge3])
    face = Part.Face(wire)
    
    # Revolve around Z-axis
    tooth_ring = face.revolve(
        App.Vector(0, 0, 0),
        App.Vector(0, 0, 1),
        360
    )
    
    return tooth_ring


def create_sphere_with_cutouts():
    """Create sphere with visible cutout cones AND ratchet grooves"""
    print(f"Creating sphere: {SPHERE_OUTER_DIA:.1f}mm diameter")
    
    doc = App.ActiveDocument
    
    # Solid sphere
    solid_sphere = Part.makeSphere(SPHERE_OUTER_DIA / 2.0)
    
    # TOP HOLE - small straight cylinder above apex
    top_hole = Part.makeCylinder(
        HOLE_DIA / 2.0,
        10,
        App.Vector(0, 0, FERRULE_LENGTH),
        App.Vector(0, 0, 1)
    )
    
    # BOTTOM CONE CUTOUT - widens going down
    bottom_cone_cutout = Part.makeCone(
        RING_NARROW_DIA / 2.0,
        RING_WIDE_DIA / 2.0,
        FERRULE_LENGTH,
        App.Vector(0, 0, 0),
        App.Vector(0, 0, -1)
    )
    
    # TOP CONE CUTOUT - narrows going up
    top_cone_cutout = Part.makeCone(
        TOP_CUTOUT_NARROW_DIA / 2.0,
        RING_NARROW_DIA / 2.0,
        FERRULE_LENGTH,
        App.Vector(0, 0, FERRULE_LENGTH),
        App.Vector(0, 0, -1)
    )
    
    # ADD RATCHET GROOVES to cone cutouts (NEW!)
    print(f"  Adding ratchet grooves to sphere interior...")
    num_teeth = int((2 * FERRULE_LENGTH) / RATCHET_TOOTH_SPACING)  # Full height
    
    ratchet_grooves = None
    for i in range(num_teeth):
        z_pos = FERRULE_LENGTH - (i * RATCHET_TOOTH_SPACING) - RATCHET_TOOTH_WIDTH/2
        
        # Calculate sphere interior radius at this Z position
        if z_pos >= 0:
            # Top cone region (narrows going up)
            t = z_pos / FERRULE_LENGTH
            sphere_radius = (RING_NARROW_DIA/2.0) + t * (TOP_CUTOUT_NARROW_DIA/2.0 - RING_NARROW_DIA/2.0)
        else:
            # Bottom cone region (widens going down)
            t = abs(z_pos) / FERRULE_LENGTH
            sphere_radius = (RING_NARROW_DIA/2.0) + t * (RING_WIDE_DIA/2.0 - RING_NARROW_DIA/2.0)
        
        # Create groove (tooth protruding inward into the cutout space)
        groove = create_ratchet_tooth_ring(z_pos, sphere_radius)
        
        if ratchet_grooves is None:
            ratchet_grooves = groove
        else:
            ratchet_grooves = ratchet_grooves.fuse(groove)
    
    # Subtract grooves from cones
    if ratchet_grooves:
        bottom_cone_cutout = bottom_cone_cutout.fuse(ratchet_grooves)
        top_cone_cutout = top_cone_cutout.fuse(ratchet_grooves)
    
    # Make cutters visible
    bottom_cone_obj = doc.addObject("Part::Feature", "BottomCone_Cutter")
    bottom_cone_obj.Shape = bottom_cone_cutout
    bottom_cone_obj.ViewObject.ShapeColor = (0.0, 1.0, 0.0)
    bottom_cone_obj.ViewObject.Transparency = 60
    
    top_cone_obj = doc.addObject("Part::Feature", "TopCone_Cutter")
    top_cone_obj.Shape = top_cone_cutout
    top_cone_obj.ViewObject.ShapeColor = (0.0, 0.0, 1.0)
    top_cone_obj.ViewObject.Transparency = 60
    
    # Cut sphere
    sphere_cut = solid_sphere.cut(top_hole).cut(bottom_cone_cutout).cut(top_cone_cutout)
    
    sphere_obj = doc.addObject("Part::Feature", "Sphere")
    sphere_obj.Shape = sphere_cut
    sphere_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
    sphere_obj.ViewObject.Transparency = 30
    
    print(f"  {num_teeth} ratchet grooves added to sphere interior")
    
    return sphere_obj, bottom_cone_obj, top_cone_obj


def create_ridge_ring(z_position):
    """Create a single ridge ring protruding INWARD (existing function)"""
    
    outer_radius = LINE_DIA / 2.0
    inner_radius = outer_radius - RIDGE_HEIGHT
    
    base_top = App.Vector(outer_radius, 0, z_position + RIDGE_WIDTH/2)
    peak = App.Vector(inner_radius, 0, z_position)
    base_bottom = App.Vector(outer_radius, 0, z_position - RIDGE_WIDTH/2)
    
    edge1 = Part.LineSegment(base_top, peak).toShape()
    edge2 = Part.LineSegment(peak, base_bottom).toShape()
    edge3 = Part.LineSegment(base_bottom, base_top).toShape()
    
    wire = Part.Wire([edge1, edge2, edge3])
    face = Part.Face(wire)
    
    ridge_ring = face.revolve(
        App.Vector(0, 0, 0),
        App.Vector(0, 0, 1),
        360
    )
    
    return ridge_ring


def create_compression_ring_with_ridges():
    """Create compression ring with inward ridges AND outward ratchet teeth"""
    print(f"Creating compression ring with ridges and ratchet teeth")
    
    doc = App.ActiveDocument
    
    # Outer tapered shell
    ring_cone = Part.makeCone(
        RING_NARROW_DIA / 2.0,
        RING_WIDE_DIA / 2.0,
        FERRULE_LENGTH,
        App.Vector(0, 0, 0),
        App.Vector(0, 0, -1)
    )
    
    # Hollow with line hole
    line_hole = Part.makeCylinder(
        LINE_DIA / 2.0,
        FERRULE_LENGTH + 2,
        App.Vector(0, 0, 1),
        App.Vector(0, 0, -1)
    )
    
    hollow_ring = ring_cone.cut(line_hole)
    
    # ADD INWARD RIDGES (existing)
    num_ridges = int(FERRULE_LENGTH / RIDGE_SPACING)
    print(f"  Adding {num_ridges} inward ridges ({RIDGE_HEIGHT}mm)...")
    
    ridges_combined = None
    for i in range(num_ridges):
        z_pos = -i * RIDGE_SPACING - RIDGE_SPACING/2
        if z_pos > -FERRULE_LENGTH:
            ridge = create_ridge_ring(z_pos)
            if ridges_combined is None:
                ridges_combined = ridge
            else:
                ridges_combined = ridges_combined.fuse(ridge)
    
    if ridges_combined:
        ring_with_ridges = hollow_ring.fuse(ridges_combined)
    else:
        ring_with_ridges = hollow_ring
    
    # ADD OUTWARD RATCHET TEETH (NEW!)
    num_teeth = int(FERRULE_LENGTH / RATCHET_TOOTH_SPACING)
    print(f"  Adding {num_teeth} ratchet teeth ({RATCHET_TOOTH_HEIGHT}mm outward)...")
    
    ratchet_teeth = None
    for i in range(num_teeth):
        z_pos = -i * RATCHET_TOOTH_SPACING - RATCHET_TOOTH_WIDTH/2
        if z_pos > -FERRULE_LENGTH:
            # Calculate ring outer radius at this Z position (tapered)
            t = abs(z_pos) / FERRULE_LENGTH
            ring_radius = (RING_NARROW_DIA/2.0) + t * (RING_WIDE_DIA/2.0 - RING_NARROW_DIA/2.0)
            
            tooth = create_ratchet_tooth_ring(z_pos, ring_radius)
            
            if ratchet_teeth is None:
                ratchet_teeth = tooth
            else:
                ratchet_teeth = ratchet_teeth.fuse(tooth)
    
    # Fuse ratchet teeth to ring
    if ratchet_teeth:
        ring_complete = ring_with_ridges.fuse(ratchet_teeth)
    else:
        ring_complete = ring_with_ridges
    
    # CREATE SPLIT with 2mm plate
    plate_size = RING_WIDE_DIA + 10
    
    cutting_plate = Part.makeBox(
        plate_size,
        GAP_WIDTH,
        FERRULE_LENGTH + 2
    )
    
    cutting_plate.translate(App.Vector(
        -plate_size/2,
        -GAP_WIDTH/2,
        -FERRULE_LENGTH - 1
    ))
    
    # Make plate visible
    plate_obj = doc.addObject("Part::Feature", "SplitPlate_Cutter")
    plate_obj.Shape = cutting_plate
    plate_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
    plate_obj.ViewObject.Transparency = 60
    
    # Cut gap
    split_ring = ring_complete.cut(cutting_plate)
    
    ring_obj = doc.addObject("Part::Feature", "CompressionRing")
    ring_obj.Shape = split_ring
    ring_obj.ViewObject.ShapeColor = (0.9, 0.9, 0.9)
    ring_obj.ViewObject.Transparency = 20
    
    print(f"  Ring complete: inward ridges + outward ratchet teeth + {GAP_WIDTH}mm split")
    
    return ring_obj, plate_obj


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("CAP - WITH RATCHET MECHANISM (Cable Tie Style)")
    print("=" * 70)
    print(f"\nParameters:")
    print(f"  Sphere: {SPHERE_OUTER_DIA:.1f}mm ({SPHERE_RATIO}× line)")
    print(f"  Inward ridges: {RIDGE_HEIGHT}mm")
    print(f"  Ratchet teeth: {RATCHET_TOOTH_HEIGHT}mm outward")
    print(f"  Gap: {GAP_WIDTH}mm")
    print()
    
    line = create_line()
    sphere, bottom_cone, top_cone = create_sphere_with_cutouts()
    ring, plate = create_compression_ring_with_ridges()
    
    print("\nComponents:")
    print("  1. Line (brown)")
    print("  2. Sphere (red) - with ratchet grooves in cutout")
    print("  3. BottomCone_Cutter (green) - with grooves")
    print("  4. TopCone_Cutter (blue) - with grooves")
    print("  5. CompressionRing (light gray) - inward ridges + outward ratchet")
    print("  6. SplitPlate_Cutter (yellow)")
    print()
    print("RATCHET ACTION: Slides in easily, locks on pullback!")
    print()
    
    App.ActiveDocument.recompute()
    if App.GuiUp:
        import FreeCADGui
        FreeCADGui.SendMsgToActiveView("ViewFit")


if __name__ == '__main__':
    main()