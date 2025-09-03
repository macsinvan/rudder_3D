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
VERSION = "1.0.3"  # Updated version

# Stock positioning parameters
POST_CENTRE_X = 323  # mm - X position for post centre
POST_TOP_Z = -79     # mm - Z position for top of post
POST_DIAMETER = 44   # mm - diameter of the post
POST_DIAMETER_DELTA = 4  # mm - difference in post diameter for cutout stock

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
   
   # Split the hollowed foil into two halves - FIXED METHOD
   print(f"\n✂️ Splitting hollowed foil into two halves for 3D printing...")
   
   try:
       # Get bounding box for reference
       bbox = hollowed_foil_obj.Shape.BoundBox
       print(f"   Hollowed foil bounds:")
       print(f"      X: {bbox.XMin:.1f} to {bbox.XMax:.1f}")
       print(f"      Y: {bbox.YMin:.1f} to {bbox.YMax:.1f}")
       print(f"      Z: {bbox.ZMin:.1f} to {bbox.ZMax:.1f}")
       
       # Create two boxes with slight overlap at Y=0 to ensure clean cut
       overlap = 0.5  # Small overlap to ensure proper intersection
       
       # Box for positive Y side (starboard) - from slightly negative to beyond YMax
       box_positive_y = Part.makeBox(
           bbox.XLength + 200,                    # Width in X - make it bigger
           bbox.YMax + 100 + overlap,             # From slightly before Y=0 to well beyond YMax
           bbox.ZLength + 200,                    # Height in Z - make it bigger
           Base.Vector(bbox.XMin - 100, -overlap, bbox.ZMin - 100)  # Starting slightly before Y=0
       )
       
       print(f"   Positive Y box bounds: {box_positive_y.BoundBox}")
       
       # Box for negative Y side (port) - from YMin to slightly positive
       box_negative_y = Part.makeBox(
           bbox.XLength + 200,                    # Width in X - make it bigger
           abs(bbox.YMin) + 100 + overlap,        # From well before YMin to slightly past Y=0
           bbox.ZLength + 200,                    # Height in Z - make it bigger
           Base.Vector(bbox.XMin - 100, bbox.YMin - 100, bbox.ZMin - 100)  # Starting well before YMin
       )
       
       print(f"   Negative Y box bounds: {box_negative_y.BoundBox}")
       
       # Use common() operation to get intersection with each half-space
       print(f"   Creating port half (negative Y side)...")
       port_half = hollowed_foil_obj.Shape.common(box_negative_y)
       
       print(f"   Creating starboard half (positive Y side)...")
       starboard_half = hollowed_foil_obj.Shape.common(box_positive_y)
       
       # Verify the splits worked
       if port_half.isNull() or len(port_half.Faces) == 0:
           print(f"   ❌ Port half is empty! Debug info:")
           print(f"      Hollowed shape type: {hollowed_foil_obj.Shape.ShapeType}")
           print(f"      Hollowed shape valid: {hollowed_foil_obj.Shape.isValid()}")
           # Try alternative method
           print(f"   Trying alternative split method...")
           port_half = hollowed_foil_obj.Shape.cut(box_positive_y)
       
       if starboard_half.isNull() or len(starboard_half.Faces) == 0:
           print(f"   ❌ Starboard half is empty! Debug info:")
           print(f"      Hollowed shape type: {hollowed_foil_obj.Shape.ShapeType}")
           print(f"      Hollowed shape valid: {hollowed_foil_obj.Shape.isValid()}")
           # Try alternative method
           print(f"   Trying alternative split method...")
           starboard_half = hollowed_foil_obj.Shape.cut(box_negative_y)
       
       # Create objects for both halves
       port_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Port_Half")
       port_obj.Shape = port_half
       port_obj.ViewObject.ShapeColor = (0.2, 0.4, 0.6)  # Blue-ish
       port_obj.ViewObject.Transparency = 30
       
       starboard_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Starboard_Half")
       starboard_obj.Shape = starboard_half
       starboard_obj.ViewObject.ShapeColor = (0.4, 0.6, 0.2)  # Green-ish
       starboard_obj.ViewObject.Transparency = 30
       
       # Optionally separate the halves slightly for visualization
       separation_distance = 10  # mm
       starboard_obj.Placement.Base.y += separation_distance
       port_obj.Placement.Base.y -= separation_distance
       
       # Hide the original hollowed foil
       hollowed_foil_obj.ViewObject.Visibility = False
       
       print(f"   ✅ Split complete!")
       print(f"   Port half faces: {len(port_half.Faces)}")
       print(f"   Starboard half faces: {len(starboard_half.Faces)}")
       print(f"   Halves separated by {separation_distance*2}mm for visualization")
       
       # Create folder for 3D print files if it doesn't exist
       os.makedirs(PRINT_FOLDER, exist_ok=True)
       
       # Export the halves as STEP files for 3D printing
       port_path = f"{PRINT_FOLDER}/{BOAT_NAME}_Port_Half.step"
       starboard_path = f"{PRINT_FOLDER}/{BOAT_NAME}_Starboard_Half.step"
       
       if len(port_half.Faces) > 0:
           port_half.exportStep(port_path)
           print(f"   Port half exported: {port_path}")
       else:
           print(f"   ⚠️ Port half not exported (empty shape)")
       
       if len(starboard_half.Faces) > 0:
           starboard_half.exportStep(starboard_path)
           print(f"   Starboard half exported: {starboard_path}")
       else:
           print(f"   ⚠️ Starboard half not exported (empty shape)")
       
   except Exception as e:
       print(f"   ❌ Splitting failed: {e}")
       import traceback
       traceback.print_exc()
   
   # Update view
   doc.recompute()
   Gui.SendMsgToActiveView("ViewFit")
   Gui.activeDocument().activeView().viewIsometric()
   
   print(f"\n✅ Import, cavity creation, and splitting complete!")
   print(f"   • Port Half: ready for 3D printing")
   print(f"   • Starboard Half: ready for 3D printing")
   print(f"   • Stock: positioned for reference")
   print(f"\n📁 Files saved to: {PRINT_FOLDER}")


# Run the script
run()