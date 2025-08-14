# Macros/FoilBuildFull.py
"""
Foil Build Full Pipeline
Converts STEP outline profiles to 3D NACA foil via chord slicing and lofting.
"""

import sys, os
# Ensure our packages are findable
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)  # so 'outline' package is found
sys.path.insert(0, os.path.join(project, "foil"))  # so 'rudderlib_foil' package is found

from PySide2 import QtWidgets
import FreeCAD as App, FreeCADGui as Gui, Part
from FreeCAD import Vector
from outline.geometry import slice_chords
from rudderlib_foil.naca import naca4_coordinates

# Configuration - Easily adjustable parameters
CONFIG = {
    # NACA Profile Settings
    'naca_profile': '0012',      # NACA 4-digit code (0012 = 12% thick, symmetric)
    'naca_points': 50,           # Number of points in airfoil cross-section
    
    # Slicing Settings  
    'slice_spacing': 10.0,       # mm between chord slices (smaller = more sections)
    'min_chord_length': 1.0,     # mm minimum chord length to include
    
    # Geometry Settings
    'plane_size': 1000,          # mm size of sectioning planes
    'min_wire_size': 1.0,        # mm minimum wire diagonal for validation
    
    # Visual Settings
    'section_color': (0.0, 0.0, 1.0),      # Blue for airfoil sections
    'orig_wire_color': (1.0, 0.6, 0.6),    # Light red for original outline
    'shrunk_wire_color': (1.0, 0.0, 0.0),  # Red for shrunk outline  
    'loft_color': (0.6, 0.8, 1.0),         # Light blue for final loft
}

# Constants (derived from config)
VERSION = "1.0.1"
SLICE_SPACING = CONFIG['slice_spacing']
PLANE_SIZE = CONFIG['plane_size'] 
NACA_PROFILE = CONFIG['naca_profile']
NACA_POINTS = CONFIG['naca_points']

def run():
    """
    Single full-pipeline macro: outline → chords → NACA sections → loft
    """
    print(f"FoilBuildFull v{VERSION}")
    print(f"Config: NACA {CONFIG['naca_profile']}, {CONFIG['slice_spacing']}mm spacing, {CONFIG['naca_points']} pts/section")
    
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

    # 3) Read outline & shrunk profile with validation
    try:
        compound = Part.read(step_path)
        subs = getattr(compound, 'SubShapes', [compound])
        if len(subs) < 2:
            print("❌ STEP must include outline and shrunk profile.")
            return
        
        # Validate we can create wires
        if not subs[0].Edges or not subs[1].Edges:
            print("❌ STEP shapes must contain edges to form wires.")
            return
            
        orig_wire = Part.Wire(subs[0].Edges)
        shrunk_wire = Part.Wire(subs[1].Edges)
        
        # Validate wires are reasonable
        if orig_wire.BoundBox.DiagonalLength < CONFIG['min_wire_size']:
            print("❌ Original wire too small - check STEP file units.")
            return
        if shrunk_wire.BoundBox.DiagonalLength < CONFIG['min_wire_size']:
            print("❌ Shrunk wire too small - check STEP file units.")
            return
            
        print(f"✅ Loaded wires: Orig={len(orig_wire.Edges)} edges, Shrunk={len(shrunk_wire.Edges)} edges")
        
    except Exception as e:
        print(f"❌ Failed to read STEP file: {e}")
        return

    # Draw original & shrunk wires
    for name, wire, color in [("Orig", orig_wire, CONFIG['orig_wire_color']),
                              ("Shrunk", shrunk_wire, CONFIG['shrunk_wire_color'])]:
        feat = doc.addObject("Part::Feature", f"{name}_Wire")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = color
        feat.ViewObject.LineWidth = 2

    # 4) Slice chords via Part.section with validation
    chords = []
    bb = shrunk_wire.BoundBox
    total_height = bb.ZMax - bb.ZMin
    if total_height < SLICE_SPACING:
        print(f"❌ Wire height ({total_height:.1f}mm) too small for slicing at {SLICE_SPACING}mm intervals.")
        return
        
    levels = [bb.ZMin + i * SLICE_SPACING for i in range(int(total_height / SLICE_SPACING) + 1)]
    print(f"🔪 Slicing {len(levels)} levels from Z={bb.ZMin:.1f} to Z={bb.ZMax:.1f}")
    
    for z in levels:
        plane = Part.makePlane(PLANE_SIZE, PLANE_SIZE, Vector(0, 0, z), Vector(0, 0, 1))
        section = shrunk_wire.section(plane)
        verts = section.Vertexes
        if len(verts) >= 2:
            pts = sorted([v.Point for v in verts], key=lambda p: p.x)
            chord_length = pts[-1].x - pts[0].x
            if chord_length > CONFIG['min_chord_length']:  # Configurable minimum chord length
                chords.append(((pts[0].x, z), (pts[-1].x, z)))
    
    if not chords:
        print("❌ No valid chords found - check wire geometry.")
        return
    print(f"✅ Found {len(chords)} valid chords for sections.")

    # 5) Generate NACA sections
    sections = []
    for idx, ((x1, z1), (x2, z2)) in enumerate(chords):
        p_le = Vector(x1, 0.0, z1)  # leading edge (minimum x)
        p_te = Vector(x2, 0.0, z2)  # trailing edge (maximum x)
        vec = p_te.sub(p_le)
        length = vec.Length
        ux = vec.normalize()
        uy = ux.cross(Vector(0.0, 0.0, 1.0)).normalize()

        coords = naca4_coordinates(length, float(CONFIG['naca_profile'][2:]), num_pts=CONFIG['naca_points'])
        pts3 = [p_le + ux * x + uy * z for x, z in coords]
        wire = Part.makePolygon(pts3)
        feat = doc.addObject("Part::Feature", f"Section_{idx}")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = CONFIG['section_color']
        feat.ViewObject.LineWidth = 1
        sections.append(feat)
    print(f"Built {len(sections)} sections.")

    # 6) Loft sections in-memory
    shapes = [o.Shape for o in sections]
    try:
        loft = Part.makeLoft(shapes, solid=False, ruled=False)
        lf = doc.addObject("Part::Feature", "Foil_Loft")
        lf.Shape = loft
        lf.ViewObject.ShapeColor = CONFIG['loft_color']
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