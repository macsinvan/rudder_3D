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
VERSION = "1.0.0"        # Initial implementation

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
    """
    try:
        print(f"✂️ Splitting foil through the chord for visualization...")
        
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
        
        # Create upper half object
        upper_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Foil_Upper")
        upper_obj.Shape = upper_half
        upper_obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0)  # Green
        
        # Create lower half object  
        lower_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Foil_Lower")
        lower_obj.Shape = lower_half
        lower_obj.ViewObject.ShapeColor = (0.0, 0.6, 0.0)  # Darker green
        
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
    Position the stock inside the foil cavity, centered between the split halves.
    Applies 180° rotation around Z-axis to orient post toward leading edge.
    """
    try:
        print(f"🎯 Positioning stock between upper and lower foil halves...")
        
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
        
        # Calculate position offset to center rotated stock in cavity
        stock_offset = Vector(
            foil_bbox.Center.x - rotated_bbox.Center.x,  # Center on X
            foil_bbox.Center.y - rotated_bbox.Center.y,  # Center on Y (between halves)
            foil_bbox.Center.z - rotated_bbox.Center.z   # Center on Z
        )
        
        # Create translation matrix
        translation_matrix = App.Matrix()
        translation_matrix.move(stock_offset)
        
        # Apply translation to the already rotated shape
        final_shape = rotated_shape.transformGeometry(translation_matrix)
        stock_obj.Shape = final_shape
        
        print(f"   ✅ Positioned stock between upper and lower halves")
        print(f"   📐 Stock offset: ({stock_offset.x:.1f}, {stock_offset.y:.1f}, {stock_offset.z:.1f})mm")
        print(f"   🎯 Post now oriented toward leading edge")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to position stock: {e}")
        return False


def create_breakaway_tabs(foil_obj, stock_obj, doc):
    """
    Create breakaway tabs connecting the stock to the foil.
    Stock is now positioned inside the cavity.
    """
    try:
        print(f"🔗 Creating {TAB_COUNT} breakaway tabs...")
        
        foil_bbox = foil_obj.Shape.BoundBox
        stock_bbox = stock_obj.Shape.BoundBox
        
        tabs = []
        
        # Create tabs that bridge from stock (inside cavity) to foil exterior
        for i in range(TAB_COUNT):
            # Position tabs to connect stock to foil opening
            # Since stock is inside cavity, tabs need to reach outside
            
            # Calculate tab position - from stock edge to foil edge
            if i == 0:  # Top tab
                tab_start = Vector(stock_bbox.Center.x, stock_bbox.YMax, stock_bbox.ZMax + 2)
                tab_end = Vector(foil_bbox.Center.x, foil_bbox.YMax + 5, stock_bbox.ZMax + 2)
            elif i == 1:  # Side tab
                tab_start = Vector(stock_bbox.XMax + 2, stock_bbox.Center.y, stock_bbox.Center.z)
                tab_end = Vector(foil_bbox.XMax + 5, stock_bbox.Center.y, stock_bbox.Center.z)
            else:  # Bottom tab
                tab_start = Vector(stock_bbox.Center.x, stock_bbox.YMin, stock_bbox.ZMin - 2)
                tab_end = Vector(foil_bbox.Center.x, foil_bbox.YMin - 5, stock_bbox.ZMin - 2)
            
            # Create tab as connecting bridge
            tab_center = Vector(
                (tab_start.x + tab_end.x) / 2,
                (tab_start.y + tab_end.y) / 2,
                (tab_start.z + tab_end.z) / 2
            )
            
            tab_shape = Part.makeBox(
                TAB_WIDTH, 
                TAB_THICKNESS, 
                TAB_WIDTH,
                Vector(tab_center.x - TAB_WIDTH/2, tab_center.y - TAB_THICKNESS/2, tab_center.z - TAB_WIDTH/2)
            )
            
            tab_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Tab_{i}")
            tab_obj.Shape = tab_shape
            tab_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)  # Yellow
            tabs.append(tab_obj)
        
        print(f"   ✅ Created {len(tabs)} breakaway tabs connecting stock to foil")
        return tabs
        
    except Exception as e:
        print(f"❌ Failed to create tabs: {e}")
        return []


def arrange_for_printing(foil_obj, stock_obj, tabs, doc):
    """
    Arrange all parts for optimal printing on the build plate.
    """
    try:
        print(f"🎯 Arranging parts for printing...")
        
        # Get bounding boxes BEFORE any transformations
        foil_bbox = foil_obj.Shape.BoundBox
        stock_bbox = stock_obj.Shape.BoundBox
        
        # Create transformation matrix for foil (position at origin)
        foil_matrix = App.Matrix()
        foil_offset = Vector(-foil_bbox.Center.x, -foil_bbox.YMin, -foil_bbox.ZMin)
        foil_matrix.move(foil_offset)
        foil_obj.Shape = foil_obj.Shape.transformGeometry(foil_matrix)
        
        # Create transformation matrix for stock (position next to foil)
        stock_matrix = App.Matrix()
        stock_offset = Vector(
            foil_bbox.XLength/2 + PRINT_MARGIN - stock_bbox.Center.x,
            -stock_bbox.YMin, 
            -stock_bbox.ZMin
        )
        stock_matrix.move(stock_offset)
        stock_obj.Shape = stock_obj.Shape.transformGeometry(stock_matrix)
        
        # Position tabs using transformation matrices
        for i, tab in enumerate(tabs):
            tab_matrix = App.Matrix()
            tab_offset = Vector(
                foil_bbox.XLength/4 * (i - len(tabs)/2),
                0,
                foil_bbox.ZLength + PRINT_MARGIN
            )
            tab_matrix.move(tab_offset)
            tab.Shape = tab.Shape.transformGeometry(tab_matrix)
        
        print(f"   ✅ Arranged parts for printing")
        return True
        
    except Exception as e:
        print(f"❌ Failed to arrange parts: {e}")
        return False


def create_demo_assembly_simple(upper_foil_obj, lower_foil_obj, stock_obj, doc):
    """
    Create simple demo assembly with split foil halves and stock (no tabs).
    """
    try:
        print(f"🔧 Creating simple demo assembly...")
        
        # Start with upper foil half
        assembly_shape = upper_foil_obj.Shape
        
        # Add lower foil half
        assembly_shape = assembly_shape.fuse(lower_foil_obj.Shape)
        
        # Add stock
        assembly_shape = assembly_shape.fuse(stock_obj.Shape)
        
        # Create final assembly object
        assembly_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Assembly")
        assembly_obj.Shape = assembly_shape
        assembly_obj.ViewObject.ShapeColor = (0.0, 0.6, 1.0)  # Light blue
        
        print(f"   ✅ Created simple demo assembly (no tabs)")
        return assembly_obj
        
    except Exception as e:
        print(f"❌ Failed to create assembly: {e}")
        return None


def run():
    print(f"\n🎭 Demo Model Generator v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📐 Scale: {SCALE_FACTOR} ({int(SCALE_FACTOR*100)}% of original)")
    print(f"🔗 Tabs: {TAB_COUNT} x {TAB_WIDTH}mm x {TAB_THICKNESS}mm")
    
    # Ensure output folder exists
    ensure_output_folder()
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

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

    # Step 6: Create simple assembly (no tabs)
    print(f"\n🔧 STEP 6: Creating simple demo assembly...")
    assembly_obj = create_demo_assembly_simple(upper_foil_obj, lower_foil_obj, stock_obj, doc)
    if not assembly_obj:
        print("❌ Failed to create assembly.")
        return

    # Step 8: Export STL for demo printing
    print(f"\n💾 STEP 8: Exporting demo STL...")
    demo_stl_path = f"{DEMO_FOLDER}/{DEMO_STL}"
    
    try:
        assembly_obj.Shape.exportStl(demo_stl_path)
        print(f"✅ Exported demo STL: {demo_stl_path}")
        
        # Validation
        stl_size = os.path.getsize(demo_stl_path)
        print(f"   📏 STL file size: {stl_size} bytes")
        
    except Exception as e:
        print(f"❌ STL export failed: {e}")

    # Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    # Summary
    print(f"\n🎭 {BOAT_NAME} demo model complete!")
    print(f"📐 Scale: {SCALE_FACTOR} ({int(SCALE_FACTOR*100)}% of original size)")
    print(f"🖨️ Ready for demo printing: {demo_stl_path}")
    print(f"🔗 Print all parts together, then break apart tabs for assembly demo!")