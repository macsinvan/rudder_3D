# Rudder Profile Cutter - Creates final foil by cutting stock cavity
# Version 2.0.0 - Simplified

import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.0.0"

# Paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
OUTPUT_BASE = f"{BOAT_FOLDER}/output"

# Files
FOIL_STEP = f"{OUTPUT_BASE}/foil/{BOAT_NAME}_Foil.step"
PROFILE_STEP = f"{OUTPUT_BASE}/outline/{BOAT_NAME}_Profile.step"
OUTPUT_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Cut_Foil.step"
OUTPUT_STL = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Cut_Foil.stl"

# Parameters
CUTTER_HEIGHT = 100.0  # mm
CUTTER_MARGIN = 50.0   # mm

def run():
    print(f"\n🔪 Rudder Cutter v{VERSION} for {BOAT_NAME}")
    
    # Ensure output folder
    os.makedirs(os.path.dirname(OUTPUT_STEP), exist_ok=True)
    
    # New document
    doc = App.newDocument(f"Cutter_{BOAT_NAME}")
    Gui.activateWorkbench("PartWorkbench")
    
    # Import foil
    if not os.path.exists(FOIL_STEP):
        print("❌ Foil not found")
        return
    
    foil_shape = Part.read(FOIL_STEP)
    # Ensure solid
    if foil_shape.ShapeType != 'Solid':
        if foil_shape.Shells:
            foil_shape = Part.makeSolid(foil_shape.Shells[0])
    
    foil = doc.addObject("Part::Feature", "Foil")
    foil.Shape = foil_shape
    print(f"✅ Imported foil")
    
    # Import profile and extract shrunk wire
    if not os.path.exists(PROFILE_STEP):
        print("❌ Profile not found")
        return
    
    profile_compound = Part.read(PROFILE_STEP)
    subs = profile_compound.SubShapes if hasattr(profile_compound, 'SubShapes') else [profile_compound]
    
    if len(subs) < 2:
        print("❌ Profile missing shrunk wire")
        return
    
    # Second subshape is shrunk wire
    shrunk_wire = Part.Wire(subs[1].Edges)
    print(f"✅ Extracted shrunk wire: {len(shrunk_wire.Edges)} edges")
    
    # Create cutter (box with hole)
    bbox = shrunk_wire.BoundBox
    
    # Outer box
    outer = Part.makeBox(
        bbox.XLength + 2*CUTTER_MARGIN,
        2*CUTTER_HEIGHT,
        bbox.ZLength + 2*CUTTER_MARGIN,
        Vector(bbox.XMin - CUTTER_MARGIN, -CUTTER_HEIGHT, bbox.ZMin - CUTTER_MARGIN)
    )
    
    # Inner cavity (extrude shrunk wire)
    inner_face = Part.Face(shrunk_wire)
    inner = inner_face.extrude(Vector(0, 2*CUTTER_HEIGHT, 0))
    inner.translate(Vector(0, -CUTTER_HEIGHT, 0))
    
    # Create cutter
    cutter_shape = outer.cut(inner)
    cutter = doc.addObject("Part::Feature", "Cutter")
    cutter.Shape = cutter_shape
    cutter.ViewObject.Transparency = 50
    print("✅ Created cutter")
    
    # Align cutter to foil center
    offset = foil.Shape.BoundBox.Center - cutter.Shape.BoundBox.Center
    cutter_shape = cutter.Shape.copy()
    cutter_shape.translate(offset)
    
    # Cut foil
    cut_shape = foil.Shape.cut(cutter_shape)
    cut_foil = doc.addObject("Part::Feature", "Cut_Foil")
    cut_foil.Shape = cut_shape
    cut_foil.ViewObject.ShapeColor = (0.0, 0.8, 0.0)
    print("✅ Cut complete")
    
    # Export
    Part.export([cut_foil], OUTPUT_STEP)
    print(f"✅ Exported STEP: {OUTPUT_STEP}")
    
    try:
        cut_foil.Shape.exportStl(OUTPUT_STL)
        print(f"✅ Exported STL: {OUTPUT_STL}")
    except:
        print("⚠️ STL export failed")
    
    # Finalize
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    print(f"\n🚤 {BOAT_NAME} cutter complete!")