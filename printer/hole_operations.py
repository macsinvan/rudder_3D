"""
Hole Operations Module
Handles creation of alignment and joining holes for rudder pieces
"""
import FreeCAD as App
import Part


def add_z_cut_alignment_pins(shape, z_cut_position, 
                             hole_diameter=6, support_diameter=10, 
                             hole_depth=25):
    """
    Add alignment holes at a Z-cut position.
    Holes are placed at 20%, 40%, 60%, 80% of chord width.
    
    Args:
        shape: The shape to add holes to
        z_cut_position: Z coordinate of the cut
        hole_diameter: Dowel hole diameter (6mm)
        support_diameter: Not used for straight holes (kept for compatibility)
        hole_depth: Hole depth (25mm)
    
    Returns:
        Modified shape with alignment holes
    """
    from FreeCAD import Vector, Base
    
    print(f"      Adding alignment holes at Z={z_cut_position:.1f}")
    
    # Step 1: Find chord bounds at this Z
    # Create thin horizontal slice
    slice_thickness = 1.0
    sample_slice = Part.makeBox(
        1000,  # Large X
        1000,  # Large Y  
        slice_thickness,
        Vector(-500, -500, z_cut_position - slice_thickness/2)
    )
    
    # Get intersection
    try:
        cross_section = shape.common(sample_slice)
        chord_bbox = cross_section.BoundBox
        
        x_min = chord_bbox.XMin
        x_max = chord_bbox.XMax
        chord_width = x_max - x_min
        y_pos = 0 - 3 - hole_diameter/2
        
        print(f"         Chord: X from {x_min:.1f} to {x_max:.1f} (width={chord_width:.1f})")
        
    except:
        print(f"         ❌ Failed to find chord at Z={z_cut_position:.1f}")
        return shape
    
    # Step 2: Calculate hole positions (20%, 40%, 60%, 90% along chord)
    hole_positions = []
    for fraction in [0.2, 0.4, 0.6, 0.9]:
        x_pos = x_min + (chord_width * fraction)
        hole_positions.append(Vector(x_pos, y_pos, z_cut_position))
    
    # Step 3: Create straight alignment holes
    result_shape = shape
    successful_holes = 0
    
    for i, pos in enumerate(hole_positions):
        # Create simple cylinder hole
        hole_cylinder = Part.makeCylinder(
            hole_diameter / 2,
            hole_depth,
            pos - Vector(0, 0, hole_depth/2),  # Center on cut plane
            Vector(0, 0, 1)  # Z direction
        )
        
        # Subtract hole from shape
        try:
            result_shape = result_shape.cut(hole_cylinder)
            successful_holes += 1
        except:
            print(f"         ⚠️ Failed to add hole {i+1}")
    
    print(f"         ✅ Added {successful_holes}/4 holes")
    return result_shape


def add_x_cut_alignment_pins(shape, x_cut_position, z_start, z_end,
                             hole_diameter=6, hole_depth=25):
    """
    Add alignment holes at an X-cut position.
    Holes are placed at 10%, 40%, 60%, 80% of slice height.
    Holes are perpendicular to the X-cut plane (along X-axis).
    
    Args:
        shape: The shape to add holes to
        x_cut_position: X coordinate of the cut
        z_start: Bottom Z coordinate of the slice
        z_end: Top Z coordinate of the slice
        hole_diameter: Dowel hole diameter (6mm)
        hole_depth: Hole depth (25mm)
    
    Returns:
        Modified shape with alignment holes
    """
    from FreeCAD import Vector, Base
    
    print(f"      Adding X-cut alignment holes at X={x_cut_position:.1f}")
    
    # Calculate slice height
    slice_height = z_end - z_start
    
    # Get shape bounding box for Y position
    bbox = shape.BoundBox
    y_pos = 0 - 3 - hole_diameter/2  # Position holes just off the Y=0 split
    
    print(f"         Slice from Z={z_start:.1f} to {z_end:.1f} (height={slice_height:.1f})")
    print(f"         Y position for holes: {y_pos:.1f}")
    
    # Calculate hole positions at 10%, 40%, 60%, 80% of height
    hole_positions = []
    for fraction in [0.1, 0.4, 0.6, 0.8]:
        z_pos = z_start + (slice_height * fraction)
        hole_positions.append(Vector(x_cut_position, y_pos, z_pos))
    
    # Create alignment holes perpendicular to X-cut plane (along X-axis)
    result_shape = shape
    successful_holes = 0
    
    for i, pos in enumerate(hole_positions):
        # Create cylinder hole along X-axis (perpendicular to cut plane)
        hole_cylinder = Part.makeCylinder(
            hole_diameter / 2,
            hole_depth,
            pos - Vector(hole_depth/2, 0, 0),  # Center on cut plane, extend in X
            Vector(1, 0, 0)  # X direction (perpendicular to X-cut plane)
        )
        
        # Subtract hole from shape
        try:
            result_shape = result_shape.cut(hole_cylinder)
            successful_holes += 1
        except:
            print(f"         ⚠️ Failed to add X-cut hole {i+1}")
    
    print(f"         ✅ Added {successful_holes}/4 X-cut holes")
    return result_shape


def add_y_half_joining_holes(shape, z_start, z_end, section_name,
                             hole_diameter=6, row_positions=[0.25, 0.75], 
                             x_positions=[0.1, 0.4, 0.6, 0.9], hole_depth=25):
    """
    Add horizontal holes in Y-direction for joining port and starboard halves.
    
    Args:
        shape: The shape to add holes to
        z_start: Bottom Z of the section
        z_end: Top Z of the section  
        section_name: Name for logging
        hole_diameter: Bolt hole diameter (6mm)
        row_positions: Z positions as fraction of section height [0.25, 0.75]
        x_positions: X positions as fraction of chord width [0.1, 0.4, 0.6, 0.9]
        hole_depth: Depth of holes into the half (25mm)
    
    Returns:
        Modified shape with joining holes
    """
    from FreeCAD import Vector, Base
    
    section_height = z_end - z_start
    print(f"      Adding Y-direction joining holes to {section_name}")
    print(f"         Section Z: {z_start:.1f} to {z_end:.1f} (height={section_height:.1f})")
    
    result_shape = shape
    total_holes = 0
    
    # Create holes at each row position
    for row_frac in row_positions:
        z_position = z_start + (section_height * row_frac)
        print(f"         Row at Z={z_position:.1f} ({row_frac*100:.0f}% of section height)")
        
        # Find chord bounds at this Z using thin slice method
        slice_thickness = 1.0
        sample_slice = Part.makeBox(
            1000,  # Large X
            1000,  # Large Y  
            slice_thickness,
            Vector(-500, -500, z_position - slice_thickness/2)
        )
        
        # Get intersection to find chord
        try:
            cross_section = shape.common(sample_slice)
            chord_bbox = cross_section.BoundBox
            
            x_min = chord_bbox.XMin
            x_max = chord_bbox.XMax
            chord_width = x_max - x_min
            
            print(f"            Chord: X from {x_min:.1f} to {x_max:.1f} (width={chord_width:.1f})")
            
            # Create holes at each X position along this row
            for x_frac in x_positions:
                x_pos = x_min + (chord_width * x_frac)
                
                # Create horizontal hole (Y-direction) from Y=0 into the port half
                hole_cylinder = Part.makeCylinder(
                    hole_diameter / 2,
                    hole_depth,
                    Vector(x_pos, -hole_depth/2, z_position),  # Start at Y=0, extend into port half
                    Vector(0, -1, 0)  # Negative Y direction (into port half)
                )
                
                # Subtract hole from shape
                try:
                    result_shape = result_shape.cut(hole_cylinder)
                    total_holes += 1
                except:
                    print(f"            ⚠️ Failed to add hole at X={x_pos:.1f}")
            
        except:
            print(f"            ❌ Failed to find chord at Z={z_position:.1f}")
    
    expected_holes = len(row_positions) * len(x_positions)
    print(f"         ✅ Added {total_holes}/{expected_holes} joining holes")
    return result_shape