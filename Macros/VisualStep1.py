# Macros/VisualStep1.py

import sys, os
# ensure our project root is on the path so Python finds the outline package
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

import FreeCAD as App
import FreeCADGui as Gui
import Part
from outline.csv_io import read_transform_csv
from FreeCAD import Vector

def run():
    # 1) new document
    doc_name = "VisualStep1"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")

    # 2) load points
    csv_path = os.path.expanduser("~/Documents/FreeCAD/RudderArcs.csv")
    pts2d = read_transform_csv(csv_path)    # list of (x,z) tuples

    # 3) plot each as a small sphere
    for i, (x, z) in enumerate(pts2d):
        s = Part.makeSphere(1.0, Vector(x, 0, z))
        obj = doc.addObject("Part::Feature", f"Pt_{i}")
        obj.Shape = s
        obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)

    # 4) fit view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == "__main__":
    run()