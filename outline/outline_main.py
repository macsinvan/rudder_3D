"""
Rudder Outline Builder - Simplified Version
Processes Profile and Outline CSV files with LINE and ARC segments.
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
VERSION = "3.0.0"  # Simplified version

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
OFFSET_DIST = -5.0  # mm inward offset
GRID_SPACING = 10   # mm grid spacing
GRID_MARGIN = 50    # mm beyond bounds

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


def create_edges(segments):
    """Create FreeCAD edges from segments."""
    edges = []
    
    for seg_type, points in segments:
        if seg_type == 'line':
            for i in range(len(points) - 1):
                p1 = Vector(points[i][0], 0, points[i][1])
                p2 = Vector(points[i+1][0], 0, points[i+1][1])
                edges.append(Part.makeLine(p1, p2))
        elif seg_type == 'arc':
            p1 = Vector(points[0][0], 0, points[0][1])
            p2 = Vector(points[1][0], 0, points[1][1])
            p3 = Vector(points[2][0], 0, points[2][1])
            edges.append(Part.Arc(p1, p2, p3).toShape())
    
    return edges


def add_point_markers(segments, doc, object_prefix):
    """Add red spheres and labels at each point for the outline."""
    print(f"   Adding point markers and labels...")
    
    # Collect all unique points
    point_set = set()
    for seg_type, points in segments:
        for point in points:
            point_set.add(tuple(point))
    
    # Create sphere and label for each point
    for csv_x, csv_y in point_set:
        # Create small red sphere
        sphere = Part.makeSphere(2.0, Vector(csv_x, 0, csv_y))
        sphere_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Point_{csv_x}_{csv_y}")
        sphere_obj.Shape = sphere
        sphere_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)  # Red
        
        # Create label with CSV coordinates - offset above and to the right
        label = doc.addObject("App::Annotation", f"{BOAT_NAME}_{object_prefix}_Label_{csv_x}_{csv_y}")
        label.LabelText = f"[{csv_x}, {csv_y}]"
        label.Position = Vector(csv_x + 5, 0, csv_y + 5)  # Offset for visibility
        label.ViewObject.TextColor = (1.0, 0.0, 0.0)  # Red text
        label.ViewObject.FontSize = 24  # Much larger font
    
    print(f"   Added {len(point_set)} point markers")


def process_csv(csv_filename, object_prefix, colors, doc):
    """Process a CSV file and create FreeCAD objects."""
    csv_path = f"{INPUT_FOLDER}/{csv_filename}"
    
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_filename} not found, skipping")
        return None, None
    
    print(f"📂 Processing {csv_filename}")
    
    # Parse CSV
    try:
        segments = read_csv(csv_path)
    except ValueError as e:
        print(f"❌ {csv_filename}: {e}")
        return None, None
    
    # Create edges and wire
    edges = create_edges(segments)
    wire = Part.Wire(edges)
    
    # Close wire if needed
    if not wire.isClosed():
        last = wire.Edges[-1].Vertexes[-1].Point
        first = wire.Edges[0].Vertexes[0].Point
        if last.distanceToPoint(first) > 0.1:
            wire = Part.Wire(edges + [Part.makeLine(last, first)])
    
    print(f"   Wire: {len(wire.Edges)} edges, closed: {wire.isClosed()}")
    
    objects = []
    
    # Create fill (face)
    try:
        face = Part.Face(wire)
        fill_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Fill")
        fill_obj.Shape = face
        fill_obj.ViewObject.ShapeColor = colors['fill']
        fill_obj.ViewObject.Transparency = 70
    except:
        pass  # Face optional
    
    # Create wire object
    wire_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Wire")
    wire_obj.Shape = wire
    wire_obj.ViewObject.ShapeColor = colors['wire']
    wire_obj.ViewObject.LineWidth = 3
    objects.append(wire_obj)
    
    # Create shrunk wire
    try:
        shrunk_wire = wire.makeOffset2D(OFFSET_DIST)
        
        # Validate it's closed
        if not shrunk_wire.isClosed():
            raise ValueError("Shrunk wire not closed")
        
        shrunk_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Shrunk")
        shrunk_obj.Shape = shrunk_wire
        shrunk_obj.ViewObject.ShapeColor = colors['shrunk']
        shrunk_obj.ViewObject.LineWidth = 2
        objects.append(shrunk_obj)
        
        print(f"   Shrunk: {len(shrunk_wire.Edges)} edges")
        
    except Exception as e:
        print(f"❌ Shrunk wire failed: {e}")
        return None, None
    
    # Add point markers for Outline only
    if object_prefix == "Outline":
        add_point_markers(segments, doc, object_prefix)
    
    # Get points for grid
    all_points = []
    for _, points in segments:
        all_points.extend(points)
    
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
    
    # Ensure output folder
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # New document
    doc_name = f"Rudder_Outline_{BOAT_NAME}"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")
    
    # Process Profile
    print("\n📋 PROFILE:")
    profile_objects, profile_points = process_csv(PROFILE_CSV, "Profile", PROFILE_COLORS, doc)
    
    # Process Outline
    print("\n📋 OUTLINE:")
    outline_objects, outline_points = process_csv(OUTLINE_CSV, "Outline", OUTLINE_COLORS, doc)
    
    # Export STEP files
    if profile_objects:
        path = f"{OUTPUT_FOLDER}/{PROFILE_STEP}"
        Part.export(profile_objects, path)
        print(f"✅ Exported: {path}")
    
    if outline_objects:
        path = f"{OUTPUT_FOLDER}/{OUTLINE_STEP}"
        Part.export(outline_objects, path)
        print(f"✅ Exported: {path}")
    
    # Draw grid (use outline points if available)
    grid_points = outline_points if outline_points else profile_points
    if grid_points:
        draw_grid(grid_points, doc)
    
    # Finalize
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()
    
    print(f"\n🚤 {BOAT_NAME} complete!")
    print(f"📁 Files in: {OUTPUT_FOLDER}")