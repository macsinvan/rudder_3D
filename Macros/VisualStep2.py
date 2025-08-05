# Macros/VisualStep2.py

import sys, os
# ensure project root on path
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

import FreeCAD as App
import FreeCADGui as Gui
import Part
from outline.csv_io import read_transform_csv
from FreeCAD import Vector

def run():
    # 1) new document
    doc_name = "VisualStep2"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")

    # 2) load transformed points
    csv_path = os.path.expanduser("~/Documents/FreeCAD/RudderArcs.csv")
    pts2d = read_transform_csv(csv_path)    # list of (x,z)

    # 3) build arcs between every triple of points stepping by 2
    edges = []
    for i in range(0, len(pts2d) - 2, 2):
        p1 = Vector(pts2d[i][0], 0, pts2d[i][1])
        p2 = Vector(pts2d[i+1][0], 0, pts2d[i+1][1])
        p3 = Vector(pts2d[i+2][0], 0, pts2d[i+2][1])
        try:
            arc = Part.Arc(p1, p2, p3)
            edges.append(arc.toShape())
        except Exception as e:
            App.Console.PrintMessage(f"Skipping arc {i}-{i+2}: {e}\\n")

    # 4) create the wire (auto-close if needed)
    if not edges:
        App.Console.PrintMessage("No edges to build wire.\\n")
        return

    wire = Part.Wire(edges)
    if not wire.isClosed():
        last_pt = wire.Edges[-1].Vertexes[-1].Point
        first_pt = wire.Edges[0].Vertexes[0].Point
        closing_edge = Part.makeLine(last_pt, first_pt)
        wire = Part.Wire(wire.Edges + [closing_edge])

    # 5) show the wire
    wire_obj = doc.addObject("Part::Feature", "OutlineWire")
    wire_obj.Shape = wire
    wire_obj.ViewObject.ShapeColor = (0.3, 1.0, 0.3)
    wire_obj.ViewObject.LineWidth = 2

    # 6) fit view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == "__main__":
    run()