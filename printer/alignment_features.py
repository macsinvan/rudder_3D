"""
Alignment features module for Demo Model Generator
Creates supported dowel holes for piece alignment
"""
import Part
from FreeCAD import Vector, Base


def create_supported_alignment_holes(piece_shape, cut_plane, cut_position, 
                                    hole_diameter=6, support_diameter=10, 
                                    hole_depth=25, edge_distance=20):
    """
    Create hollow support cylinders with holes for dowel alignment.
    SIMPLIFIED VERSION - Just one test hollow cylinder at origin
    """
    
    print(f"      Creating single test hollow alignment feature at origin")
    
    # Parameters for hollow structure
    wall_thickness = 1.2  # mm - typical for 3 wall lines at 0.4mm nozzle
    position = Vector(0, 0, 0)  # At origin for testing
    direction = Vector(1, 0, 0)  # Pointing in +X direction
    
    # Create outer cylinder
    outer_cyl = Part.makeCylinder(
        support_diameter / 2,  # 5mm radius
        hole_depth,            # 25mm length
        position,
        direction
    )
    
    # Create middle hollow to make outer wall
    middle_hollow = Part.makeCylinder(
        (support_diameter / 2) - wall_thickness,  # 3.8mm radius
        hole_depth + 1,  # Slightly longer for clean cut
        position - direction * 0.5,
        direction
    )
    
    # Create outer wall by subtracting middle from outer
    outer_wall = outer_cyl.cut(middle_hollow)
    
    # Create inner support ring around dowel hole
    inner_support = Part.makeCylinder(
        (hole_diameter / 2) + wall_thickness,  # 4.2mm radius
        hole_depth,
        position,
        direction
    )
    
    # Create the dowel hole
    dowel_hole = Part.makeCylinder(
        hole_diameter / 2,  # 3mm radius
        hole_depth + 1,  # Slightly longer for clean cut
        position - direction * 0.5,
        direction
    )
    
    # Cut dowel hole from inner support
    inner_ring = inner_support.cut(dowel_hole)
    
    # Combine outer wall and inner ring
    hollow_support = outer_wall.fuse(inner_ring)
    
    # Optional: Add connecting ribs between inner and outer walls
    # This provides structural support while keeping it mostly hollow
    for angle in [0, 90, 180, 270]:
        rib_width = 1.0  # mm
        rib_height = support_diameter / 2  # Full radius
        rib_length = hole_depth
        
        # Create a thin box as a rib
        rib = Part.makeBox(
            rib_length,
            rib_width,
            rib_height,
            Vector(0, -rib_width/2, 0)
        )
        
        # Rotate around X axis
        import math
        rib_matrix = Base.Matrix()
        rib_matrix.rotateX(math.radians(angle))
        rib = rib.transformGeometry(rib_matrix)
        
        # Add to structure
        hollow_support = hollow_support.fuse(rib)
    
    # Cut the final dowel hole again to ensure it's clean
    hollow_support = hollow_support.cut(dowel_hole)
    
    # Add hollow support to piece
    result_shape = piece_shape.fuse(hollow_support)
    
    print(f"      ✅ Added hollow alignment feature at (0,0,0)")
    print(f"      Structure: {wall_thickness}mm walls, {hole_diameter}mm center hole")
    
    return result_shape


def visualize_alignment_features(doc, piece_shape, cut_plane, cut_position,
                                hole_diameter=6, support_diameter=10, 
                                hole_depth=25, edge_distance=20):
    """
    Create visible cylinder objects for testing/visualization.
    """
    return []