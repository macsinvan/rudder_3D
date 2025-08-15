# Macros/VisualFullMacro.py
"""
Comprehensive Rudder Visual Macro - Boat-Centric Version
Combines CSV import, outline wire, shrink, STEP export, grid, and point plotting.
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
VERSION = "2.1.0"  # Updated for explicit geometry CSV

# Derived paths - everything flows from boat name
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/input"
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/01_outline"

# File specifications
CSV_FILE = f"{BOAT_NAME}_Rudder_Profile.csv"
STEP_FILE = f"{BOAT_NAME}_Profiles.step"

# Parameters
OFFSET_DIST = -5.0  # mm inward offset for shrink
GRID_SPACING = 10   # mm grid spacing
GRID_MARGIN = 50    # mm beyond bounds
MACRO_NAME = f"Rudder_Visual_{BOAT_NAME}"


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
    
    print(f"📐 Parsed {len(segments)} geometry segments:")
    for i, (seg_type, points) in enumerate(segments):
        start_pt = points[0] if points else "none"
        end_pt = points[-1] if points else "none"
        print(f"   {i}: {seg_type.upper()} with {len(points)} points: {start_pt} -> {end_pt}")
    
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
                    print(f"⚠️ Arc needs exactly 3 points, got {len(points)}")
                    
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
            print(f"⚠️ Failed to create {seg_type}: {e}")
            # Fallback: create lines between consecutive points
            for i in range(len(points) - 1):
                p1 = Vector(points[i][0], 0, points[i][1])
                p2 = Vector(points[i+1][0], 0, points[i+1][1])
                edges.append(Part.makeLine(p1, p2))
    
    print(f"✅ Created {len(edges)} edges from segments")
    return edges

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth - change this for different boats
VERSION = "2.0.0"

# Derived paths - everything flows from boat name
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/input"
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/01_outline"

# File specifications
CSV_FILE = f"{BOAT_NAME}_Rudder_Profile.csv"
STEP_FILE = f"{BOAT_NAME}_Profiles.step"

# Parameters
OFFSET_DIST = -5.0  # mm inward offset for shrink
GRID_SPACING = 10   # mm grid spacing
GRID_MARGIN = 50    # mm beyond bounds
MACRO_NAME = f"Rudder_Visual_{BOAT_NAME}"


def get_csv_path():
    """
    Get CSV path using boat-centric logic:
    1. Try organized location first
    2. Fall back to file dialog if not found
    """
    organized_path = f"{INPUT_FOLDER}/{CSV_FILE}"
    
    if os.path.exists(organized_path):
        print(f"📁 Using organized file: {organized_path}")
        return organized_path
    else:
        print(f"📁 {CSV_FILE} not found in organized location")
        print(f"   Expected: {organized_path}")
        print(f"📁 Opening file dialog for manual selection...")
        
        # Fall back to file dialog
        dlg = QtWidgets.QFileDialog()
        dlg.setWindowTitle(f"Select {BOAT_NAME} Rudder Profile CSV")
        dlg.setNameFilter("CSV files (*.csv)")
        dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        
        if dlg.exec_():
            manual_path = dlg.selectedFiles()[0]
            print(f"📁 User selected: {manual_path}")
            return manual_path
        else:
            print("❌ No file selected. Aborting.")
            return None


def ensure_output_folder():
    """Ensure output folder exists for this boat"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def run():
    print(f"\n🚤 Rudder Visual Full Macro v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📂 Boat folder: {BOAT_FOLDER}")
    print(f"📐 Mode: Explicit geometry CSV parsing")
    
    # 1) Get CSV file path
    csv_path = get_csv_path()
    if not csv_path:
        return
    
    # 2) Ensure output folder exists
    ensure_output_folder()
    
    # 3) New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

    # 4) Load and parse explicit geometry CSV
    segments = read_explicit_csv(csv_path)
    if not segments:
        App.Console.PrintMessage("No geometry segments loaded from CSV. Aborting.\n")
        return

    # 5) Create edges from geometry segments
    edges = create_edges_from_segments(segments)
    if not edges:
        App.Console.PrintMessage("No edges created from segments. Aborting.\n")
        return
    
    # 6) Build wire
    try:
        wire = Part.Wire(edges)
        if not wire.isClosed():
            # Try to close the wire
            last_pt = wire.Edges[-1].Vertexes[-1].Point
            first_pt = wire.Edges[0].Vertexes[0].Point
            if last_pt.distanceToPoint(first_pt) > 0.1:  # If not already connected
                closing_edge = Part.makeLine(last_pt, first_pt)
                wire = Part.Wire(edges + [closing_edge])
                print("🔗 Added closing edge to complete wire")
    except Exception as e:
        App.Console.PrintMessage(f"Failed to create wire: {e}\n")
        return

    # 7) Display fill, outline, and shrunk wire
    try:
        face = Part.Face(wire)
        fill_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Fill")
        fill_obj.Shape = face
        fill_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.6)
        fill_obj.ViewObject.Transparency = 70
    except Exception as e:
        print(f"⚠️ Could not create face: {e}")

    outline_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Outline")
    outline_obj.Shape = wire
    outline_obj.ViewObject.ShapeColor = (0.3, 1.0, 0.3)
    outline_obj.ViewObject.LineWidth = 3

    try:
        shrunk_wire = wire.makeOffset2D(OFFSET_DIST)
        shrunk_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Shrunk")
        shrunk_obj.Shape = shrunk_wire
        shrunk_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)
        shrunk_obj.ViewObject.LineWidth = 2
    except Exception as e:
        print(f"⚠️ Could not create shrunk wire: {e}")
        shrunk_obj = None

    # 8) Export as STEP to organized output folder
    step_path = f"{OUTPUT_FOLDER}/{STEP_FILE}"
    try:
        export_objects = [outline_obj]
        if shrunk_obj:
            export_objects.append(shrunk_obj)
        Part.export(export_objects, step_path)
        print(f"✅ Exported STEP: {step_path}")
    except Exception as e:
        print(f"❌ STEP export failed: {e}")

    # 9) Get all points for grid and visualization
    all_points = []
    for seg_type, points in segments:
        all_points.extend(points)

    # 10) Draw grid
    if all_points:
        xs = [p[0] for p in all_points]
        zs = [p[1] for p in all_points]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)
        start_x, end_x = 0, int(max_x) + GRID_MARGIN
        start_z, end_z = 0, int(min_z) - GRID_MARGIN

        # vertical lines
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

        # horizontal lines
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

        # 11) Plot points with different colors for different segment types
        colors = {'line': (1.0, 0.0, 0.0), 'arc': (0.0, 1.0, 0.0), 'curve': (0.0, 0.0, 1.0)}
        point_counter = 0
        for seg_type, points in segments:
            color = colors.get(seg_type, (0.5, 0.5, 0.5))
            for x, z in points:
                s = Part.makeSphere(2.0, Vector(x, 0, z))
                obj = doc.addObject("Part::Feature", f"Pt_{point_counter}_{seg_type}")
                obj.Shape = s
                obj.ViewObject.ShapeColor = color
                point_counter += 1

    # 12) Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()
    
    print(f"🚤 {BOAT_NAME} explicit geometry processing complete!")
    print(f"📐 Processed {len(segments)} segments with {len(edges)} edges")
    print(f"📁 Next step: Use {step_path} for foil generation")

if __name__ == "__main__":
    run()