# demo/demo_main.py
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
SCALE_FACTOR = 0.25      # 1:4 scale (25% of original size)
TAB_THICKNESS = 0.8      # mm thickness of breakaway tabs
TAB_WIDTH = 4.0          # mm width of breakaway tabs
TAB_COUNT = 3            # Number of tabs connecting parts
PRINT_MARGIN = 5.0       # mm margin between parts on print bed

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
    Position the stock inside the foil cavity with proper orientation and positioning.
    - Applies 180° rotation around Z-axis to orient post toward leading edge
    - Positions at Y=0 (center plane)
    - Extends upward (+Z) until it penetrates the top of the rudder
    """
    try:
        print(f"🎯 Positioning stock with correct orientation and penetration...")
        
        # PERFORMANCE: Disable view updates
        stock_obj.ViewObject.Visibility = False
        
        # Use upper half for reference (both halves should have same cavity)
        foil_bbox = upper_foil_obj.Shape.BoundBox
        stock_bbox = stock_obj.Shape.BoundBox
        
        # Create transformation matrix with rotation and translation
        stock_matrix = App.Matrix()
        
        # First rotate 180° around Z-axis to orient post toward leading edge
        # Rotation is around stock's current center
        stock_matrix.rotateZ(3.14159)  # 180° in radians
        print(f"   🔄 Applied 180° rotation around Z-axis")
        
        # Apply rotation first
        rotated_shape = stock_obj.Shape.transformGeometry(stock_matrix)
        
        # Get bounding box of rotated shape for positioning
        rotated_bbox = rotated_shape.BoundBox
        
        # Calculate position offset with specific requirements:
        # - X: Center in foil cavity (as before)
        # - Y: Position at Y=0 (center plane)
        # - Z: Extend upward until stock penetrates top of rudder
        penetration_distance = 5.0  # mm of penetration above rudder top
        
        stock_offset = Vector(
            foil_bbox.Center.x - rotated_bbox.Center.x,  # Center on X
            0.0 - rotated_bbox.Center.y,                 # Position at Y=0
            (foil_bbox.ZMax + penetration_distance) - rotated_bbox.ZMax  # Penetrate top by 5mm
        )
        
        # Create translation matrix
        translation_matrix = App.Matrix()
        translation_matrix.move(stock_offset)
        
        # Apply translation to the already rotated shape
        final_shape = rotated_shape.transformGeometry(translation_matrix)
        stock_obj.Shape = final_shape
        
        # Get final positioning for verification
        final_bbox = final_shape.BoundBox
        
        print(f"   ✅ Positioned stock with correct orientation")
        print(f"   📐 Stock offset: ({stock_offset.x:.1f}, {stock_offset.y:.1f}, {stock_offset.z:.1f})mm")
        print(f"   🎯 Post oriented toward leading edge")
        print(f"   📍 Stock Y-position: {final_bbox.Center.y:.1f}mm (target: 0.0mm)")
        print(f"   ⬆️  Stock top at Z={final_bbox.ZMax:.1f}mm, rudder top at Z={foil_bbox.ZMax:.1f}mm")
        print(f"   🔺 Penetration: {final_bbox.ZMax - foil_bbox.ZMax:.1f}mm above rudder")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to position stock: {e}")
        return False


def create_demo_assembly_clean(upper_foil_obj, lower_foil_obj, stock_obj, doc):
    """
    Create clean demo assembly and remove intermediate objects.
    Shows only the final split assembly for clear visualization.
    """
    try:
        print(f"🔧 Creating clean demo assembly...")
        
        # Create upper assembly (upper foil + stock)
        upper_assembly_shape = upper_foil_obj.Shape.fuse(stock_obj.Shape)
        upper_assembly_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Upper_Assembly")
        upper_assembly_obj.Shape = upper_assembly_shape
        upper_assembly_obj.ViewObject.ShapeColor = (0.2, 0.7, 0.2)  # Forest green
        upper_assembly_obj.ViewObject.Transparency = 20  # Slight transparency
        
        # Create lower assembly (lower foil + stock copy)
        lower_assembly_shape = lower_foil_obj.Shape.fuse(stock_obj.Shape)
        lower_assembly_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Lower_Assembly")
        lower_assembly_obj.Shape = lower_assembly_shape
        lower_assembly_obj.ViewObject.ShapeColor = (0.1, 0.5, 0.1)  # Darker green
        lower_assembly_obj.ViewObject.Transparency = 20  # Slight transparency
        
        # CLEANUP: Remove intermediate objects to reduce clutter
        print(f"   🧹 Cleaning up intermediate objects...")
        doc.removeObject(upper_foil_obj.Name)
        doc.removeObject(lower_foil_obj.Name)
        doc.removeObject(stock_obj.Name)
        
        print(f"   ✅ Created clean split assembly visualization")
        print(f"   📏 Upper assembly faces: {len(upper_assembly_shape.Faces)}")
        print(f"   📏 Lower assembly faces: {len(lower_assembly_shape.Faces)}")
        print(f"   🧹 Removed {3} intermediate objects")
        
        return upper_assembly_obj, lower_assembly_obj
        
    except Exception as e:
        print(f"❌ Failed to create assembly: {e}")
        return None, None


def run():
    print(f"\n🎭 Demo Model Generator v{VERSION} (Performance Optimized)")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📐 Scale: {SCALE_FACTOR} ({int(SCALE_FACTOR*100)}% of original)")
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

    # Step 3: Scale everything down for demo
    print(f"\n📐 STEP 3: Scaling for demo...")
    if not scale_object(cut_foil_obj, SCALE_FACTOR):
        print("❌ Failed to scale cut foil.")
        return
    if not scale_object(stock_obj, SCALE_FACTOR):
        print("❌ Failed to scale stock.")
        return

    # Step 4: Split foil for visualization (through chord along Y-axis)
    print(f"\n✂️ STEP 4: Splitting foil through chord for visualization...")
    upper_foil_obj, lower_foil_obj = split_foil_for_visualization(cut_foil_obj, doc)
    if not upper_foil_obj or not lower_foil_obj:
        print("❌ Failed to split foil.")
        return
    
    # Hide the original cut foil to avoid confusion
    cut_foil_obj.ViewObject.Visibility = False
    print(f"   ✅ Hidden original cut foil")

    # Step 5: Position stock between the foil halves
    print(f"\n🎯 STEP 5: Positioning stock between halves...")
    if not position_stock_in_cavity(upper_foil_obj, lower_foil_obj, stock_obj, doc):
        print("❌ Failed to position stock.")
        return

    # Step 6: Create clean split assembly
    print(f"\n🔧 STEP 6: Creating clean split assembly...")
    upper_assembly_obj, lower_assembly_obj = create_demo_assembly_clean(upper_foil_obj, lower_foil_obj, stock_obj, doc)
    if not upper_assembly_obj or not lower_assembly_obj:
        print("❌ Failed to create assembly.")
        return

    # Step 7: Export STL for demo printing (export both halves)
    print(f"\n💾 STEP 7: Exporting demo STL files...")
    
    # Export upper half
    upper_stl_path = f"{DEMO_FOLDER}/{BOAT_NAME}_Demo_Upper.stl"
    try:
        print(f"   🔄 Exporting upper half STL...")
        upper_assembly_obj.Shape.exportStl(upper_stl_path)
        upper_size = os.path.getsize(upper_stl_path)
        print(f"   ✅ Upper half: {upper_stl_path} ({upper_size/1024/1024:.1f} MB)")
    except Exception as e:
        print(f"   ❌ Upper STL export failed: {e}")
    
    # Export lower half  
    lower_stl_path = f"{DEMO_FOLDER}/{BOAT_NAME}_Demo_Lower.stl"
    try:
        print(f"   🔄 Exporting lower half STL...")
        lower_assembly_obj.Shape.exportStl(lower_stl_path)
        lower_size = os.path.getsize(lower_stl_path)
        print(f"   ✅ Lower half: {lower_stl_path} ({lower_size/1024/1024:.1f} MB)")
    except Exception as e:
        print(f"   ❌ Lower STL export failed: {e}")

    # PERFORMANCE: Final recompute to ensure everything is up to date
    print(f"\n🔄 Final recomputation and view setup...")
    doc.recompute()
    
    # Show both assembly halves with slight offset for better visualization
    upper_assembly_obj.ViewObject.Visibility = True
    lower_assembly_obj.ViewObject.Visibility = True
    
    # Finalize view
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    # Summary
    print(f"\n🎭 {BOAT_NAME} demo model complete!")
    print(f"📐 Scale: {SCALE_FACTOR} ({int(SCALE_FACTOR*100)}% of original size)")
    print(f"🖨️ Ready for demo printing:")
    print(f"   📁 Upper half: {BOAT_NAME}_Demo_Upper.stl")
    print(f"   📁 Lower half: {BOAT_NAME}_Demo_Lower.stl")
    print(f"⚡ Clean visualization with intermediate objects removed!")