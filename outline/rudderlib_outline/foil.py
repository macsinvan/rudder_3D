# macros/create_foil_macro.FCMacro
import FreeCAD, FreeCADGui, Part  
from rudderlib.foil import build_loft, make_cutter

def run():
    step = select_step()
    doc = FreeCAD.newDocument()
    shrunk = import_shrunk(step)
    cutter = make_cutter(shrunk, depth, offset)
    loft = build_loft(shrunk, z_step, naca="0012")
    # … GUI/animation calls …
    doc.recompute()
run()