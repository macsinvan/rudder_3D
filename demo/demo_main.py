"""
Demo Model Generator - Step 5A
Creates scaled-down demo model with breakaway connections for single-print assembly demonstration.

Process:
1. Import cut foil from Step 4
2. Import stock from Step 2
3. Scale everything down for demo
4. Create solid foil (no cavity for demo)
5. Add breakaway connections
6. Arrange for optimal printing
7. Export single STL for demo printing
"""
import os
from PySide2 import QtWidgets

import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth
VERSION = "1.0.1"        # Performance optimized

# Derived paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output"
CUT_FOIL_FOLDER = f"{OUTPUT_FOLDER}/cut_foil"
STOCK_FOLDER = f"{OUTPUT_FOLDER}/stock"
DEMO_FOLDER = f"{OUTPUT_FOLDER}/demo"

# Input files from previous steps
CUT_FOIL_STEP = f"{BOAT_NAME}_Cut_Foil.step"     # From Step 4
STOCK_STEP = f"{BOAT_NAME}_Stock.step"           # From Step 2

# Output file
DEMO_STL = f"{BOAT_NAME}_Demo_Model.stl"

# Demo Parameters
TAB_THICKNESS = 0.8      # mm thickness of breakaway tabs
TAB_WIDTH = 4.0          # mm width of breakaway tabs
TAB_COUNT = 3            # Number of tabs connecting parts
PRINT_MARGIN = 5.0       # mm margin between parts on print bed

# HARD-CODED POSITIONING PARAMETERS (for reliable positioning)
STOCK_Z_TOP_POSITION = 80.0   # mm - HARD-CODED stock TOP position (Z coordinate) - scaled for full size
STOCK_Y_POSITION = 0.0        # mm - HARD-CODED stock Y position (centerline)

# CLEARANCE PARAMETERS (for realistic assembly tolerances)
STOCK_CLEARANCE = 2.0    # mm - clearance around stock for real-world assembly tolerances

MACRO_NAME = f"Demo_Model_{BOAT_NAME}"


def ensure_output_folder():
    """Ensure output folder exists for this boat"""
    os.makedirs(DEMO_FOLDER, exist_ok=True)


def import_step_file(step_path, doc, object_prefix):
    """
    Import STEP file and return imported objects.
    Returns object or None if import fails.
    """
    if not os.path.exists(step_path):
        print(f"❌ STEP file not found: {step_path}")
        return None
    
    try:
        print(f"📥 Importing {step_path}...")
        
        # Import the STEP file
        imported_shape = Part.read(step_path)
        
        # Create object in document
        obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_{object_prefix}")
        obj.Shape = imported_shape
        
        # Basic validation
        print(f"   ✅ Imported: type {obj.Shape.ShapeType}, valid: {obj.Shape.isValid()}")
        
        return obj
        
    except Exception as e:
        print(f"❌ Failed to import {step_path}: {e}")
        QtWidgets.QMessageBox.critical(None, "Import Error", f"Failed to import {step_path}:\n{e}")
        return None


def scale_object(obj, scale_factor):
    """
    Scale an object uniformly by the given factor.
    """
    try:
        print(f"📐 Scaling {obj.Name} by factor {scale_factor}...")
        
        # Create scaling matrix
        matrix = App.Matrix()
        matrix.scale(scale_factor, scale_factor, scale_factor)
        
        # Apply scaling
        scaled_shape = obj.Shape.transformGeometry(matrix)
        obj.Shape = scaled_shape
        
        print(f"   ✅ Scaled: new bounds {scaled_shape.BoundBox.XLength:.1f} x {scaled_shape.BoundBox.YLength:.1f} x {scaled_shape.BoundBox.ZLength:.1f}mm")
        return True
        
    except Exception as e:
        print(f"❌ Failed to scale {obj.Name}: {e}")
        return False


def split_foil_for_visualization(cut_foil_obj, doc):
    """
    Split the foil down the middle to show the internal cavity and stock.
    Split along Y-axis (through the chord/thickness).
    PERFORMANCE: Disable view updates during operation.
    """
    try:
        print(f"✂️ Splitting foil through chord for visualization...")
        
        # PERFORMANCE: Disable view updates
        original_visibility = cut_foil_obj.ViewObject.Visibility
        cut_foil_obj.ViewObject.Visibility = False
        
        foil_shape = cut_foil_obj.Shape
        foil_bbox = foil_shape.BoundBox
        
        # Create cutting plane down the middle (XZ plane through center Y)
        cutting_plane_y = foil_bbox.Center.y
        
        # Create a large cutting box that splits the foil through chord
        cutter_box = Part.makeBox(
            foil_bbox.XLength + 10,   # Full width + margin
            foil_bbox.YLength/2 + 1,  # Half thickness + margin
            foil_bbox.ZLength + 10,   # Full length + margin
            Vector(foil_bbox.XMin - 5, cutting_plane_y, foil_bbox.ZMin - 5)
        )
        
        # Split foil into two halves through chord
        upper_half = foil_shape.cut(cutter_box)      # Upper part (smaller Y)
        lower_half = foil_shape.common(cutter_box)   # Lower part (larger Y)
        
        # Create upper half object - HIDDEN initially
        upper_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Foil_Upper")
        upper_obj.Shape = upper_half
        upper_obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0)  # Green
        upper_obj.ViewObject.Visibility = False  # PERFORMANCE: Hidden initially
        
        # Create lower half object - HIDDEN initially
        lower_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Foil_Lower")
        lower_obj.Shape = lower_half
        lower_obj.ViewObject.ShapeColor = (0.0, 0.6, 0.0)  # Darker green
        lower_obj.ViewObject.Visibility = False  # PERFORMANCE: Hidden initially
        
        print(f"   ✅ Split foil into upper and lower halves along Y-axis")
        print(f"   📏 Upper half: {len(upper_half.Faces)} faces")
        print(f"   📏 Lower half: {len(lower_half.Faces)} faces")
        print(f"   📐 Split at Y = {cutting_plane_y:.1f}mm")
        
        return upper_obj, lower_obj
        
    except Exception as e:
        print(f"❌ Failed to split foil: {e}")
        return None, None


def position_stock_in_cavity(upper_foil_obj, lower_foil_obj, stock_obj, doc):
    """
    Position the stock with HARD-CODED positioning for reliability.
    - Applies 180° rotation around Z-axis to orient post toward leading edge
    - HARD-CODED Y position at centerline (Y=0)
    - HARD-CODED Z position with TOP of stock at specified Z coordinate
    """
    try:
        print(f"🎯 Positioning stock with HARD-CODED coordinates...")
        print(f"   📐 HARD-CODED: Stock TOP at Z={STOCK_Z_TOP_POSITION}mm, Y={STOCK_Y_POSITION}mm")
        
        # Use upper half for reference
        foil_bbox = upper_foil_obj.Shape.BoundBox
        stock_bbox = stock_obj.Shape.BoundBox
        
        print(f"   📏 Original stock bounds: Z={stock_bbox.ZMin:.1f} to Z={stock_bbox.ZMax:.1f}mm (height: {stock_bbox.ZLength:.1f}mm)")
        print(f"   📏 Foil bounds: Z={foil_bbox.ZMin:.1f} to Z={foil_bbox.ZMax:.1f}mm (height: {foil_bbox.ZLength:.1f}mm)")
        
        # Create transformation matrix with rotation and translation
        stock_matrix = App.Matrix()
        
        # First rotate 180° around Z-axis to orient post toward leading edge
        stock_matrix.rotateZ(3.14159)  # 180° in radians
        print(f"   🔄 Applied 180° rotation around Z-axis")
        
        # Apply rotation first
        rotated_shape = stock_obj.Shape.transformGeometry(stock_matrix)
        rotated_bbox = rotated_shape.BoundBox
        
        # HARD-CODED position calculation:
        # - X: Center in foil cavity (only this is calculated)
        # - Y: HARD-CODED to centerline
        # - Z: HARD-CODED TOP position
        
        stock_offset = Vector(
            foil_bbox.Center.x - rotated_bbox.Center.x,     # Center on X (calculated)
            STOCK_Y_POSITION - rotated_bbox.Center.y,       # HARD-CODED Y position
            STOCK_Z_TOP_POSITION - rotated_bbox.ZMax        # HARD-CODED Z position (TOP)
        )
        
        # Create translation matrix and apply
        translation_matrix = App.Matrix()
        translation_matrix.move(stock_offset)
        final_shape = rotated_shape.transformGeometry(translation_matrix)
        
        # Update stock object
        stock_obj.Shape = final_shape
        
        # Apply BRIGHT stainless steel appearance - DIFFERENT from foil
        stock_obj.ViewObject.ShapeColor = (0.95, 0.95, 1.0)  # VERY bright stainless steel
        stock_obj.ViewObject.Transparency = 0
        stock_obj.ViewObject.DisplayMode = "Shaded"  # Proper metallic shading
        
        # Get final positioning for verification
        final_bbox = final_shape.BoundBox
        
        print(f"   ✅ Positioned stock with HARD-CODED coordinates")
        print(f"   📐 Stock offset: ({stock_offset.x:.1f}, {stock_offset.y:.1f}, {stock_offset.z:.1f})mm")
        print(f"   📍 Final stock Y-position: {final_bbox.Center.y:.1f}mm (target: {STOCK_Y_POSITION}mm)")
        print(f"   ⬆️  Final stock extends: Z={final_bbox.ZMin:.1f} to Z={final_bbox.ZMax:.1f}mm")
        print(f"   🎯 Stock TOP at Z={final_bbox.ZMax:.1f}mm (target: {STOCK_Z_TOP_POSITION}mm)")
        print(f"   📏 Stock now {final_bbox.ZLength:.1f}mm tall, foil is {foil_bbox.ZLength:.1f}mm tall")
        print(f"   🔩 Applied VERY BRIGHT stainless steel appearance")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to position stock: {e}")
        return False

def create_demo_assembly_clean(upper_foil_obj, lower_foil_obj, stock_obj, doc):
    """
    Create clean demo visualization with separate components.
    Shows split foil halves with cavities and stock as separate object.
    """
    try:
        print(f"🔧 Creating clean demo visualization with separate components...")
        
        # Apply realistic materials to the split foil halves (NO stock fusion)
        # Upper foil half with dark charcoal appearance
        upper_foil_obj.ViewObject.ShapeColor = (0.3, 0.3, 0.4)  # Dark charcoal grey
        upper_foil_obj.ViewObject.Transparency = 5   # Minimal transparency
        upper_foil_obj.ViewObject.DisplayMode = "Shaded"  # Smooth shading
        
        # Lower foil half with darker charcoal appearance
        lower_foil_obj.ViewObject.ShapeColor = (0.2, 0.2, 0.3)  # Darker charcoal grey
        lower_foil_obj.ViewObject.Transparency = 5   # Minimal transparency
        lower_foil_obj.ViewObject.DisplayMode = "Shaded"  # Smooth shading
        
        # Apply bright stainless steel to the separate stock
        stock_obj.ViewObject.ShapeColor = (0.95, 0.95, 1.0)  # Very bright stainless steel
        stock_obj.ViewObject.Transparency = 0
        stock_obj.ViewObject.DisplayMode = "Shaded"  # Metallic shading
        
        # Rename objects for clarity
        upper_foil_obj.Label = f"{BOAT_NAME}_Demo_Upper_Foil"
        lower_foil_obj.Label = f"{BOAT_NAME}_Demo_Lower_Foil"
        stock_obj.Label = f"{BOAT_NAME}_Demo_Stock"
        
        print(f"   ✅ Created clean demo visualization with separate components")
        print(f"   📏 Upper foil faces: {len(upper_foil_obj.Shape.Faces)}")
        print(f"   📏 Lower foil faces: {len(lower_foil_obj.Shape.Faces)}")
        print(f"   📏 Stock faces: {len(stock_obj.Shape.Faces)}")
        print(f"   🎨 Applied dark charcoal grey to foil halves")
        print(f"   🔩 Applied very bright stainless steel to separate stock")
        print(f"   ✨ Using 'Shaded' display mode for realistic appearance")
        print(f"   🔧 Stock remains separate - shows actual assembly method")
        
        return upper_foil_obj, lower_foil_obj, stock_obj
        
    except Exception as e:
        print(f"❌ Failed to create demo visualization: {e}")
        return None, None, None


def run():
    print(f"\n🎭 Demo Model Generator v{VERSION} (Full Size with Clearance)")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📏 Working at FULL SIZE - scale STL files as needed for printing")
    print(f"🔧 Stock clearance: {STOCK_CLEARANCE}mm for realistic assembly tolerances")
    print(f"⚡ Performance mode: Minimal view updates during processing")
    
    # Ensure output folder exists
    ensure_output_folder()
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

    # PERFORMANCE: Process without intermediate recomputes
    # Note: FreeCAD will auto-recompute as needed

    # Step 1: Import cut foil from Step 4
    print(f"\n📥 STEP 1: Importing cut foil...")
    cut_foil_path = f"{CUT_FOIL_FOLDER}/{CUT_FOIL_STEP}"
    cut_foil_obj = import_step_file(cut_foil_path, doc, "CutFoil")
    if not cut_foil_obj:
        print("❌ Cannot proceed without cut foil. Run Step 4 first.")
        return

    # Step 2: Import stock from Step 2
    print(f"\n📥 STEP 2: Importing stock...")
    stock_path = f"{STOCK_FOLDER}/{STOCK_STEP}"
    stock_obj = import_step_file(stock_path, doc, "Stock")
    if not stock_obj:
        print("❌ Cannot proceed without stock. Run Step 2 first.")
        return

    # DEBUG: Make objects visible and exit
    print(f"\n🔍 DEBUG MODE: Showing imported objects and exiting...")
    
    # Force opaque appearance for debugging
    cut_foil_obj.ViewObject.Visibility = True
    cut_foil_obj.ViewObject.Transparency = 0  # Force opaque
    cut_foil_obj.ViewObject.ShapeColor = (0.5, 0.5, 0.5)  # Medium grey
    cut_foil_obj.ViewObject.DisplayMode = "Shaded"
    
    stock_obj.ViewObject.Visibility = True
    stock_obj.ViewObject.Transparency = 0  # Force opaque
    stock_obj.ViewObject.ShapeColor = (0.8, 0.8, 0.9)  # Light steel
    stock_obj.ViewObject.DisplayMode = "Shaded"
    
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    print(f"✅ Debug view complete - Cut foil and Stock are visible")
    print(f"📏 Cut foil bounds: {cut_foil_obj.Shape.BoundBox}")
    print(f"📏 Stock bounds: {stock_obj.Shape.BoundBox}")
    print(f"🎨 Forced opaque appearance (Transparency = 0)")
    return

    # Step 3: Split foil for visualization (through chord along Y-axis)
    print(f"\n✂️ STEP 3: Splitting foil through chord for visualization...")
    upper_foil_obj, lower_foil_obj = split_foil_for_visualization(cut_foil_obj, doc)
    if not upper_foil_obj or not lower_foil_obj:
        print("❌ Failed to split foil.")
        return
    
    # Remove the original cut foil since we have the split versions
    doc.removeObject(cut_foil_obj.Name)
    print(f"   ✅ Removed original cut foil (replaced by split versions)")

    # Step 4: Position stock between the foil halves
    print(f"\n🎯 STEP 4: Positioning stock between halves...")
    if not position_stock_in_cavity(upper_foil_obj, lower_foil_obj, stock_obj, doc):
        print("❌ Failed to position stock.")
        return

    # Step 6: Create clean demo visualization with clearance cavities
    print(f"\n🔧 STEP 6: Creating clean demo visualization with clearance...")
    upper_foil_obj, lower_foil_obj, stock_obj = create_demo_assembly_clean(upper_foil_obj, lower_foil_obj, stock_obj, doc)
    if not upper_foil_obj or not lower_foil_obj or not stock_obj:
        print("❌ Failed to create demo visualization.")
        return

    # Step 7: Export STL for demo printing (export foil halves and stock separately)
    print(f"\n💾 STEP 7: Exporting full-size STL files...")
    
    # Export upper foil half
    upper_stl_path = f"{DEMO_FOLDER}/{BOAT_NAME}_Demo_Upper_Foil.stl"
    try:
        print(f"   🔄 Exporting upper foil half STL...")
        upper_foil_obj.Shape.exportStl(upper_stl_path)
        upper_size = os.path.getsize(upper_stl_path)
        print(f"   ✅ Upper foil: {upper_stl_path} ({upper_size/1024/1024:.1f} MB)")
    except Exception as e:
        print(f"   ❌ Upper STL export failed: {e}")
    
    # Export lower foil half  
    lower_stl_path = f"{DEMO_FOLDER}/{BOAT_NAME}_Demo_Lower_Foil.stl"
    try:
        print(f"   🔄 Exporting lower foil half STL...")
        lower_foil_obj.Shape.exportStl(lower_stl_path)
        lower_size = os.path.getsize(lower_stl_path)
        print(f"   ✅ Lower foil: {lower_stl_path} ({lower_size/1024/1024:.1f} MB)")
    except Exception as e:
        print(f"   ❌ Lower STL export failed: {e}")
        
    # Export stock separately
    stock_stl_path = f"{DEMO_FOLDER}/{BOAT_NAME}_Demo_Stock.stl"
    try:
        print(f"   🔄 Exporting stock STL...")
        stock_obj.Shape.exportStl(stock_stl_path)
        stock_size = os.path.getsize(stock_stl_path)
        print(f"   ✅ Stock: {stock_stl_path} ({stock_size/1024/1024:.1f} MB)")
    except Exception as e:
        print(f"   ❌ Stock STL export failed: {e}")

    # PERFORMANCE: Final recompute to ensure everything is up to date
    print(f"\n🔄 Final recomputation and view setup...")
    doc.recompute()
    
    # Show all three separate components
    upper_foil_obj.ViewObject.Visibility = True
    lower_foil_obj.ViewObject.Visibility = True
    stock_obj.ViewObject.Visibility = True
    
    # Finalize view
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    # Summary
    print(f"\n🎭 {BOAT_NAME} demo model complete!")
    print(f"📏 Working at FULL SIZE - scale STL files as needed for printing")
    print(f"🔧 Stock clearance: {STOCK_CLEARANCE}mm for realistic assembly tolerances")
    print(f"🖨️ Ready for printing:")
    print(f"   📁 Upper foil: {BOAT_NAME}_Demo_Upper_Foil.stl (with clearance cavity)")
    print(f"   📁 Lower foil: {BOAT_NAME}_Demo_Lower_Foil.stl (with clearance cavity)")
    print(f"   📁 Stock: {BOAT_NAME}_Demo_Stock.stl (demonstration reference)")
    print(f"🔧 Foil cavities sized for real-world assembly with clearance!")