# cutter/cutter_main.py
"""
Rudder Profile Cutter - Step 4
Creates final foil by cutting stock cavity into generated foil using profile cutter.

Process:
1. Import foil design from Step 3
2. Import rudder profile from Step 1 
3. Create cutter from shrunk profile (box with hole)
4. Align cutter and stock geometry
5. Cut stock cavity into foil
6. Export finished rudder foil
"""
import os
from PySide2 import QtWidgets

import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth
VERSION = "1.0.0"        # Initial implementation

# Derived paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output"
FOIL_FOLDER = f"{OUTPUT_FOLDER}/foil"
OUTLINE_FOLDER = f"{OUTPUT_FOLDER}/outline" 
CUTTER_FOLDER = f"{OUTPUT_FOLDER}/cut_foil"
STOCK_FOLDER = f"{OUTPUT_FOLDER}/stock"

# Input files from previous steps
FOIL_STEP = f"{BOAT_NAME}_Foil.step"           # From Step 3
PROFILE_STEP = f"{BOAT_NAME}_Profile.step"     # From Step 1 (contains shrunk wire)
STOCK_STEP = f"{BOAT_NAME}_Stock.step"         # From Step 2

# Output file
CUT_FOIL_STEP = f"{BOAT_NAME}_Cut_Foil.step"

# Parameters
CUTTER_HEIGHT = 100.0    # mm - height of cutter box above/below profile
CUTTER_MARGIN = 50.0     # mm - margin around profile for cutter box
MACRO_NAME = f"Rudder_Cutter_{BOAT_NAME}"


def ensure_output_folder():
    """Ensure output folder exists for this boat"""
    os.makedirs(CUTTER_FOLDER, exist_ok=True)


def import_step_file(step_path, doc, object_prefix):
    """
    Import STEP file and return imported objects.
    Returns list of objects or None if import fails.
    """
    if not os.path.exists(step_path):
        print(f"❌ STEP file not found: {step_path}")
        return None
    
    try:
        print(f"📥 Importing {step_path}...")
        
        # Import the STEP file
        imported_shape = Part.read(step_path)
        
        # Create object in document
        obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}")
        obj.Shape = imported_shape
        
        # Basic validation
        edge_count = len(obj.Shape.Edges) if hasattr(obj.Shape, 'Edges') else 0
        print(f"   ✅ Imported: {edge_count} edges, valid: {obj.Shape.isValid()}")
        
        return obj
        
    except Exception as e:
        print(f"❌ Failed to import {step_path}: {e}")
        QtWidgets.QMessageBox.critical(None, "Import Error", f"Failed to import {step_path}:\n{e}")
        return None


def extract_shrunk_wire_from_profile(profile_obj):
    """
    Extract the shrunk wire from the imported profile object.
    Uses the proven approach from foil_3D.py - create wires from edges of subshapes.
    """
    try:
        print(f"🔍 Extracting shrunk wire from profile...")
        print(f"   🔍 Profile shape type: {profile_obj.Shape.ShapeType}")
        print(f"   🔍 Profile shape valid: {profile_obj.Shape.isValid()}")
        
        # Use the proven approach from foil_3D.py
        compound = profile_obj.Shape
        subs = getattr(compound, 'SubShapes', [compound])
        
        print(f"   📊 Profile contains {len(subs)} subshapes")
        
        if len(subs) < 2:
            print(f"   ❌ CRITICAL: Expected 2 subshapes (main + shrunk), found {len(subs)}")
            return None
        
        # Debug: Show subshape details
        valid_subshapes = []
        for i, sub in enumerate(subs):
            edge_count = len(sub.Edges) if hasattr(sub, 'Edges') else 0
            diagonal = sub.BoundBox.DiagonalLength if hasattr(sub, 'BoundBox') else 0
            print(f"   📊 Subshape {i}: {sub.ShapeType}, {edge_count} edges, diagonal: {diagonal:.1f}mm")
            
            if edge_count > 0:
                valid_subshapes.append((sub, diagonal, i))
        
        if len(valid_subshapes) < 2:
            print(f"   ❌ CRITICAL: Need 2 subshapes with edges, found {len(valid_subshapes)}")
            return None
        
        # Sort by diagonal length (smallest first = shrunk wire)
        valid_subshapes.sort(key=lambda x: x[1])
        
        # Create wires from edges (foil_3D.py approach)
        try:
            main_subshape = valid_subshapes[-1][0]    # Largest
            shrunk_subshape = valid_subshapes[0][0]   # Smallest
            
            print(f"   🔧 Creating wires from edges...")
            print(f"      Main: {len(main_subshape.Edges)} edges, diagonal: {valid_subshapes[-1][1]:.1f}mm")
            print(f"      Shrunk: {len(shrunk_subshape.Edges)} edges, diagonal: {valid_subshapes[0][1]:.1f}mm")
            
            # Create shrunk wire from edges
            shrunk_wire = Part.Wire(shrunk_subshape.Edges)
            
            # Validate the wire
            if not shrunk_wire.isValid():
                print(f"   ❌ CRITICAL: Created wire is invalid!")
                return None
            
            print(f"   ✅ Successfully created shrunk wire:")
            print(f"      Wire edges: {len(shrunk_wire.Edges)}")
            print(f"      Wire closed: {shrunk_wire.isClosed()}")
            print(f"      Wire valid: {shrunk_wire.isValid()}")
            print(f"      Wire diagonal: {shrunk_wire.BoundBox.DiagonalLength:.1f}mm")
            
            return shrunk_wire
            
        except Exception as e:
            print(f"   ❌ CRITICAL: Failed to create wire from edges: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to extract shrunk wire: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_profile_cutter(shrunk_wire, doc):
    """
    Create a cutter from the shrunk profile wire.
    Creates a box with a hole matching the shrunk profile shape.
    """
    try:
        print(f"🔧 Creating profile cutter from shrunk wire...")
        
        # Get bounding box of shrunk wire
        bbox = shrunk_wire.BoundBox
        print(f"   📏 Shrunk wire bounds: {bbox.XLength:.1f} x {bbox.ZLength:.1f}mm")
        
        # Create outer box (larger than profile with margins)
        box_x_min = bbox.XMin - CUTTER_MARGIN
        box_x_max = bbox.XMax + CUTTER_MARGIN
        box_z_min = bbox.ZMin - CUTTER_MARGIN  
        box_z_max = bbox.ZMax + CUTTER_MARGIN
        box_y_min = -CUTTER_HEIGHT
        box_y_max = CUTTER_HEIGHT
        
        outer_box = Part.makeBox(
            box_x_max - box_x_min,
            box_y_max - box_y_min, 
            box_z_max - box_z_min,
            Vector(box_x_min, box_y_min, box_z_min)
        )
        
        print(f"   📦 Outer box: {outer_box.BoundBox.XLength:.1f} x {outer_box.BoundBox.YLength:.1f} x {outer_box.BoundBox.ZLength:.1f}mm")
        
        # Create inner shape (hole) from shrunk wire
        # Extrude the shrunk wire to create a solid for cutting
        inner_face = Part.Face(shrunk_wire)
        inner_solid = inner_face.extrude(Vector(0, box_y_max - box_y_min, 0))
        
        # Position the inner solid
        inner_solid.translate(Vector(0, box_y_min, 0))
        
        print(f"   🕳️ Inner solid: {inner_solid.BoundBox.XLength:.1f} x {inner_solid.BoundBox.YLength:.1f} x {inner_solid.BoundBox.ZLength:.1f}mm")
        
        # Create cutter by subtracting inner from outer (box with hole)
        cutter_shape = outer_box.cut(inner_solid)
        
        # Create cutter object
        cutter_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Cutter")
        cutter_obj.Shape = cutter_shape
        cutter_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)  # Yellow
        cutter_obj.ViewObject.Transparency = 50
        
        print(f"   ✅ Created cutter: {len(cutter_shape.Solids)} solid(s)")
        
        return cutter_obj
        
    except Exception as e:
        print(f"❌ Failed to create profile cutter: {e}")
        QtWidgets.QMessageBox.critical(None, "Cutter Creation Error", f"Failed to create profile cutter:\n{e}")
        return None


def align_and_cut_foil(foil_obj, cutter_obj, doc):
    """
    Align the cutter with the foil and perform the cut operation.
    Creates the final foil with stock cavity.
    """
    try:
        print(f"🎯 Aligning cutter and cutting foil...")
        
        # Debug: Check what types of geometry we have
        print(f"   🔍 Foil shape type: {foil_obj.Shape.ShapeType}")
        print(f"   🔍 Foil solids: {len(foil_obj.Shape.Solids) if hasattr(foil_obj.Shape, 'Solids') else 'N/A'}")
        print(f"   🔍 Foil faces: {len(foil_obj.Shape.Faces) if hasattr(foil_obj.Shape, 'Faces') else 'N/A'}")
        print(f"   🔍 Cutter shape type: {cutter_obj.Shape.ShapeType}")
        print(f"   🔍 Cutter solids: {len(cutter_obj.Shape.Solids) if hasattr(cutter_obj.Shape, 'Solids') else 'N/A'}")
        
        # Get bounding boxes for alignment
        foil_bbox = foil_obj.Shape.BoundBox
        cutter_bbox = cutter_obj.Shape.BoundBox
        
        print(f"   📏 Foil bounds: {foil_bbox.XLength:.1f} x {foil_bbox.YLength:.1f} x {foil_bbox.ZLength:.1f}mm")
        print(f"   📏 Cutter bounds: {cutter_bbox.XLength:.1f} x {cutter_bbox.YLength:.1f} x {cutter_bbox.ZLength:.1f}mm")
        
        # Align cutter to foil (center on X and Z, position on Y)
        # The cutter should be positioned to cut through the foil
        offset_x = foil_bbox.Center.x - cutter_bbox.Center.x
        offset_z = foil_bbox.Center.z - cutter_bbox.Center.z
        offset_y = foil_bbox.Center.y - cutter_bbox.Center.y
        
        print(f"   📐 Alignment offset: ({offset_x:.1f}, {offset_y:.1f}, {offset_z:.1f})mm")
        
        # Move cutter to align with foil
        cutter_aligned = cutter_obj.Shape.copy()
        cutter_aligned.translate(Vector(offset_x, offset_y, offset_z))
        
        # Create aligned cutter object for visualization
        aligned_cutter_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Cutter_Aligned")
        aligned_cutter_obj.Shape = cutter_aligned
        aligned_cutter_obj.ViewObject.ShapeColor = (1.0, 0.5, 0.0)  # Orange
        aligned_cutter_obj.ViewObject.Transparency = 70
        
        # Check if foil is a solid - if not, try to make it one
        if foil_obj.Shape.ShapeType != 'Solid' and len(foil_obj.Shape.Solids) == 0:
            print(f"   ⚠️ Foil is not a solid ({foil_obj.Shape.ShapeType}), attempting to create solid...")
            try:
                # Try to make a solid from the shell/compound
                if hasattr(foil_obj.Shape, 'Shells') and foil_obj.Shape.Shells:
                    shell = foil_obj.Shape.Shells[0]
                    foil_solid = Part.makeSolid(shell)
                    print(f"   ✅ Created solid from shell")
                elif hasattr(foil_obj.Shape, 'Faces') and foil_obj.Shape.Faces:
                    # Try to create shell from faces then solid
                    shell = Part.makeShell(foil_obj.Shape.Faces)
                    foil_solid = Part.makeSolid(shell)
                    print(f"   ✅ Created solid from faces")
                else:
                    print(f"   ❌ Cannot create solid - no shells or faces found")
                    foil_solid = foil_obj.Shape
            except Exception as e:
                print(f"   ⚠️ Could not create solid: {e}, using original shape")
                foil_solid = foil_obj.Shape
        else:
            foil_solid = foil_obj.Shape
            print(f"   ✅ Foil is already a solid")
        
        # Perform the cut operation (foil - cutter = foil with cavity)
        print(f"   ✂️ Performing Boolean cut operation...")
        cut_shape = foil_solid.cut(cutter_aligned)
        
        # Create final cut foil object
        cut_foil_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Cut_Foil")
        cut_foil_obj.Shape = cut_shape
        cut_foil_obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0)  # Green
        
        # Validation
        solid_count = len(cut_shape.Solids) if hasattr(cut_shape, 'Solids') else 0
        face_count = len(cut_shape.Faces) if hasattr(cut_shape, 'Faces') else 0
        print(f"   ✅ Cut foil created: {solid_count} solid(s), {face_count} faces, valid: {cut_shape.isValid()}")
        print(f"   🔍 Cut result type: {cut_shape.ShapeType}")
        
        if solid_count == 0 and face_count == 0:
            print(f"   ❌ Critical: No geometry in cut result - Boolean operation completely failed")
            return None
        elif solid_count == 0:
            print(f"   ⚠️ Warning: No solids in cut result - result is surface/shell geometry")
        
        return cut_foil_obj
        
    except Exception as e:
        print(f"❌ Failed to cut foil: {e}")
        QtWidgets.QMessageBox.critical(None, "Cut Operation Error", f"Failed to cut foil:\n{e}")
        return None


def run():
    print(f"\n🔪 Rudder Profile Cutter v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📂 Processing Step 4: Profile cutting operation")
    
    # Ensure output folder exists
    ensure_output_folder()
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

    # Step 1: Import foil design from Step 3
    print(f"\n📥 STEP 1: Importing foil design...")
    foil_path = f"{FOIL_FOLDER}/{FOIL_STEP}"
    foil_obj = import_step_file(foil_path, doc, "Foil")
    if not foil_obj:
        print("❌ Cannot proceed without foil. Run Step 3 first.")
        return

    # Step 2: Import rudder profile from Step 1
    print(f"\n📥 STEP 2: Importing rudder profile...")
    profile_path = f"{OUTLINE_FOLDER}/{PROFILE_STEP}"
    profile_obj = import_step_file(profile_path, doc, "Profile")
    if not profile_obj:
        print("❌ Cannot proceed without profile. Run Step 1 first.")
        return

    # Step 3: Extract shrunk wire from profile
    print(f"\n🔍 STEP 3: Extracting shrunk wire...")
    shrunk_wire = extract_shrunk_wire_from_profile(profile_obj)
    if not shrunk_wire:
        print("❌ Cannot proceed without shrunk wire.")
        return

    # Step 4: Create cutter from shrunk profile
    print(f"\n🔧 STEP 4: Creating profile cutter...")
    cutter_obj = create_profile_cutter(shrunk_wire, doc)
    if not cutter_obj:
        print("❌ Cannot proceed without cutter.")
        return

    # Step 5: Align and cut foil
    print(f"\n✂️ STEP 5: Cutting foil with profile cutter...")
    cut_foil_obj = align_and_cut_foil(foil_obj, cutter_obj, doc)
    if not cut_foil_obj:
        print("❌ Cut operation failed.")
        return

# Step 6: Export finished rudder foil
    print(f"\n💾 STEP 6: Exporting cut foil...")
    cut_foil_path = f"{CUTTER_FOLDER}/{CUT_FOIL_STEP}"
    cut_foil_stl_path = f"{CUTTER_FOLDER}/{BOAT_NAME}_Cut_Foil.stl"
    
    try:
        # Export STEP file for CAD compatibility
        Part.export([cut_foil_obj], cut_foil_path)
        print(f"✅ Exported cut foil STEP: {cut_foil_path}")
        
        # Export STL file for 3D printing
        try:
            cut_foil_obj.Shape.exportStl(cut_foil_stl_path)
            print(f"✅ Exported cut foil STL: {cut_foil_stl_path}")
        except Exception as stl_error:
            print(f"   ❌ STL export failed: {stl_error}")
            print(f"   ℹ️ STEP file is still available for CAD use")
        
        # Validation
        step_size = os.path.getsize(cut_foil_path)
        print(f"   📏 STEP file size: {step_size} bytes")
        
        if os.path.exists(cut_foil_stl_path):
            stl_size = os.path.getsize(cut_foil_stl_path)
            print(f"   📏 STL file size: {stl_size} bytes")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")

    # Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    # Summary
    print(f"\n🚤 {BOAT_NAME} profile cutting complete!")
    print(f"🔪 Cut foil exported to: {cut_foil_path}")
    print(f"📐 Ready for Step 5: Stock integration")