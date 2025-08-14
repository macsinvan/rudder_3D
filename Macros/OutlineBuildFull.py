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
from outline.csv_io import read_transform_csv
from FreeCAD import Vector

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
OFFSET_DIST = -2.0  # mm inward offset for shrink
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

    # 4) Load and transform CSV points
    pts2d = read_transform_csv(csv_path)  # returns [(x,z), ...]
    if not pts2d:
        App.Console.PrintMessage("No points loaded from CSV. Aborting.\n")
        return

    # 5) Build edges and wire
    edges = []
    for i in range(0, len(pts2d) - 2, 2):
        p1 = Vector(pts2d[i][0], 0, pts2d[i][1])
        p2 = Vector(pts2d[i+1][0], 0, pts2d[i+1][1])
        p3 = Vector(pts2d[i+2][0], 0, pts2d[i+2][1])
        try:
            edges.append(Part.Arc(p1, p2, p3).toShape())
        except Exception as e:
            App.Console.PrintMessage(f"Skipping arc {i}-{i+2}: {e}\n")
    
    wire = Part.Wire(edges)
    if not wire.isClosed():
        last_pt = wire.Edges[-1].Vertexes[-1].Point
        first_pt = wire.Edges[0].Vertexes[0].Point
        wire = Part.Wire(wire.Edges + [Part.makeLine(last_pt, first_pt)])

    # 6) Display fill, outline, and shrunk wire
    face = Part.Face(wire)
    fill_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Fill")
    fill_obj.Shape = face
    fill_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.6)
    fill_obj.ViewObject.Transparency = 70

    outline_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Outline")
    outline_obj.Shape = wire
    outline_obj.ViewObject.ShapeColor = (0.3, 1.0, 0.3)
    outline_obj.ViewObject.LineWidth = 2

    shrunk_wire = wire.makeOffset2D(OFFSET_DIST)
    shrunk_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Shrunk")
    shrunk_obj.Shape = shrunk_wire
    shrunk_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)
    shrunk_obj.ViewObject.LineWidth = 2

    # 7) Export as STEP to organized output folder
    step_path = f"{OUTPUT_FOLDER}/{STEP_FILE}"
    try:
        Part.export([outline_obj, shrunk_obj], step_path)
        print(f"✅ Exported STEP: {step_path}")
    except Exception as e:
        print(f"❌ STEP export failed: {e}")

    # 8) Draw grid
    xs = [p[0] for p in pts2d]
    zs = [p[1] for p in pts2d]
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

    # 9) Plot points
    for i,(x,z) in enumerate(pts2d):
        s = Part.makeSphere(1.5, Vector(x, 0, z))
        obj = doc.addObject("Part::Feature", f"Pt_{i}")
        obj.Shape = s
        obj.ViewObject.ShapeColor = (1.0,0.0,0.0)

    # 10) Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()
    
    print(f"🚤 {BOAT_NAME} rudder outline processing complete!")
    print(f"📁 Next step: Use {step_path} for foil generation")

if __name__ == "__main__":
    run()