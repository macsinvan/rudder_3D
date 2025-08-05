# Macros/VisualFullMacro.py
"""
Comprehensive Rudder Visual Macro
Combines CSV import, outline wire, shrink, STEP export, grid, and point plotting.
"""
import sys, os, time
# Add project root so Python finds our modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

import FreeCAD as App
import FreeCADGui as Gui
import Part
from outline.csv_io import read_transform_csv
from FreeCAD import Vector

# Parameters
CSV_REL_PATH = "~/Documents/FreeCAD/RudderArcs.csv"  # user CSV location
OFFSET_DIST = -2.0  # mm inward offset for shrink
GRID_SPACING = 10   # mm grid spacing
GRID_MARGIN = 50    # mm beyond bounds
MACRO_NAME = "Rudder_Visual_Full"


def run():
    # 1) New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

    # 2) Load and transform CSV points
    csv_path = os.path.expanduser(CSV_REL_PATH)
    pts2d = read_transform_csv(csv_path)  # returns [(x,z), ...]
    if not pts2d:
        App.Console.PrintMessage("No points loaded from CSV. Aborting.\n")
        return

    # 3) Build edges and wire
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

    # 4) Display fill, outline, and shrunk wire
    face = Part.Face(wire)
    fill_obj = doc.addObject("Part::Feature", "Rudder_Fill")
    fill_obj.Shape = face
    fill_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.6)
    fill_obj.ViewObject.Transparency = 70

    outline_obj = doc.addObject("Part::Feature", "Rudder_Outline")
    outline_obj.Shape = wire
    outline_obj.ViewObject.ShapeColor = (0.3, 1.0, 0.3)
    outline_obj.ViewObject.LineWidth = 2

    shrunk_wire = wire.makeOffset2D(OFFSET_DIST)
    shrunk_obj = doc.addObject("Part::Feature", "Rudder_Shrunk")
    shrunk_obj.Shape = shrunk_wire
    shrunk_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)
    shrunk_obj.ViewObject.LineWidth = 2

    # 5) Export as STEP
    version = time.strftime("%Y%m%d_%H%M%S")
    step_name = f"RudderProfiles_{version}.step"
    out_dir = os.path.dirname(csv_path)
    step_path = os.path.join(out_dir, step_name)
    Part.export([outline_obj, shrunk_obj], step_path)
    App.Console.PrintMessage(f"Exported STEP to: {step_path}\n")

    # 6) Draw grid
    xs = [p[0] for p in pts2d]
    zs = [p[1] for p in pts2d]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    start_x, end_x = 0, int(max_x) + GRID_MARGIN
    start_z, end_z = 0, int(min_z) - GRID_MARGIN

    # vertical lines
    for x in range(start_x, end_x + 1, GRID_SPACING):
        p1 = Vector(x, 0, start_z);
        p2 = Vector(x, 0, end_z);
        line = Part.makeLine(p1, p2)
        obj = doc.addObject("Part::Feature", f"Grid_V_{x}")
        obj.Shape = line
        color = (0.4,0.4,0.4) if x % (GRID_SPACING*10)==0 else (0.8,0.8,0.8)
        width = 2 if x % (GRID_SPACING*10)==0 else 1
        obj.ViewObject.ShapeColor = color; obj.ViewObject.LineWidth = width

    # horizontal lines
    for z in range(start_z, end_z - 1, -GRID_SPACING):
        p1 = Vector(start_x, 0, z);
        p2 = Vector(end_x, 0, z);
        line = Part.makeLine(p1, p2)
        obj = doc.addObject("Part::Feature", f"Grid_H_{z}")
        obj.Shape = line
        color = (0.4,0.4,0.4) if z % (GRID_SPACING*10)==0 else (0.8,0.8,0.8)
        width = 2 if z % (GRID_SPACING*10)==0 else 1
        obj.ViewObject.ShapeColor = color; obj.ViewObject.LineWidth = width

    # 7) Plot points
    for i,(x,z) in enumerate(pts2d):
        s = Part.makeSphere(1.5, Vector(x, 0, z))
        obj = doc.addObject("Part::Feature", f"Pt_{i}")
        obj.Shape = s
        obj.ViewObject.ShapeColor = (1.0,0.0,0.0)

    # 8) Fit view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == "__main__":
    run()
