# Macros/TestBoxMacro.py

import FreeCAD as App
import FreeCADGui as Gui
from rudderlib_foil.simple_model import create_test_box

def run():
    # 1) New document
    doc_name = "TestBoxDoc"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)

    # 2) Create a 100×50×30 mm box
    box = create_test_box(100.0, 50.0, 30.0)

    # 3) Add to document
    feat = doc.addObject("Part::Feature", "TestBox")
    feat.Shape = box

    # 4) Recompute & fit view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

# Run when macro is executed
if __name__ == "__main__":
    run()