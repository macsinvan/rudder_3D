"""
Demo Model Generator - Step 5A (Bare Bones)
Just imports the cut foil and stock objects.
"""
import os
import FreeCAD as App
import FreeCADGui as Gui
import Part

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "1.0.1"

# Stock positioning parameters
POST_CENTRE_X = 323  # mm - X position for post centre
POST_TOP_Z = -79     # mm - Z position for top of post
POST_DIAMETER = 44   # mm - diameter of the post

# Clearance for 3D printing
CLEARANCE = 1.0      # mm - clearance in each direction

# Paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output"
CUT_FOIL_FOLDER = f"{OUTPUT_FOLDER}/cut_foil"
STOCK_FOLDER = f"{OUTPUT_FOLDER}/stock"

# Input files
CUT_FOIL_STEP = f"{BOAT_NAME}_Cut_Foil.step"
STOCK_STEP = f"{BOAT_NAME}_Stock.step"

MACRO_NAME = f"Demo_Model_{BOAT_NAME}"


def import_step_file(step_path, doc, object_name):
    """Import STEP file and return imported object."""
    if not os.path.exists(step_path):
        print(f"❌ STEP file not found: {step_path}")
        return None
    
    try:
        print(f"📥 Importing {step_path}...")
        
        # Import the STEP file
        imported_shape = Part.read(step_path)
        
        # Create object in document
        obj = doc.addObject("Part::Feature", object_name)
        obj.Shape = imported_shape
        
        print(f"   ✅ Imported: {object_name}")
        print(f"   📏 Bounds: {obj.Shape.BoundBox}")
        
        return obj
        
    except Exception as e:
        print(f"❌ Failed to import {step_path}: {e}")
        return None


def run():
    print(f"\n🎭 Demo Model Generator v{VERSION} (Bare Bones)")
    print(f"🚤 Boat: {BOAT_NAME}")
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

    # Import cut foil
    print(f"\n📥 Importing cut foil...")
    cut_foil_path = f"{CUT_FOIL_FOLDER}/{CUT_FOIL_STEP}"
    cut_foil_obj = import_step_file(cut_foil_path, doc, f"{BOAT_NAME}_Cut_Foil")
    if not cut_foil_obj:
        print("❌ Cannot proceed without cut foil.")
        return

    # Import stock
    print(f"\n📥 Importing stock...")
    stock_path = f"{STOCK_FOLDER}/{STOCK_STEP}"
    stock_obj = import_step_file(stock_path, doc, f"{BOAT_NAME}_Stock")
    if not stock_obj:
        print("❌ Cannot proceed without stock.")
        return

    # Rotate stock 180° around Z-axis to orient tangs toward trailing edge
    print(f"\n🔄 Rotating stock 180° to orient tangs correctly...")
    stock_matrix = App.Matrix()
    stock_matrix.rotateZ(3.14159)  # 180° in radians
    rotated_shape = stock_obj.Shape.transformGeometry(stock_matrix)
    stock_obj.Shape = rotated_shape
    print(f"   ✅ Stock rotated - tangs now point toward trailing edge")
    
    # Position the stock based on post location
    print(f"\n📍 Positioning stock based on post location...")
    print(f"   Post centre target: X={POST_CENTRE_X}mm")
    print(f"   Post top target: Z={POST_TOP_Z}mm")
    print(f"   Post diameter: {POST_DIAMETER}mm")
    
    from FreeCAD import Vector
    
    # Get current bounding box of stock
    current_bbox = stock_obj.Shape.BoundBox
    
    # Calculate post centre X position
    # Post is at the top of the box (max Z), post_diameter/2 in from the right edge (max X)
    current_post_centre_x = current_bbox.XMax - (POST_DIAMETER / 2)
    current_post_top_z = current_bbox.ZMax
    
    print(f"   Current post centre X: {current_post_centre_x:.1f}mm")
    print(f"   Current post top Z: {current_post_top_z:.1f}mm")
    
    # Calculate offset needed to move post to target position
    offset = Vector(
        POST_CENTRE_X - current_post_centre_x,  # Move post centre to specified X
        0,                                       # Keep Y unchanged
        POST_TOP_Z - current_post_top_z          # Move post top to specified Z
    )
    
    # Apply translation
    translation_matrix = App.Matrix()
    translation_matrix.move(offset)
    positioned_shape = stock_obj.Shape.transformGeometry(translation_matrix)
    stock_obj.Shape = positioned_shape
    
    # Report final position
    final_bbox = stock_obj.Shape.BoundBox
    final_post_centre_x = final_bbox.XMax - (POST_DIAMETER / 2)
    final_post_top_z = final_bbox.ZMax
    
    print(f"   ✅ Stock positioned:")
    print(f"      Post centre X: {final_post_centre_x:.1f}mm (target: {POST_CENTRE_X}mm)")
    print(f"      Post top Z: {final_post_top_z:.1f}mm (target: {POST_TOP_Z}mm)")
    
    # Make objects visible
    cut_foil_obj.ViewObject.Visibility = True
    stock_obj.ViewObject.Visibility = True
    
    # Recompute to ensure positioning is complete
    print(f"\n🔄 Recomputing to ensure positioning is complete...")
    doc.recompute()
    print(f"   ✅ Recompute done, ready for boolean operations")
    
    # Perform 6 jogs for clearance in all directions
    print(f"\n🔧 Creating cavity with {CLEARANCE}mm clearance using 6 jogs...")
    print(f"   ⏳ This will take time - performing 6 separate cut operations...")
    
    # Start with the original foil shape
    result_shape = cut_foil_obj.Shape
    
    try:
        # Jog 1: Move stock +X and cut
        print(f"\n   Jog 1/6: +X by {CLEARANCE}mm")
        offset_x_plus = Vector(CLEARANCE, 0, 0)
        matrix_x_plus = App.Matrix()
        matrix_x_plus.move(offset_x_plus)
        stock_x_plus = stock_obj.Shape.transformGeometry(matrix_x_plus)
        result_shape = result_shape.cut(stock_x_plus)
        print(f"      ✅ Cut complete")
        
        # Jog 2: Move stock -X and cut
        print(f"\n   Jog 2/6: -X by {CLEARANCE}mm")
        offset_x_minus = Vector(-CLEARANCE, 0, 0)
        matrix_x_minus = App.Matrix()
        matrix_x_minus.move(offset_x_minus)
        stock_x_minus = stock_obj.Shape.transformGeometry(matrix_x_minus)
        result_shape = result_shape.cut(stock_x_minus)
        print(f"      ✅ Cut complete")
        
        # Jog 3: Move stock +Y and cut
        print(f"\n   Jog 3/6: +Y by {CLEARANCE}mm")
        offset_y_plus = Vector(0, CLEARANCE, 0)
        matrix_y_plus = App.Matrix()
        matrix_y_plus.move(offset_y_plus)
        stock_y_plus = stock_obj.Shape.transformGeometry(matrix_y_plus)
        result_shape = result_shape.cut(stock_y_plus)
        print(f"      ✅ Cut complete")
        
        # Jog 4: Move stock -Y and cut
        print(f"\n   Jog 4/6: -Y by {CLEARANCE}mm")
        offset_y_minus = Vector(0, -CLEARANCE, 0)
        matrix_y_minus = App.Matrix()
        matrix_y_minus.move(offset_y_minus)
        stock_y_minus = stock_obj.Shape.transformGeometry(matrix_y_minus)
        result_shape = result_shape.cut(stock_y_minus)
        print(f"      ✅ Cut complete")
        
        # Jog 5: Move stock +Z and cut
        print(f"\n   Jog 5/6: +Z by {CLEARANCE}mm")
        offset_z_plus = Vector(0, 0, CLEARANCE)
        matrix_z_plus = App.Matrix()
        matrix_z_plus.move(offset_z_plus)
        stock_z_plus = stock_obj.Shape.transformGeometry(matrix_z_plus)
        result_shape = result_shape.cut(stock_z_plus)
        print(f"      ✅ Cut complete")
        
        # Jog 6: Move stock -Z and cut
        print(f"\n   Jog 6/6: -Z by {CLEARANCE}mm")
        offset_z_minus = Vector(0, 0, -CLEARANCE)
        matrix_z_minus = App.Matrix()
        matrix_z_minus.move(offset_z_minus)
        stock_z_minus = stock_obj.Shape.transformGeometry(matrix_z_minus)
        result_shape = result_shape.cut(stock_z_minus)
        print(f"      ✅ Cut complete")
        
        # Create the hollowed foil object
        print(f"\n   Creating hollowed foil object...")
        hollowed_foil_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Hollowed_Foil")
        hollowed_foil_obj.Shape = result_shape
        hollowed_foil_obj.ViewObject.Visibility = True
        hollowed_foil_obj.ViewObject.ShapeColor = (0.3, 0.3, 0.4)  # Dark grey
        hollowed_foil_obj.ViewObject.Transparency = 70  # Make transparent to see cavity
        
        # Hide original foil
        cut_foil_obj.ViewObject.Visibility = False
        
        # Keep stock visible for reference
        stock_obj.ViewObject.ShapeColor = (0.8, 0.8, 0.9)  # Light steel
        
        print(f"\n   ✅ All 6 jogs complete - cavity created with {CLEARANCE}mm clearance in all directions")
        print(f"   Original foil faces: {len(cut_foil_obj.Shape.Faces)}")
        print(f"   Hollowed foil faces: {len(result_shape.Faces)}")
        
    except Exception as e:
        print(f"\n   ❌ Boolean cut failed at jog: {e}")
    
    # Update view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    print(f"\n✅ Import and cavity creation complete!")
    print(f"   • Hollowed Foil: with {CLEARANCE}mm clearance in all directions")
    print(f"   • Stock: positioned for reference")


# Run the script
run()