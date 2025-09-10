"""
Cutting operations for Demo Model Generator
Handles slicing of rudder halves into printable pieces
"""
import Part
from FreeCAD import Vector, Base


def create_cutting_plan(shape, half_name, print_max_size=310):
    """Create a cutting plan for a half of the model, analyzing each slice individually.
    
    Args:
        shape: The shape to analyze
        half_name: Name of the half (for reporting)
        print_max_size: Maximum printable dimension in mm
    
    Returns:
        Dictionary containing:
            - z_slices: Number of Z slices needed
            - z_slice_height: Height of each slice
            - slice_plans: List of slice information dictionaries
            - total_pieces: Total number of pieces
            - bbox: Bounding box of the shape
    """
    bbox = shape.BoundBox
    
    print(f"\n📐 Creating cutting plan for {half_name}:")
    print(f"   Original dimensions:")
    print(f"      X: {bbox.XLength:.1f}mm")
    print(f"      Y: {bbox.YLength:.1f}mm")
    print(f"      Z: {bbox.ZLength:.1f}mm")
    print(f"   Max printable size: {print_max_size}mm")
    
    # Calculate Z slices needed
    z_slices_needed = 1
    z_slice_height = bbox.ZLength
    
    if bbox.ZLength > print_max_size:
        import math
        z_slices_needed = math.ceil(bbox.ZLength / print_max_size)
        z_slice_height = bbox.ZLength / z_slices_needed
        print(f"   📊 Z-axis: Needs {z_slices_needed} slices of {z_slice_height:.1f}mm each")
    else:
        print(f"   ✅ Z-axis: Fits in one piece ({bbox.ZLength:.1f}mm < {print_max_size}mm)")
    
    # Y-axis check (already split at Y=0)
    if bbox.YLength > print_max_size:
        print(f"   ⚠️ Y-axis: {bbox.YLength:.1f}mm > {print_max_size}mm")
        print(f"      This half may still be too large in Y!")
    else:
        print(f"   ✅ Y-axis: Fits in one piece ({bbox.YLength:.1f}mm < {print_max_size}mm)")
    
    # Analyze each Z slice for X-splitting needs
    print(f"\n   🔍 Analyzing each slice for X-splitting needs:")
    total_pieces = 0
    slice_plans = []
    
    for i in range(z_slices_needed):
        # Calculate the Z bounds for this slice
        z_start = bbox.ZMin + (i * z_slice_height)
        z_end = min(z_start + z_slice_height, bbox.ZMax)
        z_mid = (z_start + z_end) / 2
        
        # Create a thin box at the middle of this slice to intersect with the shape
        # This gives us an approximation of the slice's cross-section
        test_box = Part.makeBox(
            bbox.XLength + 100,  # Wide enough to cover entire shape
            bbox.YLength + 100,  # Deep enough to cover entire shape
            1,                    # Very thin slice
            Base.Vector(bbox.XMin - 50, bbox.YMin - 50, z_mid - 0.5)
        )
        
        # Intersect to get approximate slice bounds
        try:
            slice_intersection = shape.common(test_box)
            slice_bbox = slice_intersection.BoundBox
            slice_x_length = slice_bbox.XLength
            slice_x_center = (slice_bbox.XMin + slice_bbox.XMax) / 2
        except:
            # If intersection fails, use conservative estimate
            slice_x_length = bbox.XLength
            slice_x_center = (bbox.XMin + bbox.XMax) / 2
        
        # Determine if this slice needs X-splitting
        needs_x_split = slice_x_length > print_max_size
        pieces_in_slice = 2 if needs_x_split else 1
        total_pieces += pieces_in_slice
        
        slice_info = {
            'index': i + 1,
            'z_start': z_start,
            'z_end': z_end,
            'x_length': slice_x_length,
            'x_center': slice_x_center,
            'needs_x_split': needs_x_split,
            'pieces': pieces_in_slice
        }
        slice_plans.append(slice_info)
        
        print(f"      Slice {i+1} (Z: {z_start:.0f} to {z_end:.0f}mm):")
        print(f"         X width: {slice_x_length:.1f}mm")
        if needs_x_split:
            print(f"         ❌ Needs X-split (>{print_max_size}mm) → 2 pieces")
        else:
            print(f"         ✅ No X-split needed → 1 piece")
    
    print(f"\n   📦 Total pieces for {half_name}: {total_pieces}")
    
    # Create cutting plan structure
    cutting_plan = {
        'z_slices': z_slices_needed,
        'z_slice_height': z_slice_height,
        'slice_plans': slice_plans,
        'total_pieces': total_pieces,
        'bbox': bbox
    }
    
    return cutting_plan


def perform_cutting_operations(port_half, port_plan, doc, boat_name="MackenSea", 
                              explosion_factor=0, color_base=(0.2, 0.4, 0.6)):
    """Perform the actual cutting operations to create individual pieces for ONE half only.
    Pieces remain in their original positions.
    
    Args:
        port_half: Port half shape with alignment holes (will be mirrored in slicer)
        port_plan: Cutting plan dictionary from create_cutting_plan()
        doc: FreeCAD document
        boat_name: Name of the boat for piece naming
        explosion_factor: Distance to separate pieces for visualization (0 = no separation)
        color_base: Base RGB color tuple for pieces
    
    Returns:
        List of (piece_name, piece_shape) tuples
    """
    print(f"\n✂️ PERFORMING CUTTING OPERATIONS...")
    print(f"   Creating {port_plan['total_pieces']} pieces (port half only - will be mirrored in slicer)")
    print(f"   Pieces will remain in original positions")
    
    pieces = []
    piece_objects = []
    
    print(f"\n   Processing Port half (for mirroring)...")
    
    # Cut into Z slices
    for i, slice_info in enumerate(port_plan['slice_plans']):
        slice_num = i + 1
        z_start = slice_info['z_start']
        z_end = slice_info['z_end']
        z_mid = (z_start + z_end) / 2
        
        print(f"      Creating slice {slice_num} (Z: {z_start:.0f} to {z_end:.0f}mm)")
        
        # Create cutting boxes for this slice
        bbox = port_half.BoundBox
        
        # Box to isolate this Z slice
        slice_box = Part.makeBox(
            bbox.XLength + 200,
            bbox.YLength + 200,
            z_end - z_start,
            Base.Vector(bbox.XMin - 100, bbox.YMin - 100, z_start)
        )
        
        # Extract the slice
        try:
            slice_shape = port_half.common(slice_box)
            
            # Now check if X-split is needed
            if slice_info['needs_x_split']:
                x_center = slice_info['x_center']
                print(f"         Splitting at X={x_center:.0f}mm")
                
                # Create boxes for left (A) and right (B) pieces
                left_box = Part.makeBox(
                    x_center - bbox.XMin + 10,
                    bbox.YLength + 200,
                    z_end - z_start + 10,
                    Base.Vector(bbox.XMin - 10, bbox.YMin - 100, z_start - 5)
                )
                
                right_box = Part.makeBox(
                    bbox.XMax - x_center + 10,
                    bbox.YLength + 200,
                    z_end - z_start + 10,
                    Base.Vector(x_center, bbox.YMin - 100, z_start - 5)
                )
                
                # Create A and B pieces
                piece_a = slice_shape.common(left_box)
                piece_b = slice_shape.common(right_box)
                
                # Name pieces without P/S designation
                name_a = f"{slice_num}A"
                name_b = f"{slice_num}B"
                
                pieces.append((name_a, piece_a))
                pieces.append((name_b, piece_b))
                
                print(f"         ✅ Created pieces {name_a} and {name_b}")
                
                # Create FreeCAD objects - keeping original positions
                obj_a = doc.addObject("Part::Feature", f"{boat_name}_{name_a}")
                obj_a.Shape = piece_a
                obj_a.ViewObject.ShapeColor = (
                    color_base[0] + i*0.15, 
                    color_base[1], 
                    color_base[2]
                )
                obj_a.ViewObject.Transparency = 20
                
                # Optional: Add small explosion offset
                if explosion_factor > 0:
                    obj_a.Placement.Base.x -= explosion_factor  # Move A piece left slightly
                    obj_a.Placement.Base.z += i * explosion_factor  # Separate Z slices
                
                piece_objects.append(obj_a)
                
                obj_b = doc.addObject("Part::Feature", f"{boat_name}_{name_b}")
                obj_b.Shape = piece_b
                obj_b.ViewObject.ShapeColor = (
                    color_base[0] + i*0.15 + 0.05, 
                    color_base[1], 
                    color_base[2] + 0.05
                )
                obj_b.ViewObject.Transparency = 20
                
                # Optional: Add small explosion offset
                if explosion_factor > 0:
                    obj_b.Placement.Base.x += explosion_factor  # Move B piece right slightly
                    obj_b.Placement.Base.z += i * explosion_factor  # Separate Z slices
                
                piece_objects.append(obj_b)
                
            else:
                # Single piece for this slice
                name = f"{slice_num}A"
                pieces.append((name, slice_shape))
                
                print(f"         ✅ Created piece {name}")
                
                # Create FreeCAD object - keeping original position
                obj = doc.addObject("Part::Feature", f"{boat_name}_{name}")
                obj.Shape = slice_shape
                obj.ViewObject.ShapeColor = (
                    color_base[0] + i*0.15, 
                    color_base[1], 
                    color_base[2]
                )
                obj.ViewObject.Transparency = 20
                
                # Optional: Add small explosion offset for Z separation
                if explosion_factor > 0:
                    obj.Placement.Base.z += i * explosion_factor
                
                piece_objects.append(obj)
                
        except Exception as e:
            print(f"         ❌ Failed to create slice: {e}")
    
    print(f"   ✅ Created {len(piece_objects)} pieces in original positions")
    if explosion_factor > 0:
        print(f"   ℹ️ Added {explosion_factor}mm explosion offset for visualization")
    
    return pieces