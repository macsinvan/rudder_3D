# FreeCAD Macro for Multi-strand Wire Rope - Copy and translate approach
# Version 6.0 - Copy single good wire and stack

import FreeCAD
import Part
from FreeCAD import Base

# Clear existing document or create new
doc = FreeCAD.newDocument("WireRope")

# ============================================
# PARAMETERS - Based on 1x19 6mm wire rope construction
# ============================================

# Wire rope specifications (1x19 construction, 6mm overall diameter)
# 1x19 = 1 center wire + 6 inner layer + 12 outer layer = 19 total wires
# From product data: inner core is 4mm, total is 6mm

# Geometry calculation for 1x19 6mm wire:
# - Inner core diameter: 4mm (contains center + 6 inner wires)
# - Outer layer space: 6mm - 4mm = 2mm total (1mm per side)
# - Therefore outer wire diameter ≈ 1mm
# - Gap between adjacent wraps: 0.2mm (from product specification)

# Calculate helix parameters:
# - Core radius: 4mm / 2 = 2mm
# - Outer wire radius: 1mm / 2 = 0.5mm  
# - Helix radius (center of rope to center of outer wire): 2mm + 0.5mm = 2.5mm
# - Vertical spacing per wire: 1mm + 0.2mm gap = 1.2mm
# - Pitch (12 wires complete one revolution): 12 × 1.2mm = 14.4mm

wire_diameter = 1.0          # Individual outer wire diameter
helix_radius = 2.5          # Radius to center of outer wires
helix_pitch = 14.4          # One complete revolution of the spiral
rope_length = 250.0         # Full length for final version
num_strands = 12            # Number of outer wires in 1x19 construction
strand_spacing = 1.2        # Vertical spacing (wire + gap)

# ============================================
# Create the first wire strand (the good one)
# ============================================

# Create the helix path
helix_path = Part.makeHelix(
    helix_pitch,         # pitch
    rope_length,         # height  
    helix_radius         # radius
)

# Get the start point of the helix
start_point = helix_path.Vertexes[0].Point

# For a helix starting at radius on X axis, the tangent points in Y direction
tangent_vector = Base.Vector(0, 1, 0)  # Initial tangent direction for helix

# Create circle perpendicular to the helix tangent
circle = Part.makeCircle(
    wire_diameter / 2,      # radius
    start_point,            # center
    tangent_vector          # normal vector (perpendicular to profile)
)

# Convert to wire
circle_wire = Part.Wire([circle])

# Create the sweep using makePipeShell
path_wire = Part.Wire(helix_path)
first_strand = path_wire.makePipeShell(
    [circle_wire],    # list of profiles
    True,             # makeSolid
    True              # isFrenet
)

# ============================================
# Copy and stack the strands
# ============================================

all_strands = [first_strand]
print(f"Starting with strand 0 at z=0")

for i in range(1, num_strands + 2):
    # Copy the first strand
    strand_copy = first_strand.copy()
    
    # Move it up by the calculated strand spacing
    z_offset = i * strand_spacing  # Use 1.2mm spacing (wire + gap)
    strand_copy.translate(Base.Vector(0, 0, z_offset))
    
    all_strands.append(strand_copy)
    print(f"Created strand {i} at z={z_offset:.2f}mm")

print(f"Total strands created: {len(all_strands)}")

# ============================================
# Display each strand separately (no fusion)
# ============================================

# Create separate FreeCAD objects for each strand
for i, strand in enumerate(all_strands):
    strand_object = doc.addObject("Part::Feature", f"Strand_{i}")
    strand_object.Shape = strand
    


# Recompute and fit view
doc.recompute()
FreeCADGui.ActiveDocument.ActiveView.fitAll()

print(f"Wire rope created with {num_strands} strands")
print(f"Based on 1x19 6mm stainless steel wire rope:")
print(f"  Individual wire diameter: {wire_diameter}mm")
print(f"  Helix radius: {helix_radius}mm")  
print(f"  Helix pitch: {helix_pitch}mm")
print(f"  Strand spacing: {strand_spacing}mm (includes 0.2mm gap)")
print(f"  Rope length: {rope_length}mm")
print(f"  Total spiral height coverage: {(num_strands-1)*strand_spacing:.1f}mm")