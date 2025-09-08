# FreeCAD Macro for 12 Individual Wires
# Testing 100mm pitch with 12 separate wires

import FreeCAD
import Part
from FreeCAD import Base
import math

def create_wire_rope_cutting_tool(length, overall_diameter, wire_diameter, helix_pitch, num_wires, core_diameter):
    """
    Create a wire rope cutting tool with specified parameters.
    
    Parameters:
    - length: Length of wire rope in mm
    - overall_diameter: Total diameter of the wire rope in mm
    - wire_diameter: Diameter of individual wires in mm
    - helix_pitch: Pitch of the helix in mm
    - num_wires: Number of outer wires
    - core_diameter: Diameter of the solid core cylinder in mm
    
    Returns: doc - The FreeCAD document with all created objects
    """
    
    # Calculate helix radius (distance from center to wire center)
    core_radius_calc = (overall_diameter * (2/3)) / 2
    helix_radius = core_radius_calc + (wire_diameter / 2)
    
    # Angular spacing between wires
    angular_spacing = 360.0 / num_wires  # degrees
    
    # Vertical offset between adjacent wires
    vertical_offset = helix_pitch / num_wires
    
    print(f"Creating {num_wires} wires:")
    print(f"  Helix radius: {helix_radius:.2f}mm")
    print(f"  Helix pitch: {helix_pitch:.2f}mm")
    print(f"  Wire diameter: {wire_diameter}mm")
    print(f"  Angular spacing: {angular_spacing:.1f} degrees")
    print(f"  Vertical offset: {vertical_offset:.2f}mm")
    
    # Create document
    doc = FreeCAD.newDocument("WireRope_12Wires")
    
    # Create the first wire as reference
    helix_path = Part.makeHelix(
        helix_pitch,         # pitch
        length,              # height  
        helix_radius         # radius
    )
    
    # Get the start point
    start_point = helix_path.Vertexes[0].Point
    
    # Initial tangent
    tangent_z = helix_pitch / (2 * math.pi * helix_radius)
    tangent_vector = Base.Vector(0, 1, tangent_z).normalize()
    
    # Create circle profile
    circle = Part.makeCircle(
        wire_diameter / 2,   # radius
        start_point,         # center
        tangent_vector       # normal vector
    )
    
    # Convert to wire
    circle_wire = Part.Wire([circle])
    
    # Create the first sweep
    path_wire = Part.Wire(helix_path)
    first_strand = path_wire.makePipeShell(
        [circle_wire],    # profiles
        True,             # makeSolid
        True              # isFrenet
    )
    
    # Add first wire
    wire_object = doc.addObject("Part::Feature", "Wire_00")
    wire_object.Shape = first_strand
    
    print(f"  Created wire 0 at angle 0.0°")
    
    # Create remaining wires by just translating vertically
    for i in range(1, num_wires):
        # Copy the first strand
        wire_copy = first_strand.copy()
        
        # Only translate vertically to stagger the wires
        # The vertical offset creates the angular distribution naturally
        z_offset = i * vertical_offset
        wire_copy.translate(Base.Vector(0, 0, z_offset))
        
        # Add to document as separate object
        wire_object = doc.addObject("Part::Feature", f"Wire_{i:02d}")
        wire_object.Shape = wire_copy
        
        print(f"  Created wire {i} at z-offset {z_offset:.2f}mm")
    
    # Create center core cylinder
    core_cylinder = Part.makeCylinder(
        core_diameter / 2,         # radius
        length,                     # height
        Base.Vector(0, 0, 0),      # position
        Base.Vector(0, 0, 1)       # direction
    )
    
    # Add core cylinder to document
    core_object = doc.addObject("Part::Feature", "Core_Cylinder")
    core_object.Shape = core_cylinder
    
    print(f"  Created {core_diameter}mm core cylinder")
    
    # Fuse all parts into a single cutting tool
    print(f"\nFusing all parts into single cutting tool...")
    
    # Start fusion with the core cylinder
    cutting_tool = core_cylinder.copy()
    
    # Get all wire shapes from the document objects
    for i in range(num_wires):
        wire_name = f"Wire_{i:02d}"
        wire_obj = doc.getObject(wire_name)
        if wire_obj:
            cutting_tool = cutting_tool.fuse(wire_obj.Shape)
        
    # Add the fused cutting tool to document
    cutting_tool_object = doc.addObject("Part::Feature", "CuttingTool_Complete")
    cutting_tool_object.Shape = cutting_tool
    
    print(f"  Created fused cutting tool with {num_wires} wires")
    
    doc.recompute()
    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    
    print(f"\n{num_wires} separate wires + core cylinder created")
    print(f"Fused cutting tool created as 'CuttingTool_Complete'")
    
    return doc

# Main execution
if __name__ == "__main__":
    # Call function with hardcoded values
    doc = create_wire_rope_cutting_tool(
        length=250.0,           # Length of wire (mm)
        overall_diameter=6.0,   # Total rope diameter (mm)
        wire_diameter=1.0,      # Individual wire diameter (mm)
        helix_pitch=100.0,      # 100mm pitch
        num_wires=12,           # Number of wires
        core_diameter=5.0       # Core cylinder diameter (mm)
    )