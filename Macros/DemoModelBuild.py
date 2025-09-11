"""
Demo Model Generator - Step 5A (Bare Bones) - REFACTORED FOR DEBUGGING
Imports the Cut Foil and Stock and prepares for demo print
Now includes splitting into two halves for 3D printing
Refactored to allow easy step skipping during debugging
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

# Import hole operations
try:
    from printer.hole_operations import add_z_cut_alignment_pins, add_x_cut_alignment_pins, add_y_half_joining_holes
    print("✅ Hole operations imported successfully")
except ImportError as e:
    print(f"❌ Failed to import hole operations: {e}")
    print("Using inline functions as fallback...")
    
    def add_z_cut_alignment_pins(shape, z_cut_position, 
                                 hole_diameter=6, support_diameter=10, 
                                 hole_depth=25):
        """
        Add alignment holes at a Z-cut position.
        Holes are placed at 20%, 40%, 60%, 80% of chord width.
        """
        from FreeCAD import Vector, Base
        
        print(f"      Adding alignment holes at Z={z_cut_position:.1f}")
        
        # Step 1: Find chord bounds at this Z
        slice_thickness = 1.0
        sample_slice = Part.makeBox(
            1000, 1000, slice_thickness,
            Vector(-500, -500, z_cut_position - slice_thickness/2)
        )
        
        try:
            cross_section = shape.common(sample_slice)
            chord_bbox = cross_section.BoundBox
            
            x_min = chord_bbox.XMin
            x_max = chord_bbox.XMax
            chord_width = x_max - x_min
            y_pos = 0 - 3 - hole_diameter/2
            
            print(f"         Chord: X from {x_min:.1f} to {x_max:.1f} (width={chord_width:.1f})")
            
        except:
            print(f"         ❌ Failed to find chord at Z={z_cut_position:.1f}")
            return shape
        
        # Step 2: Calculate hole positions
        hole_positions = []
        for fraction in [0.2, 0.4, 0.6, 0.9]:
            x_pos = x_min + (chord_width * fraction)
            hole_positions.append(Vector(x_pos, y_pos, z_cut_position))
        
        # Step 3: Create alignment holes
        result_shape = shape
        successful_holes = 0
        
        for i, pos in enumerate(hole_positions):
            hole_cylinder = Part.makeCylinder(
                hole_diameter / 2, hole_depth,
                pos - Vector(0, 0, hole_depth/2),
                Vector(0, 0, 1)
            )
            
            try:
                result_shape = result_shape.cut(hole_cylinder)
                successful_holes += 1
            except:
                print(f"         ⚠️ Failed to add hole {i+1}")
        
        print(f"         ✅ Added {successful_holes}/4 holes")
        return result_shape

    def add_x_cut_alignment_pins(shape, x_cut_position, z_start, z_end,
                                 hole_diameter=6, hole_depth=25):
        """
        Add alignment holes at an X-cut position.
        Holes are placed at 10%, 40%, 60%, 80% of slice height.
        """
        from FreeCAD import Vector, Base
        
        print(f"      Adding X-cut alignment holes at X={x_cut_position:.1f}")
        
        slice_height = z_end - z_start
        y_pos = 0 - 3 - hole_diameter/2
        
        print(f"         Slice from Z={z_start:.1f} to {z_end:.1f} (height={slice_height:.1f})")
        print(f"         Y position for holes: {y_pos:.1f}")
        
        # Calculate hole positions
        hole_positions = []
        for fraction in [0.1, 0.4, 0.6, 0.8]:
            z_pos = z_start + (slice_height * fraction)
            hole_positions.append(Vector(x_cut_position, y_pos, z_pos))
        
        result_shape = shape
        successful_holes = 0
        
        for i, pos in enumerate(hole_positions):
            hole_cylinder = Part.makeCylinder(
                hole_diameter / 2, hole_depth,
                pos - Vector(hole_depth/2, 0, 0),
                Vector(1, 0, 0)
            )
            
            try:
                result_shape = result_shape.cut(hole_cylinder)
                successful_holes += 1
            except:
                print(f"         ⚠️ Failed to add X-cut hole {i+1}")
        
        print(f"         ✅ Added {successful_holes}/4 X-cut holes")
        return result_shape

    def add_y_half_joining_holes(shape, z_start, z_end, section_name,
                                 hole_diameter=6, row_positions=[0.25, 0.75], 
                                 x_positions=[0.1, 0.4, 0.6, 0.9], hole_depth=25):
        """
        Add horizontal holes in Y-direction for joining port and starboard halves.
        """
        from FreeCAD import Vector, Base
        
        section_height = z_end - z_start
        print(f"      Adding Y-direction joining holes to {section_name}")
        print(f"         Section Z: {z_start:.1f} to {z_end:.1f} (height={section_height:.1f})")
        
        result_shape = shape
        total_holes = 0
        
        for row_frac in row_positions:
            z_position = z_start + (section_height * row_frac)
            print(f"         Row at Z={z_position:.1f} ({row_frac*100:.0f}% of section height)")
            
            slice_thickness = 1.0
            sample_slice = Part.makeBox(
                1000, 1000, slice_thickness,
                Vector(-500, -500, z_position - slice_thickness/2)
            )
            
            try:
                cross_section = shape.common(sample_slice)
                chord_bbox = cross_section.BoundBox
                
                x_min = chord_bbox.XMin
                x_max = chord_bbox.XMax
                chord_width = x_max - x_min
                
                print(f"            Chord: X from {x_min:.1f} to {x_max:.1f} (width={chord_width:.1f})")
                
                for x_frac in x_positions:
                    x_pos = x_min + (chord_width * x_frac)
                    
                    hole_cylinder = Part.makeCylinder(
                        hole_diameter / 2, hole_depth,
                        Vector(x_pos, -hole_depth/2, z_position),
                        Vector(0, -1, 0)
                    )
                    
                    try:
                        result_shape = result_shape.cut(hole_cylinder)
                        total_holes += 1
                    except:
                        print(f"            ⚠️ Failed to add hole at X={x_pos:.1f}")
                
            except:
                print(f"            ❌ Failed to find chord at Z={z_position:.1f}")
        
        expected_holes = len(row_positions) * len(x_positions)
        print(f"         ✅ Added {total_holes}/{expected_holes} joining holes")
        return result_shape


# Define foam filling holes function (always available, not in module)
def add_foam_filling_holes(shape, z_start, z_end, section_name, x_cut_position=None,
                          hole_diameter=10, y_position=-8):
    """
    Add foam filling holes - vertical holes for foam injection.
    One hole per piece, positioned at thicker part of foil.
    
    Args:
        shape: The shape to add holes to
        z_start: Bottom Z of the section
        z_end: Top Z of the section  
        section_name: Name for logging
        x_cut_position: X coordinate of cut (None if no X-cut)
        hole_diameter: Foam hole diameter (10mm)
        y_position: Y position for holes (-8mm)
    
    Returns:
        Modified shape with foam holes
    """
    from FreeCAD import Vector, Base
    
    section_height = z_end - z_start
    # Position foam hole at 75% of section height (thicker part)
    z_position = z_start + (section_height * 0.75)
    
    print(f"      Adding foam filling hole to {section_name}")
    print(f"         Hole at Z={z_position:.1f} (75% of section height)")
    
    # Find chord bounds at this Z
    slice_thickness = 1.0
    sample_slice = Part.makeBox(
        1000, 1000, slice_thickness,
        Vector(-500, -500, z_position - slice_thickness/2)
    )
    
    try:
        cross_section = shape.common(sample_slice)
        chord_bbox = cross_section.BoundBox
        
        x_min = chord_bbox.XMin
        x_max = chord_bbox.XMax
        chord_width = x_max - x_min
        
        print(f"            Chord: X from {x_min:.1f} to {x_max:.1f} (width={chord_width:.1f})")
        
        # Calculate hole position
        if x_cut_position is not None:
            # Has X-cut: position hole 8mm from cut line (toward leading edge)
            x_pos = x_cut_position - 8  # radius + 3mm clearance
            print(f"            X-cut at {x_cut_position:.1f}, hole at X={x_pos:.1f}")
        else:
            # No X-cut: position at geometric center
            x_pos = x_min + (chord_width * 0.5)
            print(f"            No X-cut, hole at center X={x_pos:.1f}")
        
        # Create vertical foam hole
        hole_cylinder = Part.makeCylinder(
            hole_diameter / 2,
            section_height + 10,  # Through entire section
            Vector(x_pos, y_position, z_start - 5),
            Vector(0, 0, 1)  # Z direction (vertical)
        )
        
        # Subtract hole from shape
        result_shape = shape.cut(hole_cylinder)
        print(f"         ✅ Added foam hole (10mm) at X={x_pos:.1f}, Y={y_position:.1f}, Z={z_position:.1f}")
        return result_shape
        
    except Exception as e:
        print(f"            ❌ Failed to add foam hole: {e}")
        return shape


def ensure_solid(shape, operation_name="operations"):
    """
    Ensure a shape is a solid, converting from compound if necessary.
    
    Args:
        shape: The shape to check/convert
        operation_name: Name of the operation for logging
    
    Returns:
        The shape as a solid (or best attempt)
    """
    print(f"\n🔧 Converting shape back to solid after {operation_name}...")
    try:
        if shape.ShapeType == "Compound":
            print(f"   Shape is compound, attempting to fuse into solid...")
            # Try to fuse the compound into a single solid
            shape = shape.fuse([])  # Fuse with empty list to consolidate
            if shape.ShapeType == "Solid":
                print(f"   ✅ Successfully converted to solid")
            else:
                print(f"   ⚠️ Still {shape.ShapeType}, but continuing...")
        else:
            print(f"   ✅ Shape is already {shape.ShapeType}")
    except Exception as e:
        print(f"   ⚠️ Fuse operation failed: {e}, continuing anyway...")
    
    return shape


print("Imports the Cut Foil and Stock and prepares for demo print")
# Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.4.0"  # Added Z-cut alignment pins

# Stock positioning parameters
POST_CENTRE_X = 323  # mm - X position for post centre
POST_TOP_Z = -75     # mm - Z position for top of post
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

# Global variables to share data between steps
doc = None
cut_foil_obj = None
stock_obj = None
stock_cutout_obj = None
port_half = None
port_half_obj = None  # FreeCAD object for visualization
port_plan = None
pieces = []
piece_objects = []


def update_view():
    """Update document and view to show current state"""
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()


def step_1_initialize_and_setup():
    """STEP 1: Initialize document and validate STEP files"""
    global doc
    
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
            return False
        print(f"   ✅ {name} STEP file valid")
    
    return True


def step_2_import_step_files():
    """STEP 2: Import all STEP files"""
    global cut_foil_obj, stock_obj, stock_cutout_obj
    
    try:
        print(f"\n📥 Importing STEP files using enhanced loader...")
        
        # Import cut foil
        cut_foil_path = f"{CUT_FOIL_FOLDER}/{CUT_FOIL_STEP}"
        _, cut_foil_objects = load_step(cut_foil_path, MACRO_NAME, verbose=True)
        if not cut_foil_objects:
            raise StepFileError("No objects imported from cut foil file")
        cut_foil_obj = cut_foil_objects[0]
        cut_foil_obj.Label = f"{BOAT_NAME}_Cut_Foil"
        
        # Import stock
        stock_path = f"{STOCK_FOLDER}/{STOCK_STEP}"
        _, stock_objects = load_step(stock_path, MACRO_NAME, verbose=True)
        if not stock_objects:
            raise StepFileError("No objects imported from stock file")
        stock_obj = stock_objects[0]
        stock_obj.Label = f"{BOAT_NAME}_Stock"
        
        # Import stock cutout
        stock_cutout_path = f"{CUTOUT_FOLDER}/{STOCK_CUTOUT_STEP}"
        _, stock_cutout_objects = load_step(stock_cutout_path, MACRO_NAME, verbose=True)
        if not stock_cutout_objects:
            raise StepFileError("No objects imported from stock cutout file")
        stock_cutout_obj = stock_cutout_objects[0]
        stock_cutout_obj.Label = f"{BOAT_NAME}_Stock_Cutout"
        
        # Update view
        update_view()
        
        return True
        
    except StepFileError as e:
        print(f"❌ Failed to import STEP files: {e}")
        return False


def step_3_position_stock_components():
    """STEP 3: Position all stock components"""
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
    update_view()
    print(f"   ✅ Recompute done, ready for split operation")
    
    return True


def step_4_split_solid_foil_at_y_zero():
    """STEP 4: Split solid foil at Y=0 for port/starboard (BEFORE boolean cut)"""
    global port_half, port_half_obj
    
    print(f"\n✂️ Splitting solid foil at Y=0...")
    
    try:
        # Get bounding box for reference
        from FreeCAD import Vector, Base
        bbox = cut_foil_obj.Shape.BoundBox
        print(f"   Solid foil bounds:")
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
        
        # Extract port half only from SOLID foil
        print(f"   Creating port half from solid foil (will be mirrored for starboard)...")
        port_half = cut_foil_obj.Shape.common(box_negative_y)
        
        # Verify the split worked
        if port_half.isNull() or len(port_half.Faces) == 0:
            print(f"   ❌ Port half is empty! Trying alternative method...")
            box_positive_y = Part.makeBox(
                bbox.XLength + 200,
                bbox.YMax + 100 + overlap,
                bbox.ZLength + 200,
                Base.Vector(bbox.XMin - 100, -overlap, bbox.ZMin - 100)
            )
            port_half = cut_foil_obj.Shape.cut(box_positive_y)
        
        # Create FreeCAD object for port half visualization
        port_half_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Port_Half_Solid")
        port_half_obj.Shape = port_half
        port_half_obj.ViewObject.Visibility = True
        port_half_obj.ViewObject.ShapeColor = (0.2, 0.5, 0.8)  # Blue
        port_half_obj.ViewObject.Transparency = 30
        port_half_obj.Label = f"{BOAT_NAME}_Port_Half_Solid"
        
        # Hide the original foil and stock for cleaner view
        cut_foil_obj.ViewObject.Visibility = False
        stock_obj.ViewObject.Visibility = False
        stock_cutout_obj.ViewObject.Visibility = False
        
        print(f"   ✅ Solid port half created with {len(port_half.Faces)} faces")
        print(f"   ℹ️ This solid half will have holes added, then be hollowed")
        
        # Update view to focus on port half
        update_view()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Processing failed: {e}")
        return False


def step_5_create_cutting_plan():
    """STEP 5: Create cutting plan for 3D printing"""
    global port_plan
    
    print(f"\n🗺️ Creating cutting plan for 3D printing...")
    print(f"🖨️ Printer: Bambu Labs HD2 (Build volume: {HD2_BUILD_X}x{HD2_BUILD_Y}x{HD2_BUILD_Z}mm)")
    port_plan = create_cutting_plan(port_half, "Port Half", PRINT_MAX_SIZE)
    
    return True


def step_6_add_z_cut_alignment_pins():
    """STEP 6: Add Z-cut alignment pins to solid port half"""
    global port_half
    
    print(f"\n🔩 Adding Z-cut alignment holes to solid port half...")
    print(f"   Adding 4 holes at each Z-cut position")
    print(f"   Holes at 20%, 40%, 60%, 80% of chord width")
    
    if port_plan['z_slices'] > 1:
        for i in range(1, port_plan['z_slices']):
            z_cut_position = port_plan['bbox'].ZMin + (i * port_plan['z_slice_height'])
            port_half = add_z_cut_alignment_pins(
                port_half, z_cut_position,
                HOLE_DIAMETER, SUPPORT_DIAMETER, HOLE_DEPTH
            )
    
    # Update the visualization object with new holes
    port_half_obj.Shape = port_half
    port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Z_holes"
    
    # Update view
    update_view()
    print(f"   🔄 View updated to show Z-cut alignment holes in solid")
    
    return True


def step_7_add_x_cut_alignment_pins():
    """STEP 7: Add X-cut alignment pins to solid port half"""
    global port_half
    
    print(f"\n🔧 Adding X-cut alignment holes to solid port half...")
    print(f"   Adding 4 holes at each X-cut position")
    print(f"   Holes at 10%, 40%, 60%, 80% of slice height")
    
    for slice_info in port_plan['slice_plans']:
        if slice_info['needs_x_split']:
            x_center = slice_info['x_center']
            z_start = slice_info['z_start']
            z_end = slice_info['z_end']
            port_half = add_x_cut_alignment_pins(
                port_half, x_center, z_start, z_end,
                HOLE_DIAMETER, HOLE_DEPTH
            )
    
    # Update the visualization object with all alignment holes
    port_half_obj.Shape = port_half
    port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Alignment_Holes"
    port_half_obj.ViewObject.ShapeColor = (0.1, 0.6, 0.3)  # Green to show completion
    
    # Update view
    update_view()
    print(f"   🔄 View updated to show all alignment holes in solid")
    print(f"   ✅ Solid port half ready with all alignment features")
    
    return True


def step_8_add_y_half_joining_holes():
    """STEP 8: Add Y-direction holes for joining port and starboard halves"""
    global port_half
    
    print(f"\n🔩 Adding Y-direction holes for joining port and starboard halves...")
    print(f"   Adding 2 rows per section at 25% and 75% of height")
    print(f"   Adding 4 holes per row at 10%, 40%, 60%, 90% of chord")
    print(f"   Holes oriented horizontally (Y-axis) for joining halves")
    
    # Add joining holes to each planned section
    for i, slice_info in enumerate(port_plan['slice_plans']):
        section_num = i + 1
        z_start = slice_info['z_start']
        z_end = slice_info['z_end']
        section_name = f"Section {section_num}"
        
        print(f"\n   Processing {section_name} (Z: {z_start:.0f} to {z_end:.0f}mm)")
        
        port_half = add_y_half_joining_holes(
            port_half, z_start, z_end, section_name,
            HOLE_DIAMETER, [0.25, 0.75], [0.1, 0.4, 0.6, 0.9], HOLE_DEPTH
        )
    
    # Use the new ensure_solid function
    port_half = ensure_solid(port_half, "hole operations")
    
    # Update the visualization object with joining holes
    port_half_obj.Shape = port_half
    port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Joining_Holes"
    port_half_obj.ViewObject.ShapeColor = (0.8, 0.3, 0.1)  # Orange to show joining holes added
    
    # Update view
    update_view()
    print(f"   🔄 View updated to show joining holes in solid")
    print(f"   ✅ Solid port half complete with alignment and joining features")
    
    return True


def step_9_add_foam_filling_holes():
    """STEP 9: Add foam filling holes for foam injection"""
    global port_half
    
    print(f"\n🔩 Adding foam filling holes...")
    print(f"   Adding 10mm diameter holes for foam injection")
    print(f"   One hole per piece at 75% height (thicker part)")
    print(f"   Position: 8mm from X-cut line, Y=-8mm")
    
    # Add foam holes to each planned section
    for i, slice_info in enumerate(port_plan['slice_plans']):
        section_num = i + 1
        z_start = slice_info['z_start']
        z_end = slice_info['z_end']
        section_name = f"Section {section_num}"
        
        # Get X-cut position if this section needs splitting
        x_cut_position = slice_info.get('x_center') if slice_info['needs_x_split'] else None
        
        print(f"\n   Processing {section_name} (Z: {z_start:.0f} to {z_end:.0f}mm)")
        
        port_half = add_foam_filling_holes(
            port_half, z_start, z_end, section_name, x_cut_position,
            hole_diameter=10, y_position=-8
        )
    
    # Ensure solid after foam holes
    port_half = ensure_solid(port_half, "foam filling operations")
    
    # Update the visualization object with foam holes
    port_half_obj.Shape = port_half
    port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Foam_Holes"
    port_half_obj.ViewObject.ShapeColor = (0.6, 0.2, 0.8)  # Purple to show foam holes added
    
    # Update view
    update_view()
    print(f"   🔄 View updated to show foam holes")
    print(f"   ✅ Foam filling holes added")
    
    return True


def step_10_pre_boolean_checks():
    """STEP 10: Perform pre-Boolean operation validation checks"""
    print(f"\n🔍 Performing pre-Boolean operation checks...")
    print(f"   Checking port half with holes vs stock cutout")
    
    # Check 1: Validate shapes
    if not port_half.isValid():
        print(f"❌ Port half shape is not valid!")
        print(f"   The geometry has errors that prevent boolean operations.")
        print(f"   Check hole cutting operations for issues.")
        return False
    
    if not stock_cutout_obj.Shape.isValid():
        print(f"❌ Stock cutout shape is not valid!")
        print(f"   The geometry has errors that prevent boolean operations.")
        print(f"   Please check the source STEP file for issues.")
        return False
    
    print(f"   ✅ Both shapes are valid")
    
    # Check 2: Ensure shapes are solids
    if not port_half.ShapeType == "Solid":
        print(f"❌ Port half is not a solid! (Type: {port_half.ShapeType})")
        print(f"   Boolean cut operations require solid objects.")
        print(f"   The shape may have been corrupted during hole cutting.")
        return False
    
    if not stock_cutout_obj.Shape.ShapeType == "Solid":
        print(f"❌ Stock cutout is not a solid! (Type: {stock_cutout_obj.Shape.ShapeType})")
        print(f"   Boolean cut operations require solid objects.")
        print(f"   The imported shape may be a shell or open surface.")
        return False
    
    print(f"   ✅ Both shapes are solids")
    
    # Check 3: Check for intersection
    common_volume = port_half.common(stock_cutout_obj.Shape)
    if common_volume.Volume < 0.001:  # Less than 0.001 mm³
        print(f"❌ No meaningful intersection between shapes!")
        print(f"   Common volume: {common_volume.Volume:.6f} mm³")
        print(f"   The stock cutout and port half do not overlap sufficiently for a boolean cut.")
        print(f"   Check positioning or shape dimensions.")
        return False
    
    print(f"   ✅ Shapes intersect properly (common volume: {common_volume.Volume:.2f} mm³)")
    
    # Check 4: Check bounding box overlap
    port_bbox = port_half.BoundBox
    cutout_bbox = stock_cutout_obj.Shape.BoundBox
    
    if not (port_bbox.intersect(cutout_bbox)):
        print(f"❌ Bounding boxes do not intersect!")
        print(f"   Port half bounds: X({port_bbox.XMin:.1f}, {port_bbox.XMax:.1f})")
        print(f"                     Y({port_bbox.YMin:.1f}, {port_bbox.YMax:.1f})")
        print(f"                     Z({port_bbox.ZMin:.1f}, {port_bbox.ZMax:.1f})")
        print(f"   Cutout bounds: X({cutout_bbox.XMin:.1f}, {cutout_bbox.XMax:.1f})")
        print(f"                  Y({cutout_bbox.YMin:.1f}, {cutout_bbox.YMax:.1f})")
        print(f"                  Z({cutout_bbox.ZMin:.1f}, {cutout_bbox.ZMax:.1f})")
        return False
    
    print(f"   ✅ Bounding boxes overlap correctly")
    
    # Check 5: Check shape complexity
    print(f"   ℹ️ Shape complexity:")
    print(f"      Port half with holes: {len(port_half.Faces)} faces, {len(port_half.Edges)} edges")
    print(f"      Stock cutout: {len(stock_cutout_obj.Shape.Faces)} faces, {len(stock_cutout_obj.Shape.Edges)} edges")
    
    if len(port_half.Faces) > 10000 or len(stock_cutout_obj.Shape.Faces) > 10000:
        print(f"   ⚠️ Warning: High face count detected. Boolean operation may be slow.")
    
    print(f"\n✅ All pre-Boolean checks passed successfully!")
    return True


def step_11_boolean_cut_operation():
    """STEP 11: Perform boolean cut to create hollowed port half"""
    global port_half
    
    print(f"\n🔧 Creating cavity with boolean cut on port half...")
    print(f"   ⏳ This may take a moment for complex geometry...")
    try:
        # Perform the cut operation on the port half with holes
        original_faces = len(port_half.Faces)
        hollowed_port_half = port_half.cut(stock_cutout_obj.Shape)
        
        # Update the port half with the hollowed version
        port_half = hollowed_port_half
        
        # Update visualization object
        port_half_obj.Shape = port_half
        port_half_obj.Label = f"{BOAT_NAME}_Port_Half_Hollowed"
        port_half_obj.ViewObject.ShapeColor = (0.3, 0.3, 0.4)  # Dark grey
        port_half_obj.ViewObject.Transparency = 70  # Make transparent to see cavity
        
        # Show stock for reference
        stock_obj.ViewObject.Visibility = True
        stock_obj.ViewObject.ShapeColor = (0.8, 0.8, 0.9)  # Light steel
        
        print(f"   ✅ Cavity created successfully in port half")
        print(f"   Original port half faces: {original_faces}")
        print(f"   Hollowed port half faces: {len(port_half.Faces)}")
        
        # Update view
        update_view()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Boolean cut failed: {e}")
        return False


def step_12_cut_pieces():
    """STEP 12: Cut hollowed port half into pieces according to plan"""
    global pieces, piece_objects
    
    from FreeCAD import Vector, Base
    
    print(f"\n📐 Cutting pieces...")
    print(f"   Alignment, joining, and foam holes will be split automatically by cuts")
    
    # Hide the working port half object
    port_half_obj.ViewObject.Visibility = False
    stock_obj.ViewObject.Visibility = False
    
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
    
    # Update view to show pieces
    update_view()
    
    return True


def step_13_export_pieces():
    """STEP 13: Export individual pieces to STEP files"""
    print(f"\n💾 Exporting individual pieces with alignment, joining, and foam features...")
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
    
    return True


def step_14_final_view_and_summary():
    """STEP 14: Update view and print final summary"""
    # Update view
    update_view()
    
    # Summary
    print(f"\n📋 FINAL SUMMARY:")
    print(f"   🔄 MIRRORING WORKFLOW:")
    print(f"      1. Import pieces into Bambu Studio")
    print(f"      2. Print one set as-is (port half)")
    print(f"      3. Mirror and print again (creates starboard half)")
    print(f"      4. Join using 6mm dowels through alignment holes")
    print(f"      5. Join port and starboard halves using Y-direction joining holes")
    print(f"      6. Inject foam through 10mm foam filling holes")
    print(f"   Alignment features:")
    print(f"      • Z-cuts: 4 holes at 20%, 40%, 60%, 80% of chord")
    print(f"      • X-cuts: 4 holes at 10%, 40%, 60%, 80% of slice height")
    print(f"      • Hole diameter: {HOLE_DIAMETER}mm (for dowels)")
    print(f"      • Hole depth: {HOLE_DEPTH}mm")
    print(f"      • Z-holes: vertical (perpendicular to Z-cut plane)")
    print(f"      • X-holes: horizontal (perpendicular to X-cut plane)")
    print(f"   Half-joining features:")
    print(f"      • Y-direction holes: 8 holes per section (2 rows × 4 holes)")
    print(f"      • Rows at 25% and 75% of section height")
    print(f"      • Holes at 10%, 40%, 60%, 90% of chord width")
    print(f"      • Horizontal holes for joining port and starboard halves")
    print(f"   Foam filling features:")
    print(f"      • 10mm diameter vertical holes for foam injection")
    print(f"      • One hole per piece at 75% height (thicker part)")
    print(f"      • Position: 8mm from X-cut line, Y=-8mm")
    print(f"   Processing approach:")
    print(f"      • Split solid foil first (more reliable)")
    print(f"      • Add all holes to solid geometry (cleaner cuts)")
    print(f"      • Boolean cut last (on port half only)")
    print(f"   Pieces created (to be mirrored):")
    piece_list = [name for name, _ in pieces]
    piece_list.sort()  # Sort for logical order
    for piece_name in piece_list:
        print(f"      • {piece_name}")
    print(f"   📦 UNIQUE PIECES: {len(pieces)}")
    print(f"   📦 TOTAL AFTER MIRRORING: {len(pieces) * 2}")
    
    pieces_folder = f"{PRINT_FOLDER}/pieces_for_mirroring"
    print(f"\n✅ Complete! Pieces ready for mirroring in slicer.")
    print(f"📁 Files saved to: {pieces_folder}")
    
    return True


def run():
    """MASTER FUNCTION: Execute all steps in sequence - comment out steps to skip during debugging"""
    
    # STEP 1: Initialize and validate
    if not step_1_initialize_and_setup():
        return
    
    # STEP 2: Import STEP files
    if not step_2_import_step_files():
        return
    
    # STEP 3: Position stock components
    if not step_3_position_stock_components():
        return
    
    # STEP 4: Split solid foil at Y=0 (BEFORE boolean cut)
    if not step_4_split_solid_foil_at_y_zero():
        return
    
    # STEP 5: Create cutting plan for 3D printing
    if not step_5_create_cutting_plan():
        return
    
    # STEP 6: Add Z-cut alignment pins to solid port half
    if not step_6_add_z_cut_alignment_pins():
        return
    
    # STEP 7: Add X-cut alignment pins to solid port half
    if not step_7_add_x_cut_alignment_pins():
        return
    
    # STEP 8: Add Y-direction holes for joining halves to solid port half
    if not step_8_add_y_half_joining_holes():
        return
    
    # STEP 9: Add foam filling holes (NEW)
    if not step_9_add_foam_filling_holes():
        return
    
    # STEP 10: Pre-Boolean checks
    if not step_10_pre_boolean_checks():
        return
    
    # STEP 11: Boolean cut operation (port half only, AFTER holes)
    if not step_11_boolean_cut_operation():
        return
    
    # STEP 12: Cut pieces according to plan
    if not step_12_cut_pieces():
        return
    
    # STEP 13: Export pieces to STEP files
    if not step_13_export_pieces():
        return
    
    # STEP 14: Final view update and summary
    step_14_final_view_and_summary()


# Run the script
run()