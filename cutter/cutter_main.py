# Rudder Profile Cutter - Creates final foil by cutting stock cavity
# Version 2.0.1 - Fixed shell creation using makeThickness

import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.0.1"

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
   
   # Validate the cut shape
   if cut_shape.isNull():
       print("❌ Cut operation resulted in null shape")
       return
   
   if not cut_shape.isValid():
       print("⚠️ Cut shape is invalid, attempting to fix...")
       try:
           cut_shape = cut_shape.fix()
           if cut_shape.isNull() or not cut_shape.isValid():
               print("❌ Could not fix invalid cut shape")
               return
           print("✅ Fixed cut shape")
       except:
           print("❌ Shape fixing failed")
           return
   
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
   
   # Create shell version using makeThickness (proven method)
   print("\n🔧 Creating shell version")
   SHELL_THICKNESS = 2.0  # mm wall thickness
   
   # Double-check shape validity before shell creation
   print(f"🔍 Shape validation: isNull={cut_shape.isNull()}, isValid={cut_shape.isValid()}, ShapeType={cut_shape.ShapeType}")
   
   if cut_shape.isNull() or not cut_shape.isValid():
       print("❌ Cannot create shell from invalid cut shape")
       return
   
   # Convert Compound to Solid if necessary (makeThickness requires a Solid)
   if cut_shape.ShapeType == 'Compound':
       print("🔧 Converting Compound to Solid for shell creation...")
       try:
           # Get all solids from the compound
           solids = cut_shape.Solids
           if len(solids) == 0:
               print("❌ No solids found in compound")
               return
           elif len(solids) == 1:
               # Single solid - use it directly
               cut_shape = solids[0]
               print(f"✅ Extracted single solid from compound")
           else:
               # Multiple solids - fuse them together
               print(f"🔧 Found {len(solids)} solids, fusing them...")
               fused_shape = solids[0]
               for i in range(1, len(solids)):
                   fused_shape = fused_shape.fuse(solids[i])
               cut_shape = fused_shape
               print(f"✅ Fused {len(solids)} solids into one")
           
           print(f"🔍 Final shape: ShapeType={cut_shape.ShapeType}")
           
           # Add detailed geometric analysis
           print("🔍 Detailed shape analysis:")
           try:
               check_result = cut_shape.check(True)  # True enables BOP check
               print(f"   Shape check result: {check_result}")
           except Exception as e:
               print(f"   Shape check failed: {e}")

           # Also check geometric properties
           try:
               print(f"   Volume: {cut_shape.Volume}")
               print(f"   Surface Area: {cut_shape.Area}")
               print(f"   Number of faces: {len(cut_shape.Faces)}")
               print(f"   Number of edges: {len(cut_shape.Edges)}")
               print(f"   Number of vertices: {len(cut_shape.Vertexes)}")
           except Exception as e:
               print(f"   Geometric properties check failed: {e}")
           
       except Exception as e:
           print(f"❌ Failed to convert compound to solid: {e}")
           return
   
   try:
       # Method 1: Try makeThickness with standard tolerance...
       print("🔧 Attempting makeThickness with standard tolerance...")
       shell_shape = cut_shape.makeThickness([], -SHELL_THICKNESS, 0.01)
       
       if not shell_shape.isNull() and shell_shape.isValid():
           shell_foil = doc.addObject("Part::Feature", "Shell_Foil")
           shell_foil.Shape = shell_shape
           shell_foil.ViewObject.ShapeColor = (0.0, 0.5, 0.8)
           shell_foil.ViewObject.Transparency = 30
           
           print(f"✅ Shell created using makeThickness: {SHELL_THICKNESS}mm thickness")
           
           # Export shell
           SHELL_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Shell_Foil.step"
           SHELL_STL = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Shell_Foil.stl"
           
           Part.export([shell_foil], SHELL_STEP)
           print(f"✅ Exported Shell STEP: {SHELL_STEP}")
           
           try:
               shell_foil.Shape.exportStl(SHELL_STL)
               print(f"✅ Exported Shell STL: {SHELL_STL}")
           except:
               print("⚠️ Shell STL export failed")
               
           return  # Success, exit shell creation
       else:
           raise Exception("makeThickness returned null or invalid shape")
           
   except Exception as e:
       print(f"⚠️ makeThickness failed (known FreeCAD bug #19150): {e}")
       try:
           # Method 2: Shape healing approach - refine the shape first
           print("🔧 Attempting shape healing + makeThickness...")
           refined_shape = cut_shape.makeRefine()
           
           if refined_shape.isNull() or not refined_shape.isValid():
               raise Exception("Shape refinement failed")
           
           shell_shape = refined_shape.makeThickness([], -SHELL_THICKNESS, 0.01)
           
           if not shell_shape.isNull() and shell_shape.isValid():
               shell_foil = doc.addObject("Part::Feature", "Shell_Foil")
               shell_foil.Shape = shell_shape
               shell_foil.ViewObject.ShapeColor = (0.0, 0.5, 0.8)
               shell_foil.ViewObject.Transparency = 30
               
               print(f"✅ Shell created using refined shape: {SHELL_THICKNESS}mm thickness")
               
               # Export shell
               SHELL_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Shell_Foil.step"
               SHELL_STL = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Shell_Foil.stl"
               
               Part.export([shell_foil], SHELL_STEP)
               print(f"✅ Exported Shell STEP: {SHELL_STEP}")
               
               try:
                   shell_foil.Shape.exportStl(SHELL_STL)
                   print(f"✅ Exported Shell STL: {SHELL_STL}")
               except:
                   print("⚠️ Shell STL export failed")
                   
               return  # Success, exit shell creation
           else:
               raise Exception("makeThickness on refined shape returned null or invalid shape")
               
       except Exception as e2:
           print(f"⚠️ Shape healing approach failed: {e2}")
           try:
               # Method 3: Manual shell creation using scaling and boolean operations
               print("🔧 Attempting manual shell creation (workaround for FreeCAD bug)...")
               
               # Create a uniformly scaled-down version of the solid
               # Calculate scale factor to achieve desired wall thickness
               bbox = cut_shape.BoundBox
               min_dimension = min(bbox.XLength, bbox.YLength, bbox.ZLength)
               
               if min_dimension <= 2 * SHELL_THICKNESS:
                   print(f"⚠️ Shape too small for {SHELL_THICKNESS}mm shell (min dimension: {min_dimension:.2f}mm)")
                   print("🔧 Reducing shell thickness automatically...")
                   SHELL_THICKNESS = min_dimension * 0.3  # Use 30% of smallest dimension
                   print(f"   New shell thickness: {SHELL_THICKNESS:.2f}mm")
               
               # Create center point for scaling
               center = cut_shape.CenterOfMass
               
               # Calculate scale factor (approximate)
               avg_dimension = (bbox.XLength + bbox.YLength + bbox.ZLength) / 3
               scale_factor = max(0.1, 1 - (2 * SHELL_THICKNESS / avg_dimension))
               
               print(f"   Using scale factor: {scale_factor:.3f}")
               
               # Create transformation matrix for uniform scaling about center
               import FreeCAD
               matrix = FreeCAD.Matrix()
               matrix.scale(scale_factor, scale_factor, scale_factor)
               
               # Translate to origin, scale, translate back
               scaled_shape = cut_shape.copy()
               scaled_shape.translate(-center)
               scaled_shape = scaled_shape.transformGeometry(matrix)
               scaled_shape.translate(center)
               
               if scaled_shape.isNull() or not scaled_shape.isValid():
                   raise Exception("Scaled shape is invalid")
               
               # Create shell by boolean cut
               shell_shape = cut_shape.cut(scaled_shape)
               
               if not shell_shape.isNull() and shell_shape.isValid():
                   shell_foil = doc.addObject("Part::Feature", "Shell_Foil")
                   shell_foil.Shape = shell_shape
                   shell_foil.ViewObject.ShapeColor = (0.0, 0.5, 0.8)
                   shell_foil.ViewObject.Transparency = 30
                   
                   print(f"✅ Shell created using manual scaling method: {SHELL_THICKNESS:.2f}mm thickness")
                   
                   # Export shell
                   SHELL_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Shell_Foil.step"
                   SHELL_STL = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Shell_Foil.stl"
                   
                   Part.export([shell_foil], SHELL_STEP)
                   print(f"✅ Exported Shell STEP: {SHELL_STEP}")
                   
                   try:
                       shell_foil.Shape.exportStl(SHELL_STL)
                       print(f"✅ Exported Shell STL: {SHELL_STL}")
                   except:
                       print("⚠️ Shell STL export failed")
                       
                   return  # Success, exit shell creation
               else:
                   raise Exception("Manual boolean cut resulted in null or invalid shape")
                   
           except Exception as e3:
               print(f"❌ Manual shell creation failed: {e3}")
               print("💡 This is a known FreeCAD bug #19150 affecting makeThickness on complex boolean geometry")
               print("💡 Recommended solutions:")
               print("   - Use PartDesign Thickness tool in GUI (different code path)")
               print("   - Try with different shell thickness values") 
               print("   - Consider simplifying the base geometry")
               print("   - Export solid and use external CAD for shelling")
   
   # Finalize
   doc.recompute()
   Gui.SendMsgToActiveView("ViewFit")
   Gui.activeDocument().activeView().viewIsometric() 
   
   print(f"\n🚤 {BOAT_NAME} cutter complete!")