"""
Demo Model Generator - Step 5A (Bare Bones)
Imports the Cut Foil and Stock and prepares for demo print
Now includes splitting into two halves for 3D printing
"""
import os
import FreeCAD as App
import FreeCADGui as Gui
import Part

print("Imports the Cut Foil and Stock and prepares for demo print")
# Configuration
BOAT_NAME = "MackenSea"
VERSION = "1.0.10"  # Updated version - pieces stay in original positions

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


def perform_cutting_operations(port_half, port_plan, doc):
   """Perform the actual cutting operations to create individual pieces for ONE half only.
   Pieces remain in their original positions.
   
   Args:
       port_half: Port half shape with alignment holes (will be mirrored in slicer)
       port_plan: Cutting plan for port half
       doc: FreeCAD document
   
   Returns:
       List of (piece_name, piece_shape) tuples
   """
   from FreeCAD import Vector, Base
   
   print(f"\n✂️ PERFORMING CUTTING OPERATIONS...")
   print(f"   Creating {port_plan['total_pieces']} pieces (port half only - will be mirrored in slicer)")
   print(f"   Pieces will remain in original positions")
   
   pieces = []
   piece_objects = []
   
   print(f"\n   Processing Port half (for mirroring)...")
   
   # Optional: Small explosion offset to separate pieces slightly for visualization
   EXPLOSION_FACTOR = 0  # mm - small gap between pieces for clarity (set to 0 for exact positions)
   
   # Cut into Z slices
   for i, slice_info in enumerate(port_plan['slice_plans']):
       slice_num = i + 1
       z_start = slice_info['z_start']
       z_end = slice_info['z_end']
       z_mid = (z_start + z_end) / 2
       
       print(f"      Creating slice {slice_num} (Z: {z_start:.0f} to {z_end:.0f}mm)")
       
       # Create cutting boxes for this slice
       bbox = port_half.BoundBox
       
       # Box to isolate this Z slice
       slice_box = Part.makeBox(
           bbox.XLength + 200,
           bbox.YLength + 200,
           z_end - z_start,
           Base.Vector(bbox.XMin - 100, bbox.YMin - 100, z_start)
       )
       
       # Extract the slice
       try:
           slice_shape = port_half.common(slice_box)
           
           # Now check if X-split is needed
           if slice_info['needs_x_split']:
               x_center = slice_info['x_center']
               print(f"         Splitting at X={x_center:.0f}mm")
               
               # Create boxes for left (A) and right (B) pieces
               left_box = Part.makeBox(
                   x_center - bbox.XMin + 10,
                   bbox.YLength + 200,
                   z_end - z_start + 10,
                   Base.Vector(bbox.XMin - 10, bbox.YMin - 100, z_start - 5)
               )
               
               right_box = Part.makeBox(
                   bbox.XMax - x_center + 10,
                   bbox.YLength + 200,
                   z_end - z_start + 10,
                   Base.Vector(x_center, bbox.YMin - 100, z_start - 5)
               )
               
               # Create A and B pieces
               piece_a = slice_shape.common(left_box)
               piece_b = slice_shape.common(right_box)
               
               # Name pieces without P/S designation
               name_a = f"{slice_num}A"
               name_b = f"{slice_num}B"
               
               pieces.append((name_a, piece_a))
               pieces.append((name_b, piece_b))
               
               print(f"         ✅ Created pieces {name_a} and {name_b}")
               
               # Create FreeCAD objects - keeping original positions
               obj_a = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name_a}")
               obj_a.Shape = piece_a
               obj_a.ViewObject.ShapeColor = (0.2 + i*0.15, 0.4, 0.6)
               obj_a.ViewObject.Transparency = 20
               
               # Optional: Add small explosion offset
               if EXPLOSION_FACTOR > 0:
                   obj_a.Placement.Base.x -= EXPLOSION_FACTOR  # Move A piece left slightly
                   obj_a.Placement.Base.z += i * EXPLOSION_FACTOR  # Separate Z slices
               
               piece_objects.append(obj_a)
               
               obj_b = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name_b}")
               obj_b.Shape = piece_b
               obj_b.ViewObject.ShapeColor = (0.25 + i*0.15, 0.4, 0.65)
               obj_b.ViewObject.Transparency = 20
               
               # Optional: Add small explosion offset
               if EXPLOSION_FACTOR > 0:
                   obj_b.Placement.Base.x += EXPLOSION_FACTOR  # Move B piece right slightly
                   obj_b.Placement.Base.z += i * EXPLOSION_FACTOR  # Separate Z slices
               
               piece_objects.append(obj_b)
               
           else:
               # Single piece for this slice
               name = f"{slice_num}A"
               pieces.append((name, slice_shape))
               
               print(f"         ✅ Created piece {name}")
               
               # Create FreeCAD object - keeping original position
               obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name}")
               obj.Shape = slice_shape
               obj.ViewObject.ShapeColor = (0.2 + i*0.15, 0.4, 0.6)
               obj.ViewObject.Transparency = 20
               
               # Optional: Add small explosion offset for Z separation
               if EXPLOSION_FACTOR > 0:
                   obj.Placement.Base.z += i * EXPLOSION_FACTOR
               
               piece_objects.append(obj)
               
       except Exception as e:
           print(f"         ❌ Failed to create slice: {e}")
   
   print(f"   ✅ Created {len(piece_objects)} pieces in original positions")
   if EXPLOSION_FACTOR > 0:
       print(f"   ℹ️ Added {EXPLOSION_FACTOR}mm explosion offset for visualization")
   
   return pieces


def create_cutting_plan(shape, half_name):
   """Create a cutting plan for a half of the model, analyzing each slice individually."""
   from FreeCAD import Vector, Base
   bbox = shape.BoundBox
   
   print(f"\n📐 Creating cutting plan for {half_name}:")
   print(f"   Original dimensions:")
   print(f"      X: {bbox.XLength:.1f}mm")
   print(f"      Y: {bbox.YLength:.1f}mm")
   print(f"      Z: {bbox.ZLength:.1f}mm")
   print(f"   Max printable size: {PRINT_MAX_SIZE}mm")
   
   # Calculate Z slices needed
   z_slices_needed = 1
   z_slice_height = bbox.ZLength
   
   if bbox.ZLength > PRINT_MAX_SIZE:
       import math
       z_slices_needed = math.ceil(bbox.ZLength / PRINT_MAX_SIZE)
       z_slice_height = bbox.ZLength / z_slices_needed
       print(f"   📊 Z-axis: Needs {z_slices_needed} slices of {z_slice_height:.1f}mm each")
   else:
       print(f"   ✅ Z-axis: Fits in one piece ({bbox.ZLength:.1f}mm < {PRINT_MAX_SIZE}mm)")
   
   # Y-axis check (already split at Y=0)
   if bbox.YLength > PRINT_MAX_SIZE:
       print(f"   ⚠️ Y-axis: {bbox.YLength:.1f}mm > {PRINT_MAX_SIZE}mm")
       print(f"      This half may still be too large in Y!")
   else:
       print(f"   ✅ Y-axis: Fits in one piece ({bbox.YLength:.1f}mm < {PRINT_MAX_SIZE}mm)")
   
   # Analyze each Z slice for X-splitting needs
   print(f"\n   🔍 Analyzing each slice for X-splitting needs:")
   total_pieces = 0
   slice_plans = []
   
   for i in range(z_slices_needed):
       # Calculate the Z bounds for this slice
       z_start = bbox.ZMin + (i * z_slice_height)
       z_end = min(z_start + z_slice_height, bbox.ZMax)
       z_mid = (z_start + z_end) / 2
       
       # Create a thin box at the middle of this slice to intersect with the shape
       # This gives us an approximation of the slice's cross-section
       test_box = Part.makeBox(
           bbox.XLength + 100,  # Wide enough to cover entire shape
           bbox.YLength + 100,  # Deep enough to cover entire shape
           1,                    # Very thin slice
           Base.Vector(bbox.XMin - 50, bbox.YMin - 50, z_mid - 0.5)
       )
       
       # Intersect to get approximate slice bounds
       try:
           slice_intersection = shape.common(test_box)
           slice_bbox = slice_intersection.BoundBox
           slice_x_length = slice_bbox.XLength
           slice_x_center = (slice_bbox.XMin + slice_bbox.XMax) / 2
       except:
           # If intersection fails, use conservative estimate
           slice_x_length = bbox.XLength
           slice_x_center = (bbox.XMin + bbox.XMax) / 2
       
       # Determine if this slice needs X-splitting
       needs_x_split = slice_x_length > PRINT_MAX_SIZE
       pieces_in_slice = 2 if needs_x_split else 1
       total_pieces += pieces_in_slice
       
       slice_info = {
           'index': i + 1,
           'z_start': z_start,
           'z_end': z_end,
           'x_length': slice_x_length,
           'x_center': slice_x_center,
           'needs_x_split': needs_x_split,
           'pieces': pieces_in_slice
       }
       slice_plans.append(slice_info)
       
       print(f"      Slice {i+1} (Z: {z_start:.0f} to {z_end:.0f}mm):")
       print(f"         X width: {slice_x_length:.1f}mm")
       if needs_x_split:
           print(f"         ❌ Needs X-split (>{PRINT_MAX_SIZE}mm) → 2 pieces")
       else:
           print(f"         ✅ No X-split needed → 1 piece")
   
   print(f"\n   📦 Total pieces for {half_name}: {total_pieces}")
   
   # Create cutting plan structure
   cutting_plan = {
       'z_slices': z_slices_needed,
       'z_slice_height': z_slice_height,
       'slice_plans': slice_plans,
       'total_pieces': total_pieces,
       'bbox': bbox
   }
   
   return cutting_plan


def run():
   print(f"\n🎭 Demo Model Generator v{VERSION} (Bare Bones)")
   print(f"✨ VERSION {VERSION} - Pieces stay in original positions!")
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

   # Import stock cutout
   print(f"\n📥 Importing stock cutout...")
   stock_cutout_path = f"{CUTOUT_FOLDER}/{STOCK_CUTOUT_STEP}"
   stock_cutout_obj = import_step_file(stock_cutout_path, doc, f"{BOAT_NAME}_Stock_Cutout")
   if not stock_cutout_obj:
       print("❌ Cannot proceed without stock cutout.")
       return

   # Rotate stock 180° around Z-axis to orient tangs toward trailing edge
   print(f"\n🔄 Rotating stock 180° to orient tangs correctly...")
   stock_matrix = App.Matrix()
   stock_matrix.rotateZ(3.14159)  # 180° in radians
   rotated_shape = stock_obj.Shape.transformGeometry(stock_matrix)
   stock_obj.Shape = rotated_shape
   print(f"   ✅ Stock rotated - tangs now point toward trailing edge")
   
   # Rotate stock cutout 180° around Z-axis to orient tangs toward trailing edge
   print(f"\n🔄 Rotating stock cutout 180° to orient tangs correctly...")
   stock_cutout_matrix = App.Matrix()
   stock_cutout_matrix.rotateZ(3.14159)  # 180° in radians
   rotated_cutout_shape = stock_cutout_obj.Shape.transformGeometry(stock_cutout_matrix)
   stock_cutout_obj.Shape = rotated_cutout_shape
   print(f"   ✅ Stock cutout rotated - tangs now point toward trailing edge")
   
   # Position the stock based on post location
   print(f"\n📍 Positioning stock based on post location...")
   print(f"   Post centre target: X={POST_CENTRE_X}mm")
   print(f"   Post top target: Z={POST_TOP_Z}mm")
   print(f"   Post diameter: {POST_DIAMETER}mm")
   
   from FreeCAD import Vector, Base
   
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
   
   # Position the stock cutout based on post location (with larger diameter)
   print(f"\n📍 Positioning stock cutout based on post location...")
   cutout_post_diameter = POST_DIAMETER + POST_DIAMETER_DELTA
   # Adjust target X to account for larger post radius
   cutout_target_x = POST_CENTRE_X - (POST_DIAMETER_DELTA / 2) + (POST_DIAMETER_DELTA/2)
   print(f"   Post centre target: X={cutout_target_x}mm (adjusted for larger post)")
   print(f"   Post top target: Z={POST_TOP_Z}mm")
   print(f"   Post diameter for cutout: {cutout_post_diameter}mm")
   
   # Get current bounding box of stock cutout
   current_cutout_bbox = stock_cutout_obj.Shape.BoundBox
   
   # Calculate post centre X position for cutout
   current_cutout_post_centre_x = current_cutout_bbox.XMax - (cutout_post_diameter / 2)
   current_cutout_post_top_z = current_cutout_bbox.ZMax
   
   print(f"   Current cutout post centre X: {current_cutout_post_centre_x:.1f}mm")
   print(f"   Current cutout post top Z: {current_cutout_post_top_z:.1f}mm")
   
   # Calculate offset needed to move cutout post to adjusted target position
   cutout_offset = Vector(
       cutout_target_x - current_cutout_post_centre_x,  # Move post centre to adjusted X
       0,                                                # Keep Y unchanged
       POST_TOP_Z - current_cutout_post_top_z           # Move post top to specified Z
   )
   
   # Apply translation to cutout
   cutout_translation_matrix = App.Matrix()
   cutout_translation_matrix.move(cutout_offset)
   positioned_cutout_shape = stock_cutout_obj.Shape.transformGeometry(cutout_translation_matrix)
   stock_cutout_obj.Shape = positioned_cutout_shape
   
   # Report final cutout position
   final_cutout_bbox = stock_cutout_obj.Shape.BoundBox
   final_cutout_post_centre_x = final_cutout_bbox.XMax - (cutout_post_diameter / 2)
   final_cutout_post_top_z = final_cutout_bbox.ZMax
   
   print(f"   ✅ Stock cutout positioned:")
   print(f"      Post centre X: {final_cutout_post_centre_x:.1f}mm (target: {cutout_target_x}mm)")
   print(f"      Post top Z: {final_cutout_post_top_z:.1f}mm (target: {POST_TOP_Z}mm)")
   
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
       
       # Create cutting plan for port half
       print(f"\n🗺️ Creating cutting plan for 3D printing...")
       print(f"🖨️ Printer: Bambu Labs HD2 (Build volume: {HD2_BUILD_X}x{HD2_BUILD_Y}x{HD2_BUILD_Z}mm)")
       port_plan = create_cutting_plan(port_half, "Port Half")
       
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
       
       # Perform the actual cutting operations (port half only)
       pieces = perform_cutting_operations(port_half, port_plan, doc)
       
       # Hide stock for cleaner view of pieces
       stock_obj.ViewObject.Visibility = False
       
       # Export individual pieces
       print(f"\n💾 Exporting individual pieces...")
       pieces_folder = f"{PRINT_FOLDER}/pieces_for_mirroring"
       os.makedirs(pieces_folder, exist_ok=True)
       
       exported_count = 0
       for piece_name, piece_shape in pieces:
           try:
               piece_path = f"{pieces_folder}/{BOAT_NAME}_{piece_name}.step"
               piece_shape.exportStep(piece_path)
               print(f"   ✅ Exported: {piece_name} → {piece_path}")
               exported_count += 1
           except Exception as e:
               print(f"   ❌ Failed to export {piece_name}: {e}")
       
       print(f"\n   📦 Successfully exported {exported_count}/{len(pieces)} pieces")
       
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