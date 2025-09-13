"""
Rudder Outline Builder - Scaled Version with Integrity Checks
Processes Profile and Outline CSV files with LINE and ARC segments.
Scales to standard dimensions (X=500mm, Z=1110mm) based on outline.
Creates wire and shrunk wire for each, exports as STEP.
"""
import os
import sys
from PySide2 import QtWidgets
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Add helpers path and import CSV reader
sys.path.insert(0, os.path.expanduser("~/Rudder_Code/helpers"))
from read_rudder_outline_csv import read_csv

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "4.2.0"  # Added integrity checks

# Paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/input"
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/outline"

# Files
PROFILE_CSV = f"{BOAT_NAME}_Rudder_Profile.csv"
OUTLINE_CSV = f"{BOAT_NAME}_Rudder_Outline.csv"
PROFILE_STEP = f"{BOAT_NAME}_Profile.step"
OUTLINE_STEP = f"{BOAT_NAME}_Outline.step"

# Parameters
TARGET_X = 500.0    # mm target width
TARGET_Z = 1110.0   # mm target height
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


def calculate_scale_factors(segments):
    """Calculate scale factors to achieve target dimensions."""
    # Collect all points
    all_points = []
    for _, points in segments:
        all_points.extend(points)
    
    # Find current bounds
    xs = [p[0] for p in all_points]
    zs = [p[1] for p in all_points]
    max_x = max(xs)
    min_z = min(zs)  # Will be negative
    
    # Calculate scale factors
    scale_x = TARGET_X / max_x
    scale_z = TARGET_Z / abs(min_z)
    
    print(f"\n📏 SCALING CALCULATIONS:")
    print(f"   Original dimensions:")
    print(f"      X max = {max_x:.1f}mm")
    print(f"      Z min = {min_z:.1f}mm (height = {abs(min_z):.1f}mm)")
    print(f"   Target dimensions:")
    print(f"      X = {TARGET_X}mm")
    print(f"      Z = {TARGET_Z}mm")
    print(f"   Scale factors:")
    print(f"      X scale = {scale_x:.4f} ({scale_x*100:.1f}%)")
    print(f"      Z scale = {scale_z:.4f} ({scale_z*100:.1f}%)")
    
    return scale_x, scale_z, max_x, abs(min_z)


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
            p1 = Vector(points[0][0] * scale_x, 0, points[0][1] * scale_z)
            p2 = Vector(points[1][0] * scale_x, 0, points[1][1] * scale_z)
            p3 = Vector(points[2][0] * scale_x, 0, points[2][1] * scale_z)
            edges.append(Part.Arc(p1, p2, p3).toShape())
    
    return edges


def add_dimension_labels(doc, original_x, original_z, scale_x, scale_z):
    """Add dimension labels showing original and scaled sizes."""
    # Create text showing dimensions
    info_text = f"""SCALING INFO:
Original: {original_x:.1f} x {original_z:.1f}mm
Scaled: {TARGET_X:.0f} x {TARGET_Z:.0f}mm
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
    x_dim_line = Part.makeLine(Vector(0, 0, 20), Vector(TARGET_X, 0, 20))
    x_dim_obj = doc.addObject("Part::Feature", "X_Dimension")
    x_dim_obj.Shape = x_dim_line
    x_dim_obj.ViewObject.ShapeColor = (0.0, 0.0, 0.0)
    x_dim_obj.ViewObject.LineWidth = 2
    
    # X dimension label
    x_label = doc.addObject("App::Annotation", "X_Label")
    x_label.LabelText = f"{TARGET_X:.0f}mm"
    x_label.Position = Vector(TARGET_X/2, 0, 30)
    x_label.ViewObject.TextColor = (0.0, 0.0, 0.0)
    x_label.ViewObject.FontSize = 28
    
    # Vertical dimension (Z)
    z_dim_line = Part.makeLine(Vector(-20, 0, 0), Vector(-20, 0, -TARGET_Z))
    z_dim_obj = doc.addObject("Part::Feature", "Z_Dimension")
    z_dim_obj.Shape = z_dim_line
    z_dim_obj.ViewObject.ShapeColor = (0.0, 0.0, 0.0)
    z_dim_obj.ViewObject.LineWidth = 2
    
    # Z dimension label
    z_label = doc.addObject("App::Annotation", "Z_Label")
    z_label.LabelText = f"{TARGET_Z:.0f}mm"
    z_label.Position = Vector(-40, 0, -TARGET_Z/2)
    z_label.ViewObject.TextColor = (0.0, 0.0, 0.0)
    z_label.ViewObject.FontSize = 28


def process_csv(csv_filename, object_prefix, colors, doc, scale_x=1.0, scale_z=1.0):
    """Process a CSV file and create FreeCAD objects with scaling."""
    csv_path = f"{INPUT_FOLDER}/{csv_filename}"
    
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_filename} not found, skipping")
        return None, None, None
    
    print(f"📂 Processing {csv_filename}")
    
    # Parse CSV
    try:
        segments = read_csv(csv_path)
    except ValueError as e:
        print(f"❌ {csv_filename}: {e}")
        return None, None, None
    
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
        return None, None, None
    
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
        return None, None, None
    
    # Get scaled points for grid
    all_points = []
    for _, points in segments:
        for point in points:
            all_points.append((point[0] * scale_x, point[1] * scale_z))
    
    return objects, all_points, segments


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
    
    # Vertical lines
    for x in range(start_x, end_x + 1, GRID_SPACING):
        line = Part.makeLine(Vector(x, 0, start_z), Vector(x, 0, end_z))
        obj = doc.addObject("Part::Feature", f"Grid_V_{x}")
        obj.Shape = line
        color = (0.4, 0.4, 0.4) if x % (GRID_SPACING * 10) == 0 else (0.8, 0.8, 0.8)
        width = 2 if x % (GRID_SPACING * 10) == 0 else 1
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineWidth = width
    
    # Horizontal lines
    for z in range(start_z, end_z - 1, -GRID_SPACING):
        line = Part.makeLine(Vector(start_x, 0, z), Vector(end_x, 0, z))
        obj = doc.addObject("Part::Feature", f"Grid_H_{z}")
        obj.Shape = line
        color = (0.4, 0.4, 0.4) if z % (GRID_SPACING * 10) == 0 else (0.8, 0.8, 0.8)
        width = 2 if z % (GRID_SPACING * 10) == 0 else 1
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineWidth = width


def run():
    """Main entry point."""
    print(f"\n🚤 Rudder Outline Builder v{VERSION} for {BOAT_NAME}")
    print(f"📏 Scaling to standard dimensions: X={TARGET_X}mm, Z={TARGET_Z}mm")
    
    # Ensure output folder
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # New document
    doc_name = f"Rudder_Outline_{BOAT_NAME}"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")
    
    # Process Outline FIRST to calculate scale factors
    print("\n📋 OUTLINE (calculating scale factors):")
    outline_path = f"{INPUT_FOLDER}/{OUTLINE_CSV}"
    if os.path.exists(outline_path):
        try:
            outline_segments = read_csv(outline_path)
            scale_x, scale_z, orig_x, orig_z = calculate_scale_factors(outline_segments)
        except ValueError as e:
            print(f"❌ Failed to calculate scale factors: {e}")
            scale_x, scale_z, orig_x, orig_z = 1.0, 1.0, 0, 0
    else:
        print(f"⚠️ {OUTLINE_CSV} not found, using scale 1.0")
        scale_x, scale_z, orig_x, orig_z = 1.0, 1.0, 0, 0
    
    # Process Outline with scaling
    print("\n📋 OUTLINE (applying scaling):")
    outline_objects, outline_points, _ = process_csv(OUTLINE_CSV, "Outline", OUTLINE_COLORS, doc, scale_x, scale_z)
    
    # Process Profile with SAME scale factors
    print("\n📋 PROFILE (using same scale factors):")
    profile_objects, profile_points, _ = process_csv(PROFILE_CSV, "Profile", PROFILE_COLORS, doc, scale_x, scale_z)
    
    # Add dimension labels to show scaling
    if scale_x != 1.0 or scale_z != 1.0:
        add_dimension_labels(doc, orig_x, orig_z, scale_x, scale_z)
    
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
    print(f"   Scaled size: {TARGET_X:.0f} x {TARGET_Z:.0f}mm")
    print(f"   Scale factors: X={scale_x:.4f}, Z={scale_z:.4f}")
    
    if export_success:
        print(f"\n✅ {BOAT_NAME} complete!")
    else:
        print(f"\n⚠️ {BOAT_NAME} completed with validation warnings")
    
    print(f"📁 Files in: {OUTPUT_FOLDER}")


# Execute when run as macro
if __name__ == "__main__":
    run()