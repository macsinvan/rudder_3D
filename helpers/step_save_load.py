"""
Demo Model Generator - Step 5A (Bare Bones)
Imports the Cut Foil and Stock and prepares for demo print
Now includes splitting into two halves for 3D printing
"""
import os
import sys
import FreeCAD as App
import FreeCADGui as Gui
import Part

# Add paths to find our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))  # For printer module
sys.path.insert(0, os.path.expanduser("~/Rudder_Code"))  # For helpers module

from printer.cutting_operations import create_cutting_plan, perform_cutting_operations
from printer.stock_positioning import position_all_stock_components
from helpers.step_save_load import load_step, save_step, validate_step_file, StepFileError

print("Imports the Cut Foil and Stock and prepares for demo print")
# Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.1.0"  # Updated - using STEP helper module

# Stock positioning parameters
POST_CENTRE_X = 323  # mm - X position for post centre
POST_TOP_Z = -79     # mm - Z position for top of post
POST_DIAMETER = 44   # mm - diameter of the post
POST_DIAMETER_DELTA = 4  # mm - difference in post diameter for cutout stock

# Printer specifications (Bambu Labs HD2)
HD2_BUILD_X = 325  # mm
HD2_BUILD_Y = 320  # mm  
HD2_BUILD_Z = 325  # mm
PRINT_MAX_SIZE = 310  # mm - Using 310mm (320mm - 10mm allowance) for all dimensions

# Alignment hole parameters - ENHANCED
ALIGNMENT_HOLE_DIAMETER = 6  # mm
ALIGNMENT_HOLE_DEPTH = 25  # mm - increased for better alignment
EDGE_INSET = 20  # mm - distance from edges
Y_SPLIT_HOLES = 12  # number of holes for port/starboard split
Z_CUT_HOLES = 8  # number of holes for horizontal cuts
X_CUT_HOLES = 6  # number of holes for vertical cuts

# Visualization
EXPLOSION_FACTOR = 0  # mm - set to 0 for exact positions, >0 for separated view

# Paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output"
CUT_FOIL_FOLDER = f"{OUTPUT_FOLDER}/cut_foil"
STOCK_FOLDER = f"{OUTPUT_FOLDER}/stock"
CUTOUT_FOLDER = f"{OUTPUT_FOLDER}/cutout"
PRINT_FOLDER = f"{OUTPUT_FOLDER}/demo" #3D print files

# Input files
CUT_FOIL_STEP = f"{BOAT_NAME}_Cut_Foil.step"
STOCK_STEP = f"{BOAT_NAME}_Stock.step"
STOCK_CUTOUT_STEP = f"{BOAT_NAME}_Stock_Cutout.step"

MACRO_NAME = f"Demo_Model_{BOAT_NAME}"


def create_alignment_holes_enhanced(shape, cut_plane, cut_position, z_bounds=None):
   """Create enhanced alignment holes on a cut face.
   
   Args:
       shape: The shape to add holes to
       cut_plane: 'X', 'Y', or 'Z' - the plane of the cut
       cut_position: The position of the cut plane
       z_bounds: (z_min, z_max) for X cuts to constrain holes to specific slice
   
   Returns:
       Modified shape with alignment holes
   """
   from FreeCAD import Vector, Base
   import math
   
   bbox = shape.BoundBox
   holes = []
   holes_created = 0
   
   # Define hole positions based on cut plane
   if cut_plane == 'Y':  # Port/Starboard split - most holes needed
       # Get bounds at Y=0
       x_min, x_max = bbox.XMin + EDGE_INSET, bbox.XMax - EDGE_INSET
       z_min, z_max = bbox.ZMin + EDGE_INSET, bbox.ZMax - EDGE_INSET
       
       # Create grid of holes
       x_count = 3  # 3 columns
       z_count = 4  # 4 rows = 12 total holes
       
       for i in range(x_count):
           for j in range(z_count):
               x = x_min + (x_max - x_min) * (i / (x_count - 1))
               z = z_min + (z_max - z_min) * (j / (z_count - 1))
               
               # Create holes from both sides
               for direction in [-1, 1]:
                   y_start = cut_position + (ALIGNMENT_HOLE_DEPTH/2 * direction)
                   cylinder = Part.makeCylinder(
                       ALIGNMENT_HOLE_DIAMETER / 2,
                       ALIGNMENT_HOLE_DEPTH,
                       Base.Vector(x, y_start, z),
                       Base.Vector(0, -direction, 0)
                   )
                   holes.append(cylinder)
       
       holes_created = x_count * z_count * 2  # Both sides
   
   elif cut_plane == 'Z':  # Horizontal slices
       # Get cross-section bounds at this Z position
       test_box = Part.makeBox(
           bbox.XLength + 100,
           bbox.YLength + 100,
           1,
           Base.Vector(bbox.XMin - 50, bbox.YMin - 50, cut_position - 0.5)
       )
       try:
           intersection = shape.common(test_box)
           int_bbox = intersection.BoundBox
           x_min, x_max = int_bbox.XMin + EDGE_INSET, int_bbox.XMax - EDGE_INSET
           y_min, y_max = int_bbox.YMin + EDGE_INSET/2, int_bbox.YMax - EDGE_INSET/2
       except:
           x_min, x_max = bbox.XMin + EDGE_INSET, bbox.XMax - EDGE_INSET
           y_min, y_max = bbox.YMin + EDGE_INSET/2, bbox.YMax - EDGE_INSET/2
       
       # Create 2x4 grid = 8 holes
       x_positions = [x_min + (x_max - x_min) * i / 3 for i in range(4)]
       y_positions = [y_min + (y_max - y_min) * i for i in [0.3, 0.7]]
       
       for x in x_positions:
           for y in y_positions:
               # Create holes from both sides
               for direction in [-1, 1]:
                   z_start = cut_position + (ALIGNMENT_HOLE_DEPTH/2 * direction)
                   cylinder = Part.makeCylinder(
                       ALIGNMENT_HOLE_DIAMETER / 2,
                       ALIGNMENT_HOLE_DEPTH,
                       Base.Vector(x, y, z_start),
                       Base.Vector(0, 0, -direction)
                   )
                   holes.append(cylinder)
       
       holes_created = len(x_positions) * len(y_positions) * 2
   
   elif cut_plane == 'X':  # Vertical splits
       # Use z_bounds if provided, otherwise use full bounds
       if z_bounds:
           z_min, z_max = z_bounds[0] + EDGE_INSET, z_bounds[1] - EDGE_INSET
       else:
           z_min, z_max = bbox.ZMin + EDGE_INSET, bbox.ZMax - EDGE_INSET
       
       y_min, y_max = bbox.YMin + EDGE_INSET/2, bbox.YMax - EDGE_INSET/2
       
       # Create 2x3 grid = 6 holes
       y_positions = [y_min + (y_max - y_min) * i for i in [0.3, 0.7]]
       z_positions = [z_min + (z_max - z_min) * i / 2 for i in range(3)]
       
       for y in y_positions:
           for z in z_positions:
               # Create holes from both sides
               for direction in [-1, 1]:
                   x_start = cut_position + (ALIGNMENT_HOLE_DEPTH/2 * direction)
                   cylinder = Part.makeCylinder(
                       ALIGNMENT_HOLE_DIAMETER / 2,
                       ALIGNMENT_HOLE_DEPTH,
                       Base.Vector(x_start, y, z),
                       Base.Vector(-direction, 0, 0)
                   )
                   holes.append(cylinder)
       
       holes_created = len(y_positions) * len(z_positions) * 2
   
   # Subtract all holes from the shape
   result_shape = shape
   failed_holes = 0
   
   for i, hole in enumerate(holes):
       try:
           result_shape = result_shape.cut(hole)
       except Exception as e:
           failed_holes += 1
           if failed_holes <= 3:  # Only print first few failures
               print(f"      ⚠️ Failed to create hole {i+1} at {cut_plane}={cut_position:.0f}: {str(e)[:50]}")
   
   if failed_holes > 0:
       print(f"      ⚠️ {failed_holes}/{len(holes)} holes failed to create")
   else:
       print(f"      ✅ Successfully created all {holes_created} holes")
   
   return result_shape


def run():
   print(f"\n🎭 Demo Model Generator v{VERSION} (Refactored)")
   print(f"✨ VERSION {VERSION} - Using STEP helper module for robust file operations")
   print(f"🚤 Boat: {BOAT_NAME}")
   
   # New document
   if MACRO_NAME in App.listDocuments():
       App.closeDocument(MACRO_NAME)
   doc = App.newDocument(MACRO_NAME)
   Gui.activateWorkbench("PartWorkbench")

   # Validate STEP files before import
   print(f"\n🔍 Validating STEP files...")
   cut_foil_path = f"{CUT_FOIL_FOLDER}/{CUT_FOIL_STEP}"
   stock_path = f"{STOCK_FOLDER}/{STOCK_STEP}"
   stock_cutout_path = f"{CUTOUT_FOLDER}/{STOCK_CUTOUT_STEP}"
   
   for filepath, name in [(cut_foil_path, "Cut Foil"), 
                          (stock_path, "Stock"), 
                          (stock_cutout_path, "Stock Cutout")]:
       validation = validate_step_file(filepath, verbose=False)
       if not validation['valid']:
           print(f"❌ Invalid {name} STEP file: {filepath}")
           print(f"   File exists: {validation['exists']}")
           print(f"   File size: {validation['size']} bytes")
           return
       print(f"   ✅ {name} STEP file valid")

   # Import STEP files using helper module
   try:
       print(f"\n📥 Importing STEP files using enhanced loader...")
       
       # Import cut foil
       _, cut_foil_objects = load_step(cut_foil_path, MACRO_NAME, verbose=True)
       if not cut_foil_objects:
           raise StepFileError("No objects imported from cut foil file")
       cut_foil_obj = cut_foil_objects[0]
       cut_foil_obj.Label = f"{BOAT_NAME}_Cut_Foil"
       
       # Import stock
       _, stock_objects = load_step(stock_path, MACRO_NAME, verbose=True)
       if not stock_objects:
           raise StepFileError("No objects imported from stock file")
       stock_obj = stock_objects[0]
       stock_obj.Label = f"{BOAT_NAME}_Stock"
       
       # Import stock cutout
       _, stock_cutout_objects = load_step(stock_cutout_path, MACRO_NAME, verbose=True)
       if not stock_cutout_objects:
           raise StepFileError("No objects imported from stock cutout file")
       stock_cutout_obj = stock_cutout_objects[0]
       stock_cutout_obj.Label = f"{BOAT_NAME}_Stock_Cutout"
       
   except StepFileError as e:
       print(f"❌ Failed to import STEP files: {e}")
       return

   # Position all stock components using refactored module
   final_positions = position_all_stock_components(
       stock_obj, 
       stock_cutout_obj,
       POST_CENTRE_X, 
       POST_TOP_Z, 
       POST_DIAMETER, 
       POST_DIAMETER_DELTA
   )
   
   # Make objects visible
   cut_foil_obj.ViewObject.Visibility = True
   stock_obj.ViewObject.Visibility = True
   stock_cutout_obj.ViewObject.Visibility = True
   
   # Recompute to ensure positioning is complete
   print(f"\n🔄 Recomputing to ensure positioning is complete...")
   doc.recompute()
   print(f"   ✅ Recompute done, ready for boolean operation")
   
   # Pre-Boolean operation checks
   print(f"\n🔍 Performing pre-Boolean operation checks...")
   
   # Check 1: Validate shapes
   if not cut_foil_obj.Shape.isValid():
       print(f"❌ Cut foil shape is not valid!")
       print(f"   The geometry has errors that prevent boolean operations.")
       print(f"   Please check the source STEP file for issues.")
       return
   
   if not stock_cutout_obj.Shape.isValid():
       print(f"❌ Stock cutout shape is not valid!")
       print(f"   The geometry has errors that prevent boolean operations.")
       print(f"   Please check the source STEP file for issues.")
       return
   
   print(f"   ✅ Both shapes are valid")
   
   # Check 2: Ensure shapes are solids
   if not cut_foil_obj.Shape.ShapeType == "Solid":
       print(f"❌ Cut foil is not a solid! (Type: {cut_foil_obj.Shape.ShapeType})")
       print(f"   Boolean cut operations require solid objects.")
       print(f"   The imported shape may be a shell or open surface.")
       return
   
   if not stock_cutout_obj.Shape.ShapeType == "Solid":
       print(f"❌ Stock cutout is not a solid! (Type: {stock_cutout_obj.Shape.ShapeType})")
       print(f"   Boolean cut operations require solid objects.")
       print(f"   The imported shape may be a shell or open surface.")
       return
   
   print(f"   ✅ Both shapes are solids")
   
   # Check 3: Check for intersection
   common_volume = cut_foil_obj.Shape.common(stock_cutout_obj.Shape)
   if common_volume.Volume < 0.001:  # Less than 0.001 mm³
       print(f"❌ No meaningful intersection between shapes!")
       print(f"   Common volume: {common_volume.Volume:.6f} mm³")
       print(f"   The stock cutout and foil do not overlap sufficiently for a boolean cut.")
       print(f"   Check positioning or shape dimensions.")
       return
   
   print(f"   ✅ Shapes intersect properly (common volume: {common_volume.Volume:.2f} mm³)")
   
   # Check 4: Check bounding box overlap
   foil_bbox = cut_foil_obj.Shape.BoundBox
   cutout_bbox = stock_cutout_obj.Shape.BoundBox
   
   if not (foil_bbox.intersect(cutout_bbox)):
       print(f"❌ Bounding boxes do not intersect!")
       print(f"   Foil bounds: X({foil_bbox.XMin:.1f}, {foil_bbox.XMax:.1f})")
       print(f"               Y({foil_bbox.YMin:.1f}, {foil_bbox.YMax:.1f})")
       print(f"               Z({foil_bbox.ZMin:.1f}, {foil_bbox.ZMax:.1f})")
       print(f"   Cutout bounds: X({cutout_bbox.XMin:.1f}, {cutout_bbox.XMax:.1f})")
       print(f"                  Y({cutout_bbox.YMin:.1f}, {cutout_bbox.YMax:.1f})")
       print(f"                  Z({cutout_bbox.ZMin:.1f}, {cutout_bbox.ZMax:.1f})")
       return
   
   print(f"   ✅ Bounding boxes overlap correctly")
   
   # Check 5: Check shape complexity
   print(f"   ℹ️ Shape complexity:")
   print(f"      Cut foil: {len(cut_foil_obj.Shape.Faces)} faces, {len(cut_foil_obj.Shape.Edges)} edges")
   print(f"      Stock cutout: {len(stock_cutout_obj.Shape.Faces)} faces, {len(stock_cutout_obj.Shape.Edges)} edges")
   
   if len(cut_foil_obj.Shape.Faces) > 10000 or len(stock_cutout_obj.Shape.Faces) > 10000:
       print(f"   ⚠️ Warning: High face count detected. Boolean operation may be slow.")
   
   print(f"\n✅ All pre-Boolean checks passed successfully!")
   
   # Perform single boolean cut to hollow out the foil
   print(f"\n🔧 Creating cavity with boolean cut...")
   print(f"   ⏳ This may take a moment for complex geometry...")
   try:
       # Perform the cut operation using the cutout stock
       hollowed_shape = cut_foil_obj.Shape.cut(stock_cutout_obj.Shape)
       
       # Create new hollowed foil object
       hollowed_foil_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Hollowed_Foil")
       hollowed_foil_obj.Shape = hollowed_shape
       hollowed_foil_obj.ViewObject.Visibility = True
       hollowed_foil_obj.ViewObject.ShapeColor = (0.3, 0.3, 0.4)  # Dark grey
       hollowed_foil_obj.ViewObject.Transparency = 70  # Make transparent to see cavity
       
       # Hide original foil and cutout
       cut_foil_obj.ViewObject.Visibility = False
       stock_cutout_obj.ViewObject.Visibility = False
       
       # Keep stock visible for reference
       stock_obj.ViewObject.ShapeColor = (0.8, 0.8, 0.9)  # Light steel
       
       print(f"   ✅ Cavity created successfully")
       print(f"   Original foil faces: {len(cut_foil_obj.Shape.Faces)}")
       print(f"   Hollowed foil faces: {len(hollowed_shape.Faces)}")
       
   except Exception as e:
       print(f"   ❌ Boolean cut failed: {e}")
       return
   
   # Add alignment holes for Y=0 split (port/starboard)
   print(f"\n🔩 Adding alignment holes for port/starboard split (Y=0)...")
   print(f"   Creating {Y_SPLIT_HOLES} holes in 3x4 grid pattern...")
   print(f"   These holes ensure perfect alignment when mirrored halves are joined")
   hollowed_with_y_holes = create_alignment_holes_enhanced(hollowed_shape, 'Y', 0)
   hollowed_foil_obj.Shape = hollowed_with_y_holes
   
   # Split the hollowed foil into two halves
   print(f"\n✂️ Splitting hollowed foil at Y=0...")
   
   try:
       # Get bounding box for reference
       from FreeCAD import Vector, Base
       bbox = hollowed_foil_obj.Shape.BoundBox
       print(f"   Hollowed foil bounds:")
       print(f"      X: {bbox.XMin:.1f} to {bbox.XMax:.1f}")
       print(f"      Y: {bbox.YMin:.1f} to {bbox.YMax:.1f}")
       print(f"      Z: {bbox.ZMin:.1f} to {bbox.ZMax:.1f}")
       
       # Create box for negative Y side (port) - we'll only use this half
       overlap = 0.5  # Small overlap to ensure proper intersection
       box_negative_y = Part.makeBox(
           bbox.XLength + 200,                    # Width in X - make it bigger
           abs(bbox.YMin) + 100 + overlap,        # From well before YMin to slightly past Y=0
           bbox.ZLength + 200,                    # Height in Z - make it bigger
           Base.Vector(bbox.XMin - 100, bbox.YMin - 100, bbox.ZMin - 100)  # Starting well before YMin
       )
       
       # Extract port half only
       print(f"   Creating port half (will be mirrored for starboard)...")
       port_half = hollowed_foil_obj.Shape.common(box_negative_y)
       
       # Verify the split worked
       if port_half.isNull() or len(port_half.Faces) == 0:
           print(f"   ❌ Port half is empty! Trying alternative method...")
           box_positive_y = Part.makeBox(
               bbox.XLength + 200,
               bbox.YMax + 100 + overlap,
               bbox.ZLength + 200,
               Base.Vector(bbox.XMin - 100, -overlap, bbox.ZMin - 100)
           )
           port_half = hollowed_foil_obj.Shape.cut(box_positive_y)
       
       # Hide the original hollowed foil
       hollowed_foil_obj.ViewObject.Visibility = False
       
       print(f"   ✅ Port half created with {len(port_half.Faces)} faces")
       print(f"   ℹ️ This half will be mirrored in slicer to create starboard half")
       
       # Create cutting plan for port half using refactored function
       print(f"\n🗺️ Creating cutting plan for 3D printing...")
       print(f"🖨️ Printer: Bambu Labs HD2 (Build volume: {HD2_BUILD_X}x{HD2_BUILD_Y}x{HD2_BUILD_Z}mm)")
       port_plan = create_cutting_plan(port_half, "Port Half", PRINT_MAX_SIZE)
       
       # Add alignment holes for Z cuts
       print(f"\n🔩 Adding alignment holes for Z-cuts...")
       print(f"   Each cut will have {Z_CUT_HOLES} holes in 2x4 grid pattern")
       if port_plan['z_slices'] > 1:
           for i in range(1, port_plan['z_slices']):
               z_cut_position = port_plan['bbox'].ZMin + (i * port_plan['z_slice_height'])
               print(f"   Adding holes at Z={z_cut_position:.0f}mm:")
               port_half = create_alignment_holes_enhanced(port_half, 'Z', z_cut_position)
       
       # Add alignment holes for X cuts (where needed, constrained to slice bounds)
       print(f"\n🔩 Adding alignment holes for X-cuts...")
       print(f"   Each cut will have {X_CUT_HOLES} holes in 2x3 grid pattern")
       for slice_info in port_plan['slice_plans']:
           if slice_info['needs_x_split']:
               z_bounds = (slice_info['z_start'], slice_info['z_end'])
               x_center = slice_info['x_center']
               print(f"   Adding holes at X={x_center:.0f}mm for slice {slice_info['index']} (Z: {z_bounds[0]:.0f} to {z_bounds[1]:.0f}):")
               port_half = create_alignment_holes_enhanced(port_half, 'X', x_center, z_bounds)
       
       # Perform the actual cutting operations using refactored function
       pieces = perform_cutting_operations(
           port_half, 
           port_plan, 
           doc, 
           BOAT_NAME, 
           explosion_factor=EXPLOSION_FACTOR
       )
       
       # Hide stock for cleaner view of pieces
       stock_obj.ViewObject.Visibility = False
       
       # Export individual pieces using enhanced STEP saver
       print(f"\n💾 Exporting individual pieces using enhanced STEP exporter...")
       pieces_folder = f"{PRINT_FOLDER}/pieces_for_mirroring"
       os.makedirs(pieces_folder, exist_ok=True)
       
       exported_count = 0
       failed_exports = []
       
       for piece_name, piece_shape in pieces:
           try:
               # Create a temporary object for export
               temp_obj = doc.addObject("Part::Feature", f"temp_{piece_name}")
               temp_obj.Shape = piece_shape
               
               piece_path = f"{pieces_folder}/{BOAT_NAME}_{piece_name}.step"
               save_step(temp_obj, piece_path, verbose=False)
               
               # Remove temporary object
               doc.removeObject(temp_obj.Name)
               
               print(f"   ✅ Exported: {piece_name}")
               exported_count += 1
               
           except StepFileError as e:
               print(f"   ❌ Failed to export {piece_name}: {e}")
               failed_exports.append(piece_name)
               # Clean up temp object if it exists
               if f"temp_{piece_name}" in [obj.Name for obj in doc.Objects]:
                   doc.removeObject(f"temp_{piece_name}")
       
       print(f"\n   📦 Successfully exported {exported_count}/{len(pieces)} pieces")
       if failed_exports:
           print(f"   ❌ Failed exports: {', '.join(failed_exports)}")
       
       # Summary
       print(f"\n📋 FINAL SUMMARY:")
       print(f"   🔄 MIRRORING WORKFLOW:")
       print(f"      1. Import pieces into Bambu Studio")
       print(f"      2. Print one set as-is (port half)")
       print(f"      3. Mirror and print again (creates starboard half)")
       print(f"      4. Join at Y=0 centerline using alignment holes")
       print(f"   Alignment holes:")
       print(f"      • Diameter: {ALIGNMENT_HOLE_DIAMETER}mm")
       print(f"      • Depth: {ALIGNMENT_HOLE_DEPTH}mm")
       print(f"      • Y-split: {Y_SPLIT_HOLES} holes (for joining mirrored halves)")
       print(f"      • Z-cuts: {Z_CUT_HOLES} holes each")
       print(f"      • X-cuts: {X_CUT_HOLES} holes each")
       print(f"   Pieces created (to be mirrored):")
       piece_list = [name for name, _ in pieces]
       piece_list.sort()  # Sort for logical order
       for piece_name in piece_list:
           print(f"      • {piece_name}")
       print(f"   📦 UNIQUE PIECES: {len(pieces)}")
       print(f"   📦 TOTAL AFTER MIRRORING: {len(pieces) * 2}")
       
   except Exception as e:
       print(f"   ❌ Processing failed: {e}")
       import traceback
       traceback.print_exc()
   
   # Update view
   doc.recompute()
   Gui.SendMsgToActiveView("ViewFit")
   Gui.activeDocument().activeView().viewIsometric()
   
   print(f"\n✅ Complete! Pieces ready for mirroring in slicer.")
   print(f"📁 Files saved to: {pieces_folder}")


# Run the script
run()