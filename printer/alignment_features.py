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
    Create solid support cylinders with holes for dowel alignment.
    SIMPLIFIED VERSION - Just one test cylinder at origin
    """
    
    print(f"      Creating single test alignment feature at origin")
    
    # Create ONE support cylinder at origin pointing in X direction
    support_cyl = Part.makeCylinder(
        support_diameter / 2,  # 5mm radius
        hole_depth,            # 25mm length
        Vector(0, 0, 0),       # At origin
        Vector(1, 0, 0)        # Pointing in +X direction
    )
    
    # Create the hole cylinder (slightly longer and offset for clean cut)
    hole_cyl = Part.makeCylinder(
        hole_diameter / 2,     # 3mm radius
        hole_depth + 2,        # 27mm length
        Vector(-1, 0, 0),      # Start 1mm before origin
        Vector(1, 0, 0)        # Pointing in +X direction
    )
    
    # Add support to piece
    result_shape = piece_shape.fuse(support_cyl)
    
    # Drill the hole
    result_shape = result_shape.cut(hole_cyl)
    
    print(f"      ✅ Added single test alignment feature at (0,0,0)")
    
    return result_shape


def visualize_alignment_features(doc, piece_shape, cut_plane, cut_position,
                                hole_diameter=6, support_diameter=10, 
                                hole_depth=25, edge_distance=20):
    """
    Create visible cylinder objects for testing/visualization.
    """
    return []