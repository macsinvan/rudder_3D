# Macros/VisualStep4.py

import sys, os
# add project root so outline modules resolve
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

import FreeCAD as App
import FreeCADGui as Gui
import Part
import time
from outline.csv_io import read_transform_csv
from FreeCAD import Vector

def run():
    # 1) New document
    doc_name = "VisualStep4"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")

    # 2) Load and build wires (reuse VisualStep3 logic)
    csv_path = os.path.expanduser("~/Documents/FreeCAD/RudderArcs.csv")
    pts2d = read_transform_csv(csv_path)
    # build edges
    edges = []
    for i in range(0, len(pts2d) - 2, 2):
        p1 = Vector(pts2d[i][0], 0, pts2d[i][1])
        p2 = Vector(pts2d[i+1][0], 0, pts2d[i+1][1])
        p3 = Vector(pts2d[i+2][0], 0, pts2d[i+2][1])
        try:
            edges.append(Part.Arc(p1, p2, p3).toShape())
        except Exception as e:
            App.Console.PrintMessage(f"Skipping arc {i}-{i+2}: {e}\\n")
    wire = Part.Wire(edges)
    if not wire.isClosed():
        last_pt = wire.Edges[-1].Vertexes[-1].Point
        first_pt = wire.Edges[0].Vertexes[0].Point
        wire = Part.Wire(wire.Edges + [Part.makeLine(last_pt, first_pt)])

    # create shrunk wire
    shrunk_wire = wire.makeOffset2D(-2)

    # 3) Export to STEP
    version = "v11.0"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    step_name = f"RudderProfiles_{version}_{timestamp}.step"
    out_dir = os.path.dirname(csv_path)
    step_path = os.path.join(out_dir, step_name)
    Part.export([wire, shrunk_wire], step_path)
    App.Console.PrintMessage(f"Exported STEP to: {step_path}\n")

    # 4) Draw grid (10 mm spacing) behind outline
    # get bounds
    all_pts = [Vector(x,0,z) for x,z in pts2d]
    xs = [p.x for p in all_pts]
    zs = [p.z for p in all_pts]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    # extend by 50 mm
    start_x, end_x = 0, int(max_x) + 50
    start_z, end_z = 0, int(min_z) - 50

    # vertical lines
    for x in range(start_x, end_x+1, 10):
        p1 = Vector(x, 0, start_z)
        p2 = Vector(x, 0, end_z)
        line = Part.makeLine(p1, p2)
        obj = doc.addObject("Part::Feature", f"Grid_V_{x}")
        obj.Shape = line
        color = (0.4,0.4,0.4) if x % 100 == 0 else (0.8,0.8,0.8)
        width = 2 if x % 100 == 0 else 1
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineWidth = width

    # horizontal lines
    for z in range(start_z, end_z-1, -10):
        p1 = Vector(start_x, 0, z)
        p2 = Vector(end_x, 0, z)
        line = Part.makeLine(p1, p2)
        obj = doc.addObject("Part::Feature", f"Grid_H_{z}")
        obj.Shape = line
        color = (0.4,0.4,0.4) if z % 100 == 0 else (0.8,0.8,0.8)
        width = 2 if z % 100 == 0 else 1
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineWidth = width

    # 5) Plot raw points
    for i,(x,z) in enumerate(pts2d):
        s = Part.makeSphere(1.5, Vector(x, 0, z))
        obj = doc.addObject("Part::Feature", f"Point_{i}")
        obj.Shape = s
        obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)

    # 6) Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == "__main__":
    run()