# Macros/FoilBuildFull.py

import sys, os
# ─── ensure our packages are findable ─────────────────────────
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)                           # so 'outline' package is found
sys.path.insert(0, os.path.join(project, "foil"))  # so 'rudderlib_foil' package is found

from PySide2 import QtWidgets
import FreeCAD as App, FreeCADGui as Gui, Part
from FreeCAD import Vector
from outline.geometry import slice_chords
from rudderlib_foil.naca import naca4_coordinates  # proper import now that paths are set

# Single full-pipeline macro: outline → chords → NACA sections → loft

def run():
    # 1) STEP file selection
    dlg = QtWidgets.QFileDialog()
    dlg.setWindowTitle("Select RudderProfiles STEP")
    dlg.setNameFilter("STEP (*.step *.stp)")
    dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    if not dlg.exec_():
        print("No STEP selected. Aborting.")
        return
    step_path = dlg.selectedFiles()[0]
    print(f"Loading STEP: {step_path}")

    # 2) New document
    doc_name = "FoilBuildFull"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")

    # 3) Read outline & shrunk profile
    compound = Part.read(step_path)
    subs = getattr(compound, 'SubShapes', [compound])
    if len(subs) < 2:
        print("STEP must include outline and shrunk profile.")
        return
    orig_wire   = Part.Wire(subs[0].Edges)
    shrunk_wire = Part.Wire(subs[1].Edges)

    # draw original & shrunk
    for name, wire, color in [("Orig", orig_wire, (1.0, 0.6, 0.6)),
                              ("Shrunk", shrunk_wire, (1.0, 0.0, 0.0))]:
        feat = doc.addObject("Part::Feature", f"{name}_Wire")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = color
        feat.ViewObject.LineWidth = 2

    # 4) Slice chords via Part.section for exact outline intersections
    chords = []
    bb = shrunk_wire.BoundBox
    levels = [bb.ZMin + i * 10.0 for i in range(int((bb.ZMax - bb.ZMin) / 10.0) + 1)]
    for z in levels:
        plane = Part.makePlane(1000, 1000, Vector(0, 0, z), Vector(0, 0, 1))
        section = shrunk_wire.section(plane)
        verts = section.Vertexes
        if len(verts) >= 2:
            pts = sorted([v.Point for v in verts], key=lambda p: p.x)
            chords.append(((pts[0].x, z), (pts[-1].x, z)))
    print(f"Sliced {len(chords)} chords via Part.section.")

    # 5) Generate NACA sections
    sections = []
    for idx, ((x1, z1), (x2, z2)) in enumerate(chords):
        p_te = Vector(x2, 0.0, z2)  # leading edge
        p_le = Vector(x1, 0.0, z1)  # trailing edge
        vec = p_te.sub(p_le)
        length = vec.Length
        ux = vec.normalize()
        uy = ux.cross(Vector(0.0, 0.0, 1.0)).normalize()

        coords = naca4_coordinates(length, float("0012"[2:]), num_pts=50)
        pts3 = [p_le + ux * x + uy * z for x, z in coords]
        wire = Part.makePolygon(pts3)
        feat = doc.addObject("Part::Feature", f"Section_{idx}")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = (0.0, 0.0, 1.0)
        feat.ViewObject.LineWidth = 1
        sections.append(feat)
    print(f"Built {len(sections)} sections.")

    # 6) Loft sections in-memory
    shapes = [o.Shape for o in sections]
    try:
        loft = Part.makeLoft(shapes, solid=False, ruled=False)
        lf = doc.addObject("Part::Feature", "Foil_Loft")
        lf.Shape = loft
        lf.ViewObject.ShapeColor = (0.6, 0.8, 1.0)
        lf.ViewObject.DisplayMode = "Shaded"
        print("✅ Loft created.")
    except Exception as e:
        print(f"Loft failed: {e}")
        return

    # 7) Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == '__main__':
    run()
