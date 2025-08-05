# Macros/TestLoftMacro.py

import sys, os
# Add your project folders to sys.path
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, os.path.join(project, "foil"))

import FreeCAD as App
import FreeCADGui as Gui
import Part
from loft import loft_faces, cut_solid

def run():
    # 1) New document
    doc = App.newDocument("LoftTest")

    # 2) Create two rectangular faces in the XY plane
    rect1 = Part.makePlane(10, 5, App.Vector(0, 0, 0),
                           App.Vector(1, 0, 0), App.Vector(0, 1, 0))
    rect2 = Part.makePlane(10, 5, App.Vector(0, 0, 20),
                           App.Vector(1, 0, 0), App.Vector(0, 1, 0))

    # 3) Loft between them
    loft_shape = loft_faces([rect1, rect2], solid=True)
    loft_obj = doc.addObject("Part::Feature", "Loft")
    loft_obj.Shape = loft_shape
    loft_obj.ViewObject.DisplayMode = "Shaded"
    loft_obj.ViewObject.ShapeColor = (0.6, 0.8, 1.0)

    # 4) Create a cutting box overlapping top half
    cutter = Part.makeBox(12, 6, 10, App.Vector(-1, -1, 10))
    cut_shape = cut_solid(loft_shape, cutter)
    cut_obj = doc.addObject("Part::Feature", "LoftCut")
    cut_obj.Shape = cut_shape
    cut_obj.ViewObject.DisplayMode = "Shaded"
    cut_obj.ViewObject.ShapeColor = (1.0, 0.4, 0.4)

    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    # ensure we see the model
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().viewFront()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()          # true front
    Gui.activeDocument().activeView().viewAxonometric()    # axonometric

if __name__ == "__main__":
    run()