"""
Stock positioning operations for Demo Model Generator
Handles rotation and positioning of stock and cutout relative to post location
"""
import FreeCAD as App
from FreeCAD import Vector, Base


def rotate_stock_180(stock_obj):
    """Rotate stock 180° around Z-axis to orient tangs toward trailing edge.
    
    Args:
        stock_obj: FreeCAD object containing the stock shape
    
    Returns:
        None (modifies object in place)
    """
    print(f"\n🔄 Rotating stock 180° to orient tangs correctly...")
    stock_matrix = App.Matrix()
    stock_matrix.rotateZ(3.14159)  # 180° in radians
    rotated_shape = stock_obj.Shape.transformGeometry(stock_matrix)
    stock_obj.Shape = rotated_shape
    print(f"   ✅ Stock rotated - tangs now point toward trailing edge")


def rotate_stock_cutout_180(stock_cutout_obj):
    """Rotate stock cutout 180° around Z-axis to orient tangs toward trailing edge.
    
    Args:
        stock_cutout_obj: FreeCAD object containing the stock cutout shape
    
    Returns:
        None (modifies object in place)
    """
    print(f"\n🔄 Rotating stock cutout 180° to orient tangs correctly...")
    stock_cutout_matrix = App.Matrix()
    stock_cutout_matrix.rotateZ(3.14159)  # 180° in radians
    rotated_cutout_shape = stock_cutout_obj.Shape.transformGeometry(stock_cutout_matrix)
    stock_cutout_obj.Shape = rotated_cutout_shape
    print(f"   ✅ Stock cutout rotated - tangs now point toward trailing edge")


def position_stock(stock_obj, post_centre_x, post_top_z, post_diameter):
    """Position the stock based on post location.
    
    Args:
        stock_obj: FreeCAD object containing the stock shape
        post_centre_x: Target X position for post centre in mm
        post_top_z: Target Z position for top of post in mm
        post_diameter: Diameter of the post in mm
    
    Returns:
        tuple: (final_post_centre_x, final_post_top_z) - actual positions achieved
    """
    print(f"\n📍 Positioning stock based on post location...")
    print(f"   Post centre target: X={post_centre_x}mm")
    print(f"   Post top target: Z={post_top_z}mm")
    print(f"   Post diameter: {post_diameter}mm")
    
    # Get current bounding box of stock
    current_bbox = stock_obj.Shape.BoundBox
    
    # Calculate post centre X position
    # Post is at the top of the box (max Z), post_diameter/2 in from the right edge (max X)
    current_post_centre_x = current_bbox.XMax - (post_diameter / 2)
    current_post_top_z = current_bbox.ZMax
    
    print(f"   Current post centre X: {current_post_centre_x:.1f}mm")
    print(f"   Current post top Z: {current_post_top_z:.1f}mm")
    
    # Calculate offset needed to move post to target position
    offset = Vector(
        post_centre_x - current_post_centre_x,  # Move post centre to specified X
        0,                                       # Keep Y unchanged
        post_top_z - current_post_top_z          # Move post top to specified Z
    )
    
    # Apply translation
    translation_matrix = App.Matrix()
    translation_matrix.move(offset)
    positioned_shape = stock_obj.Shape.transformGeometry(translation_matrix)
    stock_obj.Shape = positioned_shape
    
    # Report final position
    final_bbox = stock_obj.Shape.BoundBox
    final_post_centre_x = final_bbox.XMax - (post_diameter / 2)
    final_post_top_z = final_bbox.ZMax
    
    print(f"   ✅ Stock positioned:")
    print(f"      Post centre X: {final_post_centre_x:.1f}mm (target: {post_centre_x}mm)")
    print(f"      Post top Z: {final_post_top_z:.1f}mm (target: {post_top_z}mm)")
    
    return final_post_centre_x, final_post_top_z


def position_stock_cutout(stock_cutout_obj, post_centre_x, post_top_z, 
                         post_diameter, post_diameter_delta):
    """Position the stock cutout based on post location with adjusted diameter.
    
    Args:
        stock_cutout_obj: FreeCAD object containing the stock cutout shape
        post_centre_x: Target X position for post centre in mm
        post_top_z: Target Z position for top of post in mm
        post_diameter: Base diameter of the post in mm
        post_diameter_delta: Additional diameter for cutout clearance in mm
    
    Returns:
        tuple: (final_post_centre_x, final_post_top_z) - actual positions achieved
    """
    print(f"\n📍 Positioning stock cutout based on post location...")
    cutout_post_diameter = post_diameter + post_diameter_delta
    
    # Adjust target X to account for larger post radius
    cutout_target_x = post_centre_x  # Simplified - was doing unnecessary math
    print(f"   Post centre target: X={cutout_target_x}mm (adjusted for larger post)")
    print(f"   Post top target: Z={post_top_z}mm")
    print(f"   Post diameter for cutout: {cutout_post_diameter}mm")
    
    # Get current bounding box of stock cutout
    current_cutout_bbox = stock_cutout_obj.Shape.BoundBox
    
    # Calculate post centre X position for cutout
    current_cutout_post_centre_x = current_cutout_bbox.XMax - (cutout_post_diameter / 2)
    current_cutout_post_top_z = current_cutout_bbox.ZMax
    
    print(f"   Current cutout post centre X: {current_cutout_post_centre_x:.1f}mm")
    print(f"   Current cutout post top Z: {current_cutout_post_top_z:.1f}mm")
    
    # Calculate offset needed to move cutout post to target position
    cutout_offset = Vector(
        cutout_target_x - current_cutout_post_centre_x,  # Move post centre to target X
        0,                                                # Keep Y unchanged
        post_top_z - current_cutout_post_top_z           # Move post top to specified Z
    )
    
    # Apply translation to cutout
    cutout_translation_matrix = App.Matrix()
    cutout_translation_matrix.move(cutout_offset)
    positioned_cutout_shape = stock_cutout_obj.Shape.transformGeometry(cutout_translation_matrix)
    stock_cutout_obj.Shape = positioned_cutout_shape
    
    # Report final cutout position
    final_cutout_bbox = stock_cutout_obj.Shape.BoundBox
    final_cutout_post_centre_x = final_cutout_bbox.XMax - (cutout_post_diameter / 2)
    final_cutout_post_top_z = final_cutout_bbox.ZMax
    
    print(f"   ✅ Stock cutout positioned:")
    print(f"      Post centre X: {final_cutout_post_centre_x:.1f}mm (target: {cutout_target_x}mm)")
    print(f"      Post top Z: {final_cutout_post_top_z:.1f}mm (target: {post_top_z}mm)")
    
    return final_cutout_post_centre_x, final_cutout_post_top_z


def position_all_stock_components(stock_obj, stock_cutout_obj, 
                                 post_centre_x, post_top_z, 
                                 post_diameter, post_diameter_delta):
    """Complete positioning workflow for stock and cutout.
    
    Rotates both components 180° and positions them relative to post location.
    
    Args:
        stock_obj: FreeCAD object containing the stock shape
        stock_cutout_obj: FreeCAD object containing the stock cutout shape
        post_centre_x: Target X position for post centre in mm
        post_top_z: Target Z position for top of post in mm
        post_diameter: Base diameter of the post in mm
        post_diameter_delta: Additional diameter for cutout clearance in mm
    
    Returns:
        dict: Final positions for both stock and cutout
    """
    # Rotate both components
    rotate_stock_180(stock_obj)
    rotate_stock_cutout_180(stock_cutout_obj)
    
    # Position stock
    stock_x, stock_z = position_stock(stock_obj, post_centre_x, post_top_z, post_diameter)
    
    # Position cutout
    cutout_x, cutout_z = position_stock_cutout(
        stock_cutout_obj, post_centre_x, post_top_z, 
        post_diameter, post_diameter_delta
    )
    
    return {
        'stock': {'x': stock_x, 'z': stock_z},
        'cutout': {'x': cutout_x, 'z': cutout_z}
    }