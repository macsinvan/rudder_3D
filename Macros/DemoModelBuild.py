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
from printer.alignment_features import create_supported_alignment_holes, visualize_alignment_features
from helpers.step_save_load import load_step, save_step, validate_step_file, StepFileError

print("Imports the Cut Foil and Stock and prepares for demo print")
# Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.4.0"  # Added Z-cut alignment pins

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

# Alignment hole parameters - UPDATED FOR SUPPORTED HOLES
HOLE_DIAMETER = 6  # mm - dowel diameter
SUPPORT_DIAMETER = 10  # mm - support cylinder diameter
HOLE_DEPTH = 25  # mm - depth of holes
EDGE_DISTANCE = 20  # mm - distance from edges for hole placement

# Visualization
EXPLOSION_FACTOR = 0  # mm - set to 0 for exact positions, >0 for separated view
VISUALIZE_ALIGNMENT = False  # Set True to see alignment features as separate objects

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


def add_z_cut_alignment_pins(shape, z_cut_position, 
                             hole_diameter=6, support_diameter=10, 
                             hole_depth=25):
    """
    Add alignment pins at a Z-cut position.
    Pins are placed at 20%, 40%, 60%, 80% of chord width.
    
    Args:
        shape: The shape to add pins to
        z_cut_position: Z coordinate of the cut
        hole_diameter: Dowel hole diameter (6mm)
        support_diameter: Outer support diameter (10mm)
        hole_depth: Pin length (25mm)
    
    Returns:
        Modified shape with alignment pins
    """
    from FreeCAD import Vector, Base
    
    print(f"      Adding alignment pins at Z={z_cut_position:.1f}")
    
    # Step 1: Find chord bounds at this Z
    # Create thin horizontal slice
    slice_thickness = 1.0
    sample_slice = Part.makeBox(
        1000,  # Large X
        1000,  # Large Y  
        slice_thickness,
        Vector(-500, -500, z_cut_position - slice_thickness/2)
    )
    
    # Get intersection
    try:
        cross_section = shape.common(sample_slice)
        chord_bbox = cross_section.BoundBox
        
        x_min = chord_bbox.XMin
        x_max = chord_bbox.XMax
        chord_width = x_max - x_min
        
        print(f"         Chord: X from {x_min:.1f} to {x_max:.1f} (width={chord_width:.1f})")
        
    except:
        print(f"         ❌ Failed to find chord at Z={z_cut_position:.1f}")
        return shape
    
    # Step 2: Calculate pin positions (20%, 40%, 60%, 80% along chord)
    pin_positions = []
    for fraction in [0.2, 0.4, 0.6, 0.8]:
        x_pos = x_min + (chord_width * fraction)
        pin_positions.append(Vector(x_pos, 0, z_cut_position))
    
    # Step 3: Create hollow alignment cylinders
    wall_thickness = 1.2
    result_shape = shape
    successful_pins = 0
    
    for i, pos in enumerate(pin_positions):
        # Create hollow support structure
        # Outer cylinder
        outer_cyl = Part.makeCylinder(
            support_diameter / 2,
            hole_depth,
            pos - Vector(0, 0, hole_depth/2),  # Center on cut plane
            Vector(0, 0, 1)  # Z direction
        )
        
        # Hollow out the middle
        middle_hollow = Part.makeCylinder(
            (support_diameter / 2) - wall_thickness,
            hole_depth + 2,
            pos - Vector(0, 0, hole_depth/2 + 1),
            Vector(0, 0, 1)
        )
        
        # Dowel hole
        dowel_hole = Part.makeCylinder(
            hole_diameter / 2,
            hole_depth + 2,
            pos - Vector(0, 0, hole_depth/2 + 1),
            Vector(0, 0, 1)
        )
        
        # Create hollow cylinder
        hollow_pin = outer_cyl.cut(middle_hollow)
        hollow_pin = hollow_pin.cut(dowel_hole)
        
        # Add to shape
        try:
            result_shape = result_shape.fuse(hollow_pin)
            successful_pins += 1
        except:
            print(f"         ⚠️ Failed to add pin {i+1}")
    
    print(f"         ✅ Added {successful_pins}/4 pins")
    return result_shape


def run():
   print(f"\n🎭 Demo Model Generator v{VERSION} (Refactored)")
   print(f"✨ VERSION {VERSION} - Z-cut alignment pins added")
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
   
   # Split the hollowed foil at Y=0 for port/starboard
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
       
       # Add Z-cut alignment pins BEFORE cutting
       print(f"\n🔩 Adding Z-cut alignment pins before slicing...")
       print(f"   Adding 4 pins at each Z-cut position")
       print(f"   Pins at 20%, 40%, 60%, 80% of chord width")
       
       if port_plan['z_slices'] > 1:
           for i in range(1, port_plan['z_slices']):
               z_cut_position = port_plan['bbox'].ZMin + (i * port_plan['z_slice_height'])
               port_half = add_z_cut_alignment_pins(
                   port_half, z_cut_position,
                   HOLE_DIAMETER, SUPPORT_DIAMETER, HOLE_DEPTH
               )
       
       print(f"\n📐 Cutting pieces...")
       print(f"   Z-alignment pins will be split automatically by cuts")
       
       # Modified cutting operations
       pieces = []
       piece_objects = []
       
       # Cut into Z slices
       for i, slice_info in enumerate(port_plan['slice_plans']):
           slice_num = i + 1
           z_start = slice_info['z_start']
           z_end = slice_info['z_end']
           
           print(f"\n   Processing slice {slice_num} (Z: {z_start:.0f} to {z_end:.0f}mm)")
           
           # Create cutting boxes for this slice
           slice_bbox = port_half.BoundBox
           
           # Box to isolate this Z slice
           slice_box = Part.makeBox(
               slice_bbox.XLength + 200,
               slice_bbox.YLength + 200,
               z_end - z_start,
               Base.Vector(slice_bbox.XMin - 100, slice_bbox.YMin - 100, z_start)
           )
           
           # Extract the slice
           try:
               slice_shape = port_half.common(slice_box)
               
               # Now check if X-split is needed
               if slice_info['needs_x_split']:
                   x_center = slice_info['x_center']
                   print(f"      Splitting at X={x_center:.0f}mm")
                   
                   # Create boxes for left (A) and right (B) pieces
                   left_box = Part.makeBox(
                       x_center - slice_bbox.XMin + 10,
                       slice_bbox.YLength + 200,
                       z_end - z_start + 10,
                       Base.Vector(slice_bbox.XMin - 10, slice_bbox.YMin - 100, z_start - 5)
                   )
                   
                   right_box = Part.makeBox(
                       slice_bbox.XMax - x_center + 10,
                       slice_bbox.YLength + 200,
                       z_end - z_start + 10,
                       Base.Vector(x_center, slice_bbox.YMin - 100, z_start - 5)
                   )
                   
                   # Create A and B pieces
                   piece_a = slice_shape.common(left_box)
                   piece_b = slice_shape.common(right_box)
                   
                   # Note: X-alignment would go here if needed
                   
                   # Name pieces
                   name_a = f"{slice_num}A"
                   name_b = f"{slice_num}B"
                   
                   pieces.append((name_a, piece_a))
                   pieces.append((name_b, piece_b))
                   
                   print(f"      ✅ Created pieces {name_a} and {name_b}")
                   
                   # Create FreeCAD objects
                   obj_a = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name_a}")
                   obj_a.Shape = piece_a
                   obj_a.ViewObject.ShapeColor = (0.2 + i*0.15, 0.4, 0.6)
                   obj_a.ViewObject.Transparency = 20
                   
                   if EXPLOSION_FACTOR > 0:
                       obj_a.Placement.Base.x -= EXPLOSION_FACTOR
                       obj_a.Placement.Base.z += i * EXPLOSION_FACTOR
                   
                   piece_objects.append(obj_a)
                   
                   obj_b = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name_b}")
                   obj_b.Shape = piece_b
                   obj_b.ViewObject.ShapeColor = (0.25 + i*0.15, 0.4, 0.65)
                   obj_b.ViewObject.Transparency = 20
                   
                   if EXPLOSION_FACTOR > 0:
                       obj_b.Placement.Base.x += EXPLOSION_FACTOR
                       obj_b.Placement.Base.z += i * EXPLOSION_FACTOR
                   
                   piece_objects.append(obj_b)
                   
               else:
                   # Single piece for this slice (no X-split needed)
                   name = f"{slice_num}A"
                   pieces.append((name, slice_shape))
                   
                   print(f"      ✅ Created piece {name} (no X-split needed)")
                   
                   # Create FreeCAD object
                   obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name}")
                   obj.Shape = slice_shape
                   obj.ViewObject.ShapeColor = (0.2 + i*0.15, 0.4, 0.6)
                   obj.ViewObject.Transparency = 20
                   
                   if EXPLOSION_FACTOR > 0:
                       obj.Placement.Base.z += i * EXPLOSION_FACTOR
                   
                   piece_objects.append(obj)
                   
           except Exception as e:
               print(f"      ❌ Failed to create slice: {e}")
       
       # Hide stock for cleaner view of pieces
       stock_obj.ViewObject.Visibility = False
       
       # Export individual pieces using enhanced STEP saver
       print(f"\n💾 Exporting individual pieces with alignment features...")
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
       print(f"      4. Join using 6mm dowels through alignment holes")
       print(f"   Alignment features:")
       print(f"      • Z-cuts: 4 pins at 20%, 40%, 60%, 80% of chord")
       print(f"      • Hole diameter: {HOLE_DIAMETER}mm (for dowels)")
       print(f"      • Support diameter: {SUPPORT_DIAMETER}mm")
       print(f"      • Hole depth: {HOLE_DEPTH}mm")
       print(f"      • Hollow structure with {1.2}mm walls")
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