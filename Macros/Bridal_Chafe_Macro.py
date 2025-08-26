# FreeCAD Macro for 1x19 Wire Rope Model
# Version 7.0 - Refactored with function and parameters

import FreeCAD
import Part
from FreeCAD import Base

def create_wire_rope_1x19(
    length,                  # Length of rope to model (mm)
    overall_diameter,        # Total rope diameter (mm)
    wire_diameter,          # Individual wire diameter (mm)
    num_outer_wires=12,     # Number of outer spiral wires (default 12 for 1x19)
    spacing=0.2             # Gap between wire wraps (mm)
):
    """
    Create a 1x19 wire rope model for use as cutting tool in chafe protector.
    
    1x19 Construction breakdown:
    - 1 center wire (straight)
    - 6 inner layer wires (not modeled)
    - 12 outer layer wires (these create the spiral we model)
    - Total: 19 wires
    
    We only model the outer 12 wires as they create the visible spiral pattern
    that will form the groove in our chafe protector.
    
    Parameters:
    - length: Length of wire rope to model in mm
    - overall_diameter: Total diameter of the wire rope in mm  
    - wire_diameter: Diameter of individual outer wires in mm
    - num_outer_wires: Number of outer spiral wires (default 12 for 1x19)
    - spacing: Gap between adjacent wire wraps in mm (default 0.2)
    
    Returns: Fused solid of all outer wire strands
    """
    
    # Calculate derived parameters
    # Inner core diameter for 1x19 is typically 2/3 of overall diameter
    core_diameter = overall_diameter * (2/3)  # Approximately 4mm for 6mm rope
    core_radius = core_diameter / 2
    
    # Helix radius: from rope center to center of outer wire
    # This is core radius plus half the wire diameter
    helix_radius = core_radius + (wire_diameter / 2)
    
    # Vertical spacing between strands
    strand_spacing = wire_diameter + spacing
    
    # Pitch: distance for one complete spiral revolution
    # All outer wires complete one turn, spaced vertically
    helix_pitch = num_outer_wires * strand_spacing
    
    print(f"Creating 1x19 wire rope model:")
    print(f"  Core diameter: {core_diameter:.2f}mm")
    print(f"  Helix radius: {helix_radius:.2f}mm")
    print(f"  Helix pitch: {helix_pitch:.2f}mm")
    print(f"  Strand spacing: {strand_spacing:.2f}mm")
    
    # Create the first wire strand
    # Create the helix path
    helix_path = Part.makeHelix(
        helix_pitch,         # pitch
        length,              # height  
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
    
    # Create all strands by copying and translating
    all_strands = [first_strand]
    
    for i in range(1, num_outer_wires):
        # Copy the first strand
        strand_copy = first_strand.copy()
        
        # Move it up by the calculated strand spacing
        z_offset = i * strand_spacing
        strand_copy.translate(Base.Vector(0, 0, z_offset))
        
        all_strands.append(strand_copy)
        print(f"  Created strand {i} at z={z_offset:.2f}mm")
    
    # Fuse all strands together into single solid
    print("Fusing all strands into single solid...")
    wire_rope = all_strands[0]
    for strand in all_strands[1:]:
        wire_rope = wire_rope.fuse(strand)
    
    print(f"Wire rope model created successfully")
    return wire_rope

# ============================================
# Main execution
# ============================================

if __name__ == "__main__":
    # Clear existing document or create new
    doc = FreeCAD.newDocument("WireRope")
    
    # Call function with our default parameters
    wire_rope = create_wire_rope_1x19(
        length=250.0,           # 250mm length
        overall_diameter=6.0,   # 6mm total diameter
        wire_diameter=1.0,      # 1mm individual wire
        num_outer_wires=12,     # 12 outer wires (standard for 1x19)
        spacing=0.2            # 0.2mm gap between wraps
    )
    
    # Display the result
    rope_object = doc.addObject("Part::Feature", "WireRope_1x19")
    rope_object.Shape = wire_rope
    
    # Recompute and fit view
    doc.recompute()
    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    
    print("\nModel complete and displayed")