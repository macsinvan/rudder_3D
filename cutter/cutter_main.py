# Rudder Profile Cutter - Creates final foil by cutting stock cavity
# Version 3.0.0 - Simplified to only produce cut foil solid

import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "3.0.0"

# Paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
OUTPUT_BASE = f"{BOAT_FOLDER}/output"

# Files
FOIL_STEP = f"{OUTPUT_BASE}/foil/{BOAT_NAME}_Foil.step"
PROFILE_STEP = f"{OUTPUT_BASE}/outline/{BOAT_NAME}_Profile.step"
OUTPUT_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Cut_Foil.step"
OUTPUT_STL = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Cut_Foil.stl"

# Cutter parameters
CUTTER_HEIGHT = 100.0  # mm
CUTTER_MARGIN = 50.0   # mm

def ensure_solid(shape):
    """Convert shape to solid if it's a compound"""
    if shape.ShapeType == 'Solid':
        return shape
    
    if shape.ShapeType == 'Compound':
        solids = shape.Solids
        if len(solids) == 0:
            raise Exception("No solids found in compound")
        elif len(solids) == 1:
            print(f"   Extracted single solid from compound")
            return solids[0]
        else:
            print(f"   Fusing {len(solids)} solids...")
            result = solids[0]
            for i in range(1, len(solids)):
                result = result.fuse(solids[i])
            print(f"   ✅ Fused solids into one")
            return result
    
    raise Exception(f"Cannot convert {shape.ShapeType} to solid")

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
    foil_shape = ensure_solid(foil_shape)
    
    foil = doc.addObject("Part::Feature", "Foil")
    foil.Shape = foil_shape
    print(f"✅ Imported foil as solid")
    
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
    
    # Create cutter shape
    cutter_shape = outer.cut(inner)
    print("✅ Created cutter")
    
    # Align cutter to foil center
    offset = foil_shape.BoundBox.Center - cutter_shape.BoundBox.Center
    cutter_shape.translate(offset)
    
    # Cut foil
    cut_shape = foil_shape.cut(cutter_shape)
    
    # Ensure result is a solid
    cut_shape = ensure_solid(cut_shape)
    
    # Validate
    if cut_shape.isNull():
        print("❌ Cut operation resulted in null shape")
        return
    
    if not cut_shape.isValid():
        print("❌ Cut shape is invalid")
        return
    
    # Create document object for visualization
    cut_foil = doc.addObject("Part::Feature", "Cut_Foil")
    cut_foil.Shape = cut_shape
    cut_foil.ViewObject.ShapeColor = (0.0, 0.8, 0.0)
    
    # Print info
    print(f"\n✅ Cut complete")
    print(f"   Shape type: {cut_shape.ShapeType}")
    print(f"   Volume: {cut_shape.Volume/1000:.1f} cm³")
    print(f"   Surface area: {cut_shape.Area/100:.1f} cm²")
    print(f"   Faces: {len(cut_shape.Faces)}, Edges: {len(cut_shape.Edges)}")
    
    # Export solid
    Part.export([cut_foil], OUTPUT_STEP)
    print(f"✅ Exported STEP: {OUTPUT_STEP}")
    
    try:
        cut_shape.exportStl(OUTPUT_STL)
        print(f"✅ Exported STL: {OUTPUT_STL}")
    except:
        print("⚠️  STL export failed")
    
    # Update view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    print(f"\n🚤 {BOAT_NAME} cut foil complete!")

if __name__ == "__main__":
    run()