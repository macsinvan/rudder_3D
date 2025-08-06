# Macros/Stock2D.py

import sys, os
import FreeCAD as App
import FreeCADGui as Gui

# 1) Ensure project root on Python path so we can import our modules
project = os.path.expanduser("~/Rudder_Code")
if project not in sys.path:
    sys.path.insert(0, project)

from outline.csv_io   import read_transform_csv
from outline.stock_io import read_stock_csv
from outline.stock2d  import draw_stock_2d

def run():
    # -- 1) New FreeCAD document --
    doc_name = "Stock2D"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")

    # -- 2) Read outline points (optional reuse) --
    outline_csv = "/Users/andrewmackenzie/Documents/FreeCAD/RudderArcs.csv"
    pts = read_transform_csv(outline_csv)
    # TODO: call your existing outline-drawing function here

    # -- 3) Read stock specs and draw them --
    specs = read_stock_csv(outline_csv)
    draw_stock_2d(specs, doc)

    # -- 4) Finalize view --
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == "__main__":
    run()