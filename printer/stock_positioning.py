"""
Stock positioning operations for Demo Model Generator
"""
import FreeCAD as App
from FreeCAD import Vector

def position_all_stock_components(stock_obj, stock_cutout_obj, 
                                 post_centre_x, post_top_z, 
                                 post_diameter, post_diameter_delta):
    """Rotate and position stock components."""
    
    # Create transformation matrix: rotate 180° then translate
    transform = App.Matrix()
    transform.rotateZ(3.14159)  # 180° rotation
    transform.move(Vector(post_centre_x, 0, post_top_z))
    
    # Apply to both objects
    stock_obj.Shape = stock_obj.Shape.transformGeometry(transform)
    stock_cutout_obj.Shape = stock_cutout_obj.Shape.transformGeometry(transform)
    
    print(f"✅ Stock components positioned at X={post_centre_x}, Z={post_top_z}")
    
    return {
        'stock': {'x': post_centre_x, 'z': post_top_z},
        'cutout': {'x': post_centre_x, 'z': post_top_z}
    }