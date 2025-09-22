"""
Rudder Outline Builder - Scaled Version with Integrity Checks
Processes Profile CSV file and auto-generates outline from profile.
Scales to standard dimensions based on BoxSize from profile CSV.
Creates wire and shrunk wire for each, exports as STEP.
"""
import os
import sys
from PySide2 import QtWidgets
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "4.2.0"  # Added integrity checks

# Paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/input"
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/outline"

# Files
PROFILE_CSV = f"{BOAT_NAME}_Rudder_Profile.csv"
PROFILE_STEP = f"{BOAT_NAME}_Profile.step"
OUTLINE_STEP = f"{BOAT_NAME}_Outline.step"

# Parameters
OFFSET_DIST = -5.0  # mm inward offset
GRID_SPACING = 10   # mm grid spacing
GRID_MARGIN = 50    # mm beyond bounds
SHOW_MARKERS = False  # Set to True to show point markers

# Colors
PROFILE_COLORS = {
    'fill': (1.0, 0.8, 0.6),
    'wire': (1.0, 0.5, 0.0),
    'shrunk': (0.8, 0.2, 0.0)
}

OUTLINE_COLORS = {
    'fill': (0.6, 0.8, 1.0),
    'wire': (0.0, 0.5, 1.0),
    'shrunk': (0.0, 0.2, 0.8)
}


def read_csv(csv_path):
    """
    Read CSV file in the new cleaned format.
    Returns (segments, parameters) where:
    - segments is a list of tuples (segment_type, points)
    - parameters is a dict of key-value pairs from the CSV
    """
    segments = []
    parameters = {}
    current_points = []  # Track all points continuously
    
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    
    in_segments = False
    current_segment_type = None
    current_segment_points = []
    
    for line in lines:
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
        
        # Check if we've reached the points section
        if line == 'X,Y':
            in_segments = True
            continue
        
        if not in_segments:
            # Parse parameters
            if ',' in line:
                # Special handling for BoxSize which has format: BoxSize,500,1110
                if line.startswith('BoxSize,') or line.startswith('boxsize,'):
                    parts = line.split(',')
                    if len(parts) >= 3:
                        parameters['BoxSize'] = f"{parts[1].strip()},{parts[2].strip()}"
                        parameters['BoxSize_X'] = float(parts[1].strip())
                        parameters['BoxSize_Z'] = float(parts[2].strip())
                else:
                    # Regular parameter parsing
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        parameters[key] = value
        else:
            # Parse segments and points
            if line.startswith('SEGMENT'):
                # Save previous segment if exists
                if current_segment_type and current_segment_points:
                    segments.append((current_segment_type.lower(), current_segment_points[:]))
                
                # Start new segment
                parts = line.split(',')
                if len(parts) >= 2:
                    current_segment_type = parts[1].strip()
                    current_segment_points = []
                    
                    # If this isn't the first segment, start with the last point from current_points
                    if current_points:
                        current_segment_points.append(current_points[-1])
            elif ',' in line:
                # Parse point
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        x = float(parts[0].strip())
                        y = float(parts[1].strip())
                        point = (x, -y)  # Y from CSV becomes negative Z in 3D space
                        current_segment_points.append(point)
                        current_points.append(point)
                    except ValueError:
                        pass  # Skip invalid points
    
    # Save last segment
    if current_segment_type and current_segment_points:
        segments.append((current_segment_type.lower(), current_segment_points))
    
    # Validate that we have segments
    if not segments:
        raise ValueError("No valid segments found in CSV")
    
    return segments, parameters


def generate_outline_from_profile(profile_segments, profile_parameters):
    """
    Generate outline segments from profile segments.
    Outline: (0,0) → (max_x,0) → (max_x,profile_y_at_max_x) → follow COMPLETE profile to (0,0)
    """
    # Collect all points from profile to find max_x
    all_points = []
    for _, points in profile_segments:
        all_points.extend(points)
    
    if not all_points:
        raise ValueError("No points found in profile")
    
    # Find max X and corresponding Y
    max_x = max(p[0] for p in all_points)
    
    # Find which segment and point index contains max_x
    max_x_segment_idx = None
    max_x_point_idx = None
    profile_y_at_max_x = None
    
    for seg_idx, (seg_type, points) in enumerate(profile_segments):
        for pt_idx, point in enumerate(points):
            if abs(point[0] - max_x) < 0.01:  # Small tolerance
                max_x_segment_idx = seg_idx
                max_x_point_idx = pt_idx
                profile_y_at_max_x = point[1]
                break
        if max_x_segment_idx is not None:
            break
    
    if profile_y_at_max_x is None:
        # Fallback: find closest point to max_x
        closest_point = min(all_points, key=lambda p: abs(p[0] - max_x))
        profile_y_at_max_x = closest_point[1]
        print(f"   Warning: Using closest point for max_x, Y = {profile_y_at_max_x}")
    
    print(f"   Outline: max_x = {max_x}, profile_y_at_max_x = {profile_y_at_max_x}")
    print(f"   Max X found in segment {max_x_segment_idx}, point {max_x_point_idx}")
    
    # Create outline segments
    outline_segments = []
    
    # Segment 1: (0,0) → (max_x, 0) - Square top horizontal
    outline_segments.append(('line', [(0.0, 0.0), (max_x, 0.0)]))
    
    # Segment 2: (max_x, 0) → (max_x, profile_y_at_max_x) - Square top vertical
    if abs(profile_y_at_max_x) > 0.001:
        outline_segments.append(('line', [(max_x, 0.0), (max_x, profile_y_at_max_x)]))
    
    # Segment 3: Follow COMPLETE profile from max_x point forward to (0,0)
    if max_x_segment_idx is not None:
        # Start from the segment containing max_x
        for seg_idx in range(max_x_segment_idx, len(profile_segments)):
            seg_type, points = profile_segments[seg_idx]
            
            if seg_idx == max_x_segment_idx:
                # For the segment containing max_x, start from that point onwards
                segment_points = points[max_x_point_idx:]
                if len(segment_points) > 1:
                    outline_segments.append((seg_type, segment_points))
            else:
                # For subsequent segments, include all points
                if len(points) > 1:
                    outline_segments.append((seg_type, points))
        
        print(f"   Added {len(outline_segments) - 2} profile segments to outline")
    else:
        print("   Warning: Could not find max_x in segments, using fallback approach")
        # Fallback: find all points after max_x and create line segments
        remaining_points = []
        found_max_x = False
        
        for _, points in profile_segments:
            for point in points:
                if not found_max_x and abs(point[0] - max_x) < 0.01:
                    found_max_x = True
                    remaining_points.append(point)
                elif found_max_x:
                    remaining_points.append(point)
        
        # Create line segments from remaining points
        for i in range(len(remaining_points) - 1):
            p1 = remaining_points[i]
            p2 = remaining_points[i + 1]
            if abs(p1[0] - p2[0]) > 0.001 or abs(p1[1] - p2[1]) > 0.001:
                outline_segments.append(('line', [p1, p2]))
    
    print(f"   Created {len(outline_segments)} total outline segments")
    
    # Copy parameters from profile (including BoxSize)
    outline_parameters = profile_parameters.copy()
    
    return outline_segments, outline_parameters


def calculate_scale_factors(segments, box_size_x=None, box_size_z=None):
    """Calculate scale factors to achieve target dimensions."""
    # Collect all points
    all_points = []
    for _, points in segments:
        all_points.extend(points)
    
    # Check if we have points
    if not all_points:
        print(f"   ❌ ERROR: No points found in segments!")
        return 1.0, 1.0, 0, 0, 0, 0
    
    # Find current bounds
    xs = [p[0] for p in all_points]
    zs = [p[1] for p in all_points]
    
    if not xs or not zs:
        print(f"   ❌ ERROR: No valid coordinates found!")
        return 1.0, 1.0, 0, 0, 0, 0
    
    max_x = max(xs)
    min_z = min(zs)  # Will be negative
    
    # Check for zero dimensions
    if max_x == 0:
        print(f"   ❌ ERROR: Maximum X is 0!")
        return 1.0, 1.0, 0, 0, 0, 0
    
    if min_z == 0:
        print(f"   ❌ ERROR: Minimum Z is 0! All Z coordinates might be 0.")
        print(f"   Z values found: {set(zs)}")
        return 1.0, 1.0, 0, 0, 0, 0
    
    # Use BoxSize if provided, otherwise use original dimensions
    if box_size_x is None:
        box_size_x = max_x
    if box_size_z is None:
        box_size_z = abs(min_z)
    
    # Calculate scale factors
    scale_x = box_size_x / max_x
    scale_z = box_size_z / abs(min_z)
    
    print(f"\n📐 SCALING CALCULATIONS:")
    print(f"   Original dimensions:")
    print(f"      X max = {max_x:.1f}mm")
    print(f"      Z min = {min_z:.1f}mm (height = {abs(min_z):.1f}mm)")
    print(f"   Target dimensions (from BoxSize):")
    print(f"      X = {box_size_x}mm")
    print(f"      Z = {box_size_z}mm")
    print(f"   Scale factors:")
    print(f"      X scale = {scale_x:.4f} ({scale_x*100:.1f}%)")
    print(f"      Z scale = {scale_z:.4f} ({scale_z*100:.1f}%)")
    
    return scale_x, scale_z, max_x, abs(min_z), box_size_x, box_size_z


def validate_shape(shape, name):
    """Validate shape integrity before export."""
    print(f"\n🔍 Validating {name}...")
    
    issues = []
    warnings = []
    
    # Basic validity check
    if not shape.isValid():
        issues.append("Shape is not valid")
    
    # Check if null
    if shape.isNull():
        issues.append("Shape is null")
    
    # Type-specific checks
    if hasattr(shape, 'ShapeType'):
        shape_type = shape.ShapeType
        print(f"   Type: {shape_type}")
        
        if shape_type == 'Wire':
            # Wire checks
            if not shape.isClosed():
                issues.append("Wire is not closed")
            
            # Check for self-intersections
            if len(shape.Edges) > 0:
                edges = shape.Edges
                print(f"   Edges: {len(edges)}")
                
                # Check edge connectivity
                for i in range(len(edges) - 1):
                    end_vertex = edges[i].Vertexes[-1].Point
                    start_vertex = edges[i+1].Vertexes[0].Point
                    gap = end_vertex.distanceToPoint(start_vertex)
                    if gap > 0.01:  # 0.01mm tolerance
                        issues.append(f"Gap of {gap:.3f}mm between edges {i} and {i+1}")
                
                # Check closure gap
                if shape.isClosed():
                    last_vertex = edges[-1].Vertexes[-1].Point
                    first_vertex = edges[0].Vertexes[0].Point
                    closure_gap = last_vertex.distanceToPoint(first_vertex)
                    if closure_gap > 0.01:
                        warnings.append(f"Closure gap of {closure_gap:.3f}mm")
        
        elif shape_type == 'Face':
            # Face checks
            if shape.Area <= 0:
                issues.append(f"Face has invalid area: {shape.Area}")
            else:
                print(f"   Area: {shape.Area:.1f} mm²")
            
            # Check outer wire
            if hasattr(shape, 'OuterWire'):
                if not shape.OuterWire.isClosed():
                    issues.append("Face outer wire is not closed")
    
    # Geometry checks
    try:
        bbox = shape.BoundBox
        if bbox.DiagonalLength == 0:
            issues.append("Shape has zero size")
        else:
            print(f"   Bounding box: X={bbox.XMax:.1f}, Y={bbox.YMax:.1f}, Z={abs(bbox.ZMin):.1f}")
    except:
        issues.append("Cannot compute bounding box")
    
    # Report results
    if issues:
        print(f"   ❌ VALIDATION FAILED:")
        for issue in issues:
            print(f"      - {issue}")
        return False
    
    if warnings:
        print(f"   ⚠️ Warnings:")
        for warning in warnings:
            print(f"      - {warning}")
    
    print(f"   ✅ Validation passed")
    return True


def create_edges(segments, scale_x=1.0, scale_z=1.0):
    """Create FreeCAD edges from segments with optional scaling."""
    edges = []
    
    for seg_type, points in segments:
        if seg_type == 'line':
            for i in range(len(points) - 1):
                p1 = Vector(points[i][0] * scale_x, 0, points[i][1] * scale_z)
                p2 = Vector(points[i+1][0] * scale_x, 0, points[i+1][1] * scale_z)
                edges.append(Part.makeLine(p1, p2))
        elif seg_type == 'arc':
            if len(points) >= 3:
                p1 = Vector(points[0][0] * scale_x, 0, points[0][1] * scale_z)
                p2 = Vector(points[1][0] * scale_x, 0, points[1][1] * scale_z)
                p3 = Vector(points[2][0] * scale_x, 0, points[2][1] * scale_z)
                edges.append(Part.Arc(p1, p2, p3).toShape())
    
    return edges


def add_dimension_labels(doc, original_x, original_z, scale_x, scale_z, target_x, target_z):
    """Add dimension labels showing original and scaled sizes."""
    # Create text showing dimensions
    info_text = f"""SCALING INFO:
Original: {original_x:.1f} x {original_z:.1f}mm
Scaled: {target_x:.0f} x {target_z:.0f}mm
Scale X: {scale_x:.3f} ({scale_x*100:.0f}%)
Scale Z: {scale_z:.3f} ({scale_z*100:.0f}%)"""
    
    # Add annotation
    label = doc.addObject("App::Annotation", "Scaling_Info")
    label.LabelText = info_text
    label.Position = Vector(10, 0, 50)
    label.ViewObject.TextColor = (0.0, 0.0, 0.0)
    label.ViewObject.FontSize = 36
    
    # Add dimension lines for scaled outline
    # Horizontal dimension (X)
    x_dim_line = Part.makeLine(Vector(0, 0, 20), Vector(target_x, 0, 20))
    x_dim_obj = doc.addObject("Part::Feature", "X_Dimension")
    x_dim_obj.Shape = x_dim_line
    x_dim_obj.ViewObject.ShapeColor = (0.0, 0.0, 0.0)
    x_dim_obj.ViewObject.LineWidth = 2
    
    # X dimension label
    x_label = doc.addObject("App::Annotation", "X_Label")
    x_label.LabelText = f"{target_x:.0f}mm"
    x_label.Position = Vector(target_x/2, 0, 30)
    x_label.ViewObject.TextColor = (0.0, 0.0, 0.0)
    x_label.ViewObject.FontSize = 28
    
    # Vertical dimension (Z)
    z_dim_line = Part.makeLine(Vector(-20, 0, 0), Vector(-20, 0, -target_z))
    z_dim_obj = doc.addObject("Part::Feature", "Z_Dimension")
    z_dim_obj.Shape = z_dim_line
    z_dim_obj.ViewObject.ShapeColor = (0.0, 0.0, 0.0)
    z_dim_obj.ViewObject.LineWidth = 2
    
    # Z dimension label
    z_label = doc.addObject("App::Annotation", "Z_Label")
    z_label.LabelText = f"{target_z:.0f}mm"
    z_label.Position = Vector(-40, 0, -target_z/2)
    z_label.ViewObject.TextColor = (0.0, 0.0, 0.0)
    z_label.ViewObject.FontSize = 28


def process_csv(csv_filename, object_prefix, colors, doc, scale_x=1.0, scale_z=1.0):
    """Process a CSV file and create FreeCAD objects with scaling."""
    csv_path = f"{INPUT_FOLDER}/{csv_filename}"
    
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_filename} not found, skipping")
        return None, None, None, {}
    
    print(f"📂 Processing {csv_filename}")
    
    # Parse CSV
    try:
        segments, parameters = read_csv(csv_path)
    except ValueError as e:
        print(f"❌ {csv_filename}: {e}")
        return None, None, None, {}
    
    # Create scaled edges and wire
    edges = create_edges(segments, scale_x, scale_z)
    wire = Part.Wire(edges)
    
    # Close wire if needed
    if not wire.isClosed():
        last = wire.Edges[-1].Vertexes[-1].Point
        first = wire.Edges[0].Vertexes[0].Point
        if last.distanceToPoint(first) > 0.1:
            wire = Part.Wire(edges + [Part.makeLine(last, first)])
    
    print(f"   Wire: {len(wire.Edges)} edges, closed: {wire.isClosed()}")
    
    # Validate wire
    if not validate_shape(wire, f"{object_prefix} wire"):
        print(f"   ❌ Wire validation failed, aborting")
        return None, None, None, parameters
    
    # Report scaled dimensions
    bbox = wire.BoundBox
    print(f"   ✅ SCALED dimensions: X = {bbox.XMax:.1f}mm, Z = {abs(bbox.ZMin):.1f}mm")
    
    objects = []
    
    # Create fill (face)
    try:
        face = Part.Face(wire)
        if validate_shape(face, f"{object_prefix} face"):
            fill_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Fill")
            fill_obj.Shape = face
            fill_obj.ViewObject.ShapeColor = colors['fill']
            fill_obj.ViewObject.Transparency = 70
    except Exception as e:
        print(f"   ⚠️ Face creation failed: {e}")
    
    # Create wire object
    wire_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Wire")
    wire_obj.Shape = wire
    wire_obj.ViewObject.ShapeColor = colors['wire']
    wire_obj.ViewObject.LineWidth = 3
    objects.append(wire_obj)
    
    # Create shrunk wire
    try:
        shrunk_wire = wire.makeOffset2D(OFFSET_DIST)
        
        # Validate shrunk wire
        if not validate_shape(shrunk_wire, f"{object_prefix} shrunk wire"):
            raise ValueError("Shrunk wire validation failed")
        
        shrunk_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Shrunk")
        shrunk_obj.Shape = shrunk_wire
        shrunk_obj.ViewObject.ShapeColor = colors['shrunk']
        shrunk_obj.ViewObject.LineWidth = 2
        objects.append(shrunk_obj)
        
        print(f"   Shrunk: {len(shrunk_wire.Edges)} edges")
        
    except Exception as e:
        print(f"❌ Shrunk wire failed: {e}")
        return None, None, None, parameters
    
    # Get scaled points for grid
    all_points = []
    for _, points in segments:
        for point in points:
            all_points.append((point[0] * scale_x, point[1] * scale_z))
    
    return objects, all_points, segments, parameters


def process_segments(segments, object_prefix, colors, doc, scale_x=1.0, scale_z=1.0):
    """Process segments directly and create FreeCAD objects with scaling."""
    print(f"📂 Processing {object_prefix} segments")
    
    # Create scaled edges and wire
    edges = create_edges(segments, scale_x, scale_z)
    wire = Part.Wire(edges)
    
    # Close wire if needed
    if not wire.isClosed():
        last = wire.Edges[-1].Vertexes[-1].Point
        first = wire.Edges[0].Vertexes[0].Point
        if last.distanceToPoint(first) > 0.1:
            wire = Part.Wire(edges + [Part.makeLine(last, first)])
    
    print(f"   Wire: {len(wire.Edges)} edges, closed: {wire.isClosed()}")
    
    # Validate wire
    if not validate_shape(wire, f"{object_prefix} wire"):
        print(f"   ❌ Wire validation failed, aborting")
        return None, None
    
    # Report scaled dimensions
    bbox = wire.BoundBox
    print(f"   ✅ SCALED dimensions: X = {bbox.XMax:.1f}mm, Z = {abs(bbox.ZMin):.1f}mm")
    
    objects = []
    
    # Create fill (face)
    try:
        face = Part.Face(wire)
        if validate_shape(face, f"{object_prefix} face"):
            fill_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Fill")
            fill_obj.Shape = face
            fill_obj.ViewObject.ShapeColor = colors['fill']
            fill_obj.ViewObject.Transparency = 70
    except Exception as e:
        print(f"   ⚠️ Face creation failed: {e}")
    
    # Create wire object
    wire_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Wire")
    wire_obj.Shape = wire
    wire_obj.ViewObject.ShapeColor = colors['wire']
    wire_obj.ViewObject.LineWidth = 3
    objects.append(wire_obj)
    
    # Create shrunk wire
    try:
        shrunk_wire = wire.makeOffset2D(OFFSET_DIST)
        
        # Validate shrunk wire
        if not validate_shape(shrunk_wire, f"{object_prefix} shrunk wire"):
            raise ValueError("Shrunk wire validation failed")
        
        shrunk_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Shrunk")
        shrunk_obj.Shape = shrunk_wire
        shrunk_obj.ViewObject.ShapeColor = colors['shrunk']
        shrunk_obj.ViewObject.LineWidth = 2
        objects.append(shrunk_obj)
        
        print(f"   Shrunk: {len(shrunk_wire.Edges)} edges")
        
    except Exception as e:
        print(f"❌ Shrunk wire failed: {e}")
        return None, None
    
    # Get scaled points for grid
    all_points = []
    for _, points in segments:
        for point in points:
            all_points.append((point[0] * scale_x, point[1] * scale_z))
    
    return objects, all_points


def draw_grid(points, doc):
    """Draw reference grid."""
    if not points:
        return
    
    print("Drawing grid...")
    
    xs = [p[0] for p in points]
    zs = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    
    start_x, end_x = 0, int(max_x) + GRID_MARGIN
    start_z, end_z = 0, int(min_z) - GRID_MARGIN
    
    print(f"   Grid bounds: X={start_x} to {end_x}, Z={start_z} to {end_z}")
    
    # Vertical lines
    for x in range(start_x, end_x + 1, GRID_SPACING):
        line = Part.makeLine(Vector(x, 0, start_z), Vector(x, 0, end_z))
        # Fix object naming for negative coordinates
        obj_name = f"Grid_V_{x}" if x >= 0 else f"Grid_V_N{abs(x)}"
        obj = doc.addObject("Part::Feature", obj_name)
        obj.Shape = line
        color = (0.4, 0.4, 0.4) if x % (GRID_SPACING * 10) == 0 else (0.8, 0.8, 0.8)
        width = 2 if x % (GRID_SPACING * 10) == 0 else 1
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineWidth = width
    
    # Horizontal lines
    grid_count = 0
    for z in range(start_z, end_z - 1, -GRID_SPACING):
        line = Part.makeLine(Vector(start_x, 0, z), Vector(end_x, 0, z))
        # Fix object naming for negative coordinates
        obj_name = f"Grid_H_{z}" if z >= 0 else f"Grid_H_N{abs(z)}"
        obj = doc.addObject("Part::Feature", obj_name)
        obj.Shape = line
        color = (0.4, 0.4, 0.4) if z % (GRID_SPACING * 10) == 0 else (0.8, 0.8, 0.8)
        width = 2 if z % (GRID_SPACING * 10) == 0 else 1
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineWidth = width
        grid_count += 1
        
        # Limit grid lines to prevent hanging
        if grid_count > 200:
            print(f"   Grid generation stopped at {grid_count} lines to prevent hanging")
            break
    
    print(f"   Grid complete: {grid_count} horizontal lines created")


def run():
    """Main entry point."""
    print(f"\n🚤 Rudder Outline Builder v{VERSION} for {BOAT_NAME}")
    
    # Ensure output folder
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # New document
    doc_name = f"Rudder_Outline_{BOAT_NAME}"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")
    
    # Process Profile CSV to get BoxSize and calculate scale factors
    print("\n📋 PROFILE (reading BoxSize and calculating scale factors):")
    profile_path = f"{INPUT_FOLDER}/{PROFILE_CSV}"
    
    if not os.path.exists(profile_path):
        print(f"❌ {PROFILE_CSV} not found!")
        return
    
    try:
        profile_segments, profile_params = read_csv(profile_path)
        
        # Debug: Show parsed parameters
        print(f"   Parsed parameters: {list(profile_params.keys())}")
        
        # Get BoxSize from parameters
        box_size_x = None
        box_size_z = None
        if 'BoxSize_X' in profile_params and 'BoxSize_Z' in profile_params:
            box_size_x = profile_params['BoxSize_X']
            box_size_z = profile_params['BoxSize_Z']
            print(f"   Found BoxSize in profile: {box_size_x} x {box_size_z}mm")
        else:
            print(f"   ⚠️ BoxSize not found in profile CSV, using original dimensions")
            if 'BoxSize' in profile_params:
                print(f"   (BoxSize raw value: {profile_params['BoxSize']})")
        
        print(f"   Found {len(profile_segments)} segments")
        
        scale_x, scale_z, orig_x, orig_z, target_x, target_z = calculate_scale_factors(
            profile_segments, box_size_x, box_size_z)
    except ValueError as e:
        print(f"❌ Failed to process profile: {e}")
        return
    
    # Generate outline from profile
    print("\n📋 OUTLINE (auto-generating from profile):")
    try:
        outline_segments, outline_params = generate_outline_from_profile(profile_segments, profile_params)
        print(f"   Generated {len(outline_segments)} outline segments")
    except ValueError as e:
        print(f"❌ Failed to generate outline: {e}")
        return
    
    # Process Outline with scaling
    print("\n📋 OUTLINE (applying scaling):")
    outline_objects, outline_points = process_segments(
        outline_segments, "Outline", OUTLINE_COLORS, doc, scale_x, scale_z)
    
    # Process Profile with SAME scale factors
    print("\n📋 PROFILE (using same scale factors):")
    profile_objects, profile_points, _, _ = process_csv(
        PROFILE_CSV, "Profile", PROFILE_COLORS, doc, scale_x, scale_z)
    
    # Add dimension labels to show scaling
    if scale_x != 1.0 or scale_z != 1.0:
        add_dimension_labels(doc, orig_x, orig_z, scale_x, scale_z, target_x, target_z)
    
    # Export STEP files (scaled versions) - with final validation
    export_success = True
    
    if profile_objects:
        print("\n📤 Exporting Profile...")
        for obj in profile_objects:
            if not validate_shape(obj.Shape, f"Profile export {obj.Label}"):
                export_success = False
                break
        
        if export_success:
            path = f"{OUTPUT_FOLDER}/{PROFILE_STEP}"
            Part.export(profile_objects, path)
            print(f"✅ Exported scaled profile: {path}")
        else:
            print(f"❌ Profile export cancelled due to validation errors")
    
    if outline_objects and export_success:
        print("\n📤 Exporting Outline...")
        for obj in outline_objects:
            if not validate_shape(obj.Shape, f"Outline export {obj.Label}"):
                export_success = False
                break
        
        if export_success:
            path = f"{OUTPUT_FOLDER}/{OUTLINE_STEP}"
            Part.export(outline_objects, path)
            print(f"✅ Exported scaled outline: {path}")
        else:
            print(f"❌ Outline export cancelled due to validation errors")
    
    # Draw grid (use outline points if available)
    grid_points = outline_points if outline_points else profile_points
    if grid_points:
        draw_grid(grid_points, doc)
    
    # Finalize
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"   Original size: {orig_x:.1f} x {orig_z:.1f}mm")
    print(f"   Scaled size: {target_x:.0f} x {target_z:.0f}mm")
    print(f"   Scale factors: X={scale_x:.4f}, Z={scale_z:.4f}")
    
    # Print parsed parameters if available
    if profile_params:
        print(f"\n📋 Profile Parameters:")
        for key, value in profile_params.items():
            if not key.startswith('BoxSize_'):
                print(f"   {key}: {value}")
    
    if export_success:
        print(f"\n✅ {BOAT_NAME} complete!")
    else:
        print(f"\n⚠️ {BOAT_NAME} completed with validation warnings")
    
    print(f"📁 Files in: {OUTPUT_FOLDER}")


# Execute when run as macro
if __name__ == "__main__":
    run()