# Macros/VisualStep3.py

import sys, os
# Add project root so we can import outline modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

import FreeCAD as App
import FreeCADGui as Gui
import Part
from outline.csv_io import read_transform_csv
from FreeCAD import Vector

def run():
    # 1) New document
    doc_name = "VisualStep3"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")

    # 2) Load points and build wire
    csv_path = os.path.expanduser("~/Documents/FreeCAD/RudderArcs.csv")
    pts2d = read_transform_csv(csv_path)
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

    # 3) Filled face
    face = Part.Face(wire)
    fill_obj = doc.addObject("Part::Feature", "Rudder_Fill")
    fill_obj.Shape = face
    fill_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.6)
    fill_obj.ViewObject.Transparency = 70

    # 4) Outline on top
    out_obj = doc.addObject("Part::Feature", "Rudder_Outline")
    out_obj.Shape = wire
    out_obj.ViewObject.ShapeColor = (0.3, 1.0, 0.3)
    out_obj.ViewObject.LineWidth = 2

    # 5) Shrunk (offset) wire
    shrunk_wire = wire.makeOffset2D(-2)
    shrunk_obj = doc.addObject("Part::Feature", "Rudder_Shrunk")
    shrunk_obj.Shape = shrunk_wire
    shrunk_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)
    shrunk_obj.ViewObject.LineWidth = 2

    # 6) Fit view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == "__main__":
    run()