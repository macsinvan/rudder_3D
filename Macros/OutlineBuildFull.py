# Macros/OutlineBuildFull.py
"""
Comprehensive Rudder Outline Builder - Boat-Centric Version
Processes both Profile and Outline CSV files with explicit geometry.
Creates separate objects and exports for each.
Everything organized by boat name.
"""
import sys, os, time
from PySide2 import QtWidgets

# Add project root so Python finds our modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
import csv

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth - change this for different boats
VERSION = "2.2.0"  # Updated for dual CSV processing

# Derived paths - everything flows from boat name
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/input"
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/01_outline"

# File specifications
PROFILE_CSV = f"{BOAT_NAME}_Rudder_Profile.csv"
OUTLINE_CSV = f"{BOAT_NAME}_Rudder_Outline.csv"
PROFILE_STEP = f"{BOAT_NAME}_Profile.step"
OUTLINE_STEP = f"{BOAT_NAME}_Outline.step"

# Parameters
OFFSET_DIST = -5.0  # mm inward offset for shrink
GRID_SPACING = 10   # mm grid spacing
GRID_MARGIN = 50    # mm beyond bounds
MACRO_NAME = f"Rudder_Outline_{BOAT_NAME}"

# Color schemes for visual distinction
PROFILE_COLORS = {
    'fill': (1.0, 0.8, 0.6),      # Light orange
    'wire': (1.0, 0.5, 0.0),      # Orange
    'shrunk': (0.8, 0.2, 0.0),    # Dark orange
    'points': (1.0, 0.0, 0.0)     # Red
}

OUTLINE_COLORS = {
    'fill': (0.6, 0.8, 1.0),      # Light blue  
    'wire': (0.0, 0.5, 1.0),      # Blue
    'shrunk': (0.0, 0.2, 0.8),    # Dark blue
    'points': (0.0, 0.0, 1.0)     # Blue
}


def read_explicit_csv(path: str):
    """
    Read CSV with SEGMENT block format:
    SEGMENT,LINE
    x1,y1
    x2,y2
    SEGMENT,ARC
    x1,y1
    x2,y2
    x3,y3
    etc.
    """
    segments = []
    current_type = None
    current_points = []
    
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        reading_coordinates = False
        
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
                
            # Look for coordinate section header
            if len(row) >= 2 and row[0].strip().upper() == 'X' and row[1].strip().upper() == 'Y':
                reading_coordinates = True
                continue
                
            if not reading_coordinates:
                continue
                
            # Check if this is a SEGMENT header
            if len(row) >= 2 and row[0].strip().upper() == 'SEGMENT':
                # Save previous segment if we have one
                if current_type and current_points:
                    segments.append((current_type, current_points.copy()))
                
                # Start new segment
                current_type = row[1].strip().lower()
                current_points = []
                continue
            
            # Try to parse as coordinate point
            if len(row) >= 2:
                try:
                    x = float(row[0].strip())
                    y = float(row[1].strip())
                    # Transform: CSV Y becomes FreeCAD -Z (consistent with existing system)
                    current_points.append((x, -y))
                except ValueError:
                    continue
    
    # Don't forget the last segment
    if current_type and current_points:
        segments.append((current_type, current_points.copy()))
    
    print(f"   📐 Parsed {len(segments)} geometry segments:")
    for i, (seg_type, points) in enumerate(segments):
        start_pt = points[0] if points else "none"
        end_pt = points[-1] if points else "none"
        print(f"      {i}: {seg_type.upper()} with {len(points)} points: {start_pt} -> {end_pt}")
    
    return segments


def create_edges_from_segments(segments):
    """
    Create FreeCAD edges from geometry segments.
    """
    edges = []
    
    for seg_type, points in segments:
        if not points:
            continue
            
        try:
            if seg_type == 'line':
                if len(points) >= 2:
                    for i in range(len(points) - 1):
                        p1 = Vector(points[i][0], 0, points[i][1])
                        p2 = Vector(points[i+1][0], 0, points[i+1][1])
                        edges.append(Part.makeLine(p1, p2))
                        
            elif seg_type == 'arc':
                if len(points) == 3:
                    p1 = Vector(points[0][0], 0, points[0][1])
                    p2 = Vector(points[1][0], 0, points[1][1])
                    p3 = Vector(points[2][0], 0, points[2][1])
                    edges.append(Part.Arc(p1, p2, p3).toShape())
                else:
                    print(f"      ⚠️ Arc needs exactly 3 points, got {len(points)}")
                    
            elif seg_type == 'curve':
                if len(points) >= 2:
                    # Create B-spline through all points
                    vectors = [Vector(p[0], 0, p[1]) for p in points]
                    if len(vectors) >= 2:
                        # For 2 points, make a line
                        if len(vectors) == 2:
                            edges.append(Part.makeLine(vectors[0], vectors[1]))
                        else:
                            # For 3+ points, make a spline
                            try:
                                spline = Part.BSplineCurve()
                                spline.interpolate(vectors)
                                edges.append(spline.toShape())
                            except:
                                # Fallback to lines if spline fails
                                for i in range(len(vectors) - 1):
                                    edges.append(Part.makeLine(vectors[i], vectors[i+1]))
                                    
        except Exception as e:
            print(f"      ⚠️ Failed to create {seg_type}: {e}")
            # Fallback: create lines between consecutive points
            for i in range(len(points) - 1):
                p1 = Vector(points[i][0], 0, points[i][1])
                p2 = Vector(points[i+1][0], 0, points[i+1][1])
                edges.append(Part.makeLine(p1, p2))
    
    print(f"   ✅ Created {len(edges)} edges from segments")
    return edges


def process_csv_file(csv_filename, object_prefix, colors, doc):
    """
    Process a single CSV file and create FreeCAD objects.
    Returns (objects_for_export, all_points) or (None, None) if file not found.
    """
    csv_path = f"{INPUT_FOLDER}/{csv_filename}"
    
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_filename} not found, skipping...")
        return None, None
    
    print(f"🔄 Processing {csv_filename}...")
    
    # Parse CSV and create geometry
    segments = read_explicit_csv(csv_path)
    if not segments:
        print(f"   ❌ No segments found in {csv_filename}")
        return None, None
    
    edges = create_edges_from_segments(segments)
    if not edges:
        print(f"   ❌ No edges created from {csv_filename}")
        return None, None
    
    # Build wire
    try:
        wire = Part.Wire(edges)
        if not wire.isClosed():
            # Try to close the wire
            last_pt = wire.Edges[-1].Vertexes[-1].Point
            first_pt = wire.Edges[0].Vertexes[0].Point
            if last_pt.distanceToPoint(first_pt) > 0.1:  # If not already connected
                closing_edge = Part.makeLine(last_pt, first_pt)
                wire = Part.Wire(edges + [closing_edge])
                print(f"   🔗 Added closing edge to complete wire")
    except Exception as e:
        print(f"   ❌ Failed to create wire: {e}")
        return None, None

    # Create objects with proper naming
    objects_for_export = []
    
    # Fill object
    try:
        face = Part.Face(wire)
        fill_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Fill")
        fill_obj.Shape = face
        fill_obj.ViewObject.ShapeColor = colors['fill']
        fill_obj.ViewObject.Transparency = 70
    except Exception as e:
        print(f"   ⚠️ Could not create face: {e}")

    # Wire object
    wire_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Wire")
    wire_obj.Shape = wire
    wire_obj.ViewObject.ShapeColor = colors['wire']
    wire_obj.ViewObject.LineWidth = 3
    objects_for_export.append(wire_obj)

    # Shrunk wire
    try:
        shrunk_wire = wire.makeOffset2D(OFFSET_DIST)
        shrunk_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Shrunk")
        shrunk_obj.Shape = shrunk_wire
        shrunk_obj.ViewObject.ShapeColor = colors['shrunk']
        shrunk_obj.ViewObject.LineWidth = 2
        objects_for_export.append(shrunk_obj)
    except Exception as e:
        print(f"   ⚠️ Could not create shrunk wire: {e}")

    # Get all points for grid and visualization
    all_points = []
    for seg_type, points in segments:
        all_points.extend(points)

    # Plot points with segment-specific colors
    point_colors = {'line': colors['points'], 'arc': (0.0, 1.0, 0.0), 'curve': (0.0, 0.0, 1.0)}
    point_counter = 0
    for seg_type, points in segments:
        color = point_colors.get(seg_type, colors['points'])
        for x, z in points:
            s = Part.makeSphere(2.0, Vector(x, 0, z))
            obj = doc.addObject("Part::Feature", f"{object_prefix}_Pt_{point_counter}_{seg_type}")
            obj.Shape = s
            obj.ViewObject.ShapeColor = color
            point_counter += 1

    print(f"   ✅ Created {object_prefix} objects with {len(segments)} segments")
    return objects_for_export, all_points


def ensure_output_folder():
    """Ensure output folder exists for this boat"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def run():
    print(f"\n🚤 Rudder Outline Builder v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📂 Boat folder: {BOAT_FOLDER}")
    print(f"📐 Mode: Dual CSV processing (Profile + Outline)")
    
    # Ensure output folder exists
    ensure_output_folder()
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

    # Process Profile CSV
    print(f"\n📋 PROFILE PROCESSING:")
    profile_objects, profile_points = process_csv_file(PROFILE_CSV, "Profile", PROFILE_COLORS, doc)
    
    # Process Outline CSV
    print(f"\n📋 OUTLINE PROCESSING:")
    outline_objects, outline_points = process_csv_file(OUTLINE_CSV, "Outline", OUTLINE_COLORS, doc)
    
    # Check if we got any valid results
    if not profile_objects and not outline_objects:
        print("❌ No valid CSV files found. Aborting.")
        return
    
    # Export Profile objects
    if profile_objects:
        profile_step_path = f"{OUTPUT_FOLDER}/{PROFILE_STEP}"
        try:
            Part.export(profile_objects, profile_step_path)
            print(f"✅ Exported Profile STEP: {profile_step_path}")
        except Exception as e:
            print(f"❌ Profile STEP export failed: {e}")
    
    # Export Outline objects  
    if outline_objects:
        outline_step_path = f"{OUTPUT_FOLDER}/{OUTLINE_STEP}"
        try:
            Part.export(outline_objects, outline_step_path)
            print(f"✅ Exported Outline STEP: {outline_step_path}")
        except Exception as e:
            print(f"❌ Outline STEP export failed: {e}")

    # Draw grid (use outline points if available, otherwise profile points)
    grid_points = outline_points if outline_points else profile_points
    if grid_points:
        print(f"\n🔧 Drawing grid based on {len(grid_points)} points...")
        xs = [p[0] for p in grid_points]
        zs = [p[1] for p in grid_points]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)
        start_x, end_x = 0, int(max_x) + GRID_MARGIN
        start_z, end_z = 0, int(min_z) - GRID_MARGIN

        # Vertical lines
        for x in range(start_x, end_x + 1, GRID_SPACING):
            p1 = Vector(x, 0, start_z)
            p2 = Vector(x, 0, end_z)
            line = Part.makeLine(p1, p2)
            obj = doc.addObject("Part::Feature", f"Grid_V_{x}")
            obj.Shape = line
            color = (0.4,0.4,0.4) if x % (GRID_SPACING*10)==0 else (0.8,0.8,0.8)
            width = 2 if x % (GRID_SPACING*10)==0 else 1
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineWidth = width

        # Horizontal lines
        for z in range(start_z, end_z - 1, -GRID_SPACING):
            p1 = Vector(start_x, 0, z)
            p2 = Vector(end_x, 0, z)
            line = Part.makeLine(p1, p2)
            obj = doc.addObject("Part::Feature", f"Grid_H_{z}")
            obj.Shape = line
            color = (0.4,0.4,0.4) if z % (GRID_SPACING*10)==0 else (0.8,0.8,0.8)
            width = 2 if z % (GRID_SPACING*10)==0 else 1
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineWidth = width

    # Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()
    
    # Summary
    print(f"\n🚤 {BOAT_NAME} dual outline building complete!")
    profile_status = "✅ Profile processed" if profile_objects else "⚠️ Profile skipped"
    outline_status = "✅ Outline processed" if outline_objects else "⚠️ Outline skipped"
    print(f"📐 Results: {profile_status}, {outline_status}")
    print(f"📁 STEP files exported to: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    run()