"""
FreeCAD Script: Cap - Simplified Single-Part Design
Sphere diameter = 2.25 × Line diameter
Compression ring = cutout (one part)
3.5° taper angle, ring length = sphere diameter/2
"""

import FreeCAD as App
import Part
import math

# ============================================================================
# PARAMETERS - Simplified!
# ============================================================================

# Primary design parameters
LINE_DIA = 12.0                    # Line diameter (mm)
SPHERE_RATIO = 2.25                # Sphere = 2.25 × Line diameter
TAPER_ANGLE = 3.5                  # Taper angle in degrees (CHANGED from 2.5°)

# Calculated dimensions
SPHERE_OUTER_DIA = LINE_DIA * SPHERE_RATIO      # 27.0mm
FERRULE_LENGTH = SPHERE_OUTER_DIA / 2.0         # 13.5mm (CHANGED: sphere diameter/2)
HOLE_DIA = LINE_DIA + 0.5                       # 12.5mm (clearance for line)

# Taper calculation
taper_rad = math.radians(TAPER_ANGLE)
radius_increase = FERRULE_LENGTH * math.tan(taper_rad)    # 0.825mm

# Ring dimensions (starts at line diameter, tapers outward)
RING_NARROW_DIA = LINE_DIA                                # 12.0mm (CHANGED: starts at line dia)
RING_WIDE_DIA = LINE_DIA + (2 * radius_increase)         # 13.65mm

# Visualization
LINE_LENGTH = 100.0                # Length of line to show

# ============================================================================
# CREATE COMPONENTS
# ============================================================================

def create_line():
    """Create the mooring line as a cylinder"""
    print(f"Creating line: {LINE_DIA}mm diameter")
    
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("CapSimplified")
    
    # Line extends above and below sphere
    line_start = App.Vector(0, 0, -LINE_LENGTH/2)
    line_direction = App.Vector(0, 0, 1)
    
    line_cylinder = Part.makeCylinder(
        LINE_DIA / 2.0,      # radius
        LINE_LENGTH,         # height
        line_start,          # base point
        line_direction       # direction
    )
    
    line_obj = doc.addObject("Part::Feature", "Line")
    line_obj.Shape = line_cylinder
    line_obj.ViewObject.ShapeColor = (0.6, 0.4, 0.2)  # Brown (rope color)
    
    return line_obj


def create_sphere_with_tapered_recess():
    """Create SOLID sphere with tapered recess matching compression ring"""
    print(f"Creating sphere: {SPHERE_OUTER_DIA:.1f}mm diameter ({SPHERE_RATIO}× line)")
    
    doc = App.ActiveDocument
    
    # Solid sphere
    solid_sphere = Part.makeSphere(SPHERE_OUTER_DIA / 2.0)
    
    # TOP HOLE - straight cylinder from center upward
    top_hole_height = SPHERE_OUTER_DIA / 2.0 + 5  # Extend above sphere
    top_hole = Part.makeCylinder(
        HOLE_DIA / 2.0,
        top_hole_height,
        App.Vector(0, 0, 0),  # Start at center
        App.Vector(0, 0, 1)   # Upward
    )
    
    # BOTTOM HOLE - tapered cone (EXACT MATCH to compression ring)
    bottom_hole_cone = Part.makeCone(
        RING_NARROW_DIA / 2.0,  # radius at top (Z=0) = 6.0mm (line radius)
        RING_WIDE_DIA / 2.0,    # radius at bottom = 6.825mm
        FERRULE_LENGTH,         # height = 13.5mm (sphere dia/2)
        App.Vector(0, 0, 0),    # Start at z=0 (center of sphere)
        App.Vector(0, 0, -1)    # Direction: downward
    )
    
    # Cut both holes from SOLID sphere
    sphere_with_holes = solid_sphere.cut(top_hole).cut(bottom_hole_cone)
    
    # Create sphere object
    sphere_obj = doc.addObject("Part::Feature", "Sphere")
    sphere_obj.Shape = sphere_with_holes
    sphere_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red
    sphere_obj.ViewObject.Transparency = 30
    
    print(f"  Diameter: {SPHERE_OUTER_DIA:.1f}mm (solid)")
    print(f"  Top hole: {HOLE_DIA}mm straight")
    print(f"  Bottom cutout: {RING_NARROW_DIA:.2f}mm → {RING_WIDE_DIA:.2f}mm")
    print(f"  Cutout depth: {FERRULE_LENGTH:.1f}mm (sphere dia/2)")
    print(f"  Taper: {TAPER_ANGLE}°")
    
    return sphere_obj


def create_compression_ring():
    """Create compression ring - starts at line diameter, tapers outward"""
    print(f"Creating compression ring: {FERRULE_LENGTH:.1f}mm long")
    
    doc = App.ActiveDocument
    
    # Tapered cone - starts at line diameter
    ring_cone = Part.makeCone(
        RING_NARROW_DIA / 2.0,    # radius at top (Z=0) = 6.0mm
        RING_WIDE_DIA / 2.0,      # radius at bottom = 6.825mm
        FERRULE_LENGTH,           # height = 13.5mm
        App.Vector(0, 0, 0),      # Start at z=0
        App.Vector(0, 0, -1)      # Direction: downward
    )
    
    # Cut with line cylinder to make hollow
    line_cutter = Part.makeCylinder(
        LINE_DIA / 2.0,           # radius = 6mm (12mm diameter line)
        FERRULE_LENGTH + 1,       # slightly longer to ensure clean cut
        App.Vector(0, 0, 0.5),    # Start slightly above
        App.Vector(0, 0, -1)      # Downward
    )
    
    # Subtract line from ring = hollow compression ring
    hollow_ring = ring_cone.cut(line_cutter)
    
    ring_obj = doc.addObject("Part::Feature", "CompressionRing")
    ring_obj.Shape = hollow_ring
    ring_obj.ViewObject.ShapeColor = (0.7, 0.7, 0.7)  # Gray
    ring_obj.ViewObject.Transparency = 40
    
    print(f"  Outer: {RING_NARROW_DIA:.2f}mm → {RING_WIDE_DIA:.2f}mm")
    print(f"  Inner: {LINE_DIA}mm")
    print(f"  Length: {FERRULE_LENGTH:.1f}mm")
    print(f"  Starts at: Z=0 (line diameter)")
    print(f"  Taper: {TAPER_ANGLE}°")
    
    return ring_obj


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("CAP - SIMPLIFIED SINGLE-PART DESIGN")
    print("=" * 70)
    print(f"\nDesign Parameters:")
    print(f"  Line diameter: {LINE_DIA}mm")
    print(f"  Sphere ratio: {SPHERE_RATIO}× line diameter")
    print(f"  Taper angle: {TAPER_ANGLE}°")
    print(f"  Ring length: sphere diameter/2")
    print()
    print(f"Calculated Dimensions:")
    print(f"  Sphere diameter: {SPHERE_OUTER_DIA:.1f}mm")
    print(f"  Ring length: {FERRULE_LENGTH:.1f}mm")
    print(f"  Hole diameter: {HOLE_DIA}mm")
    print(f"  Radius increase: {radius_increase:.3f}mm")
    print(f"  Ring: {RING_NARROW_DIA:.2f}mm → {RING_WIDE_DIA:.2f}mm")
    print()
    
    # Create components
    line = create_line()
    sphere = create_sphere_with_tapered_recess()
    ring = create_compression_ring()
    
    print("\nComponents created:")
    print("  1. Line (brown) - 12mm mooring line")
    print("  2. Sphere (red, semi-transparent) - 27mm solid sphere")
    print("  3. CompressionRing (gray, semi-transparent) - 13.5mm long")
    print()
    print("Simplified! Ring starts at line diameter, length = sphere dia/2")
    print()
    
    App.ActiveDocument.recompute()
    if App.GuiUp:
        import FreeCADGui
        FreeCADGui.SendMsgToActiveView("ViewFit")


# Run
if __name__ == '__main__':
    main()