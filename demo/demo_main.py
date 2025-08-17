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


def create_solid_foil_from_cut(cut_foil_obj, doc):
    """
    Create a solid demo foil from the cut foil.
    For demo purposes, we want a solid foil rather than one with a cavity.
    """
    try:
        print(f"🔧 Creating solid demo foil...")
        
        # Get the cut foil shape
        cut_shape = cut_foil_obj.Shape
        
        # For demo, we'll create a simplified solid version
        # Use the outer boundary to create a solid foil
        if hasattr(cut_shape, 'Shells') and cut_shape.Shells:
            # Get the outer shell and make it solid
            outer_shell = cut_shape.Shells[0]
            try:
                solid_foil = Part.makeSolid(outer_shell)
                print(f"   ✅ Created solid foil from shell")
            except:
                # If that fails, use the original cut shape
                solid_foil = cut_shape
                print(f"   ⚠️ Using cut foil as-is for demo")
        else:
            solid_foil = cut_shape
            print(f"   ⚠️ Using cut foil as-is for demo")
        
        # Create new solid foil object
        solid_foil_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_SolidFoil")
        solid_foil_obj.Shape = solid_foil
        solid_foil_obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0)  # Green
        
        print(f"   ✅ Created solid demo foil: {solid_foil.ShapeType}")
        return solid_foil_obj
        
    except Exception as e:
        print(f"❌ Failed to create solid foil: {e}")
        return None


def create_breakaway_tabs(foil_obj, stock_obj, doc):
    """
    Create breakaway tabs connecting the stock to the foil.
    """
    try:
        print(f"🔗 Creating {TAB_COUNT} breakaway tabs...")
        
        foil_bbox = foil_obj.Shape.BoundBox
        stock_bbox = stock_obj.Shape.BoundBox
        
        tabs = []
        
        # Create tabs at different positions around the stock
        for i in range(TAB_COUNT):
            angle = (360.0 / TAB_COUNT) * i  # Distribute tabs evenly
            
            # Calculate tab position (simplified - connect to foil base)
            tab_x = stock_bbox.Center.x + (stock_bbox.XLength / 3) * (i - TAB_COUNT/2)
            tab_y = foil_bbox.YMin  # Bottom of foil
            tab_z = stock_bbox.Center.z
            
            # Create tab as a small box
            tab_shape = Part.makeBox(
                TAB_WIDTH, 
                TAB_THICKNESS, 
                TAB_WIDTH,
                Vector(tab_x - TAB_WIDTH/2, tab_y, tab_z - TAB_WIDTH/2)
            )
            
            tab_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Tab_{i}")
            tab_obj.Shape = tab_shape
            tab_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)  # Yellow
            tabs.append(tab_obj)
        
        print(f"   ✅ Created {len(tabs)} breakaway tabs")
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


def create_demo_assembly(foil_obj, stock_obj, tabs, doc):
    """
    Create final demo assembly by fusing all parts together.
    """
    try:
        print(f"🔧 Creating demo assembly...")
        
        # Start with foil
        assembly_shape = foil_obj.Shape
        
        # Add stock
        assembly_shape = assembly_shape.fuse(stock_obj.Shape)
        
        # Add all tabs
        for tab in tabs:
            assembly_shape = assembly_shape.fuse(tab.Shape)
        
        # Create final assembly object
        assembly_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Demo_Assembly")
        assembly_obj.Shape = assembly_shape
        assembly_obj.ViewObject.ShapeColor = (0.0, 0.6, 1.0)  # Light blue
        
        print(f"   ✅ Created demo assembly")
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

    # Step 4: Create solid foil for demo
    print(f"\n🔧 STEP 4: Creating solid demo foil...")
    solid_foil_obj = create_solid_foil_from_cut(cut_foil_obj, doc)
    if not solid_foil_obj:
        print("❌ Failed to create solid foil.")
        return
    
    # Hide the original cut foil to avoid confusion
    cut_foil_obj.ViewObject.Visibility = False
    print(f"   ✅ Hidden original cut foil")

    # Step 5: Create breakaway tabs
    print(f"\n🔗 STEP 5: Creating breakaway tabs...")
    tabs = create_breakaway_tabs(solid_foil_obj, stock_obj, doc)
    if not tabs:
        print("❌ Failed to create tabs.")
        return

    # Step 6: Arrange for printing
    print(f"\n🎯 STEP 6: Arranging for printing...")
    if not arrange_for_printing(solid_foil_obj, stock_obj, tabs, doc):
        print("❌ Failed to arrange parts.")
        return

    # Step 7: Create final assembly
    print(f"\n🔧 STEP 7: Creating demo assembly...")
    assembly_obj = create_demo_assembly(solid_foil_obj, stock_obj, tabs, doc)
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