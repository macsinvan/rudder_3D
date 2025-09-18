"""
Demo Model Generator - REFACTORED
Imports the Cut Foil and Stock and prepares for demo print
Creates port half with alignment holes for 3D printing
"""
import os
import sys
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector, Base

# Add paths to find our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))  # For printer module
sys.path.insert(0, os.path.expanduser("~/Rudder_Code"))  # For helpers module

from printer.cutting_operations import create_cutting_plan
from printer.stock_positioning import position_all_stock_components
from helpers.step_save_load import load_step, save_step, validate_step_file, StepFileError

# ============================================================================
# CONFIGURATION SECTION - All adjustable parameters in one place
# ============================================================================

# Boat Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.5.2"  # Z-holes now use foam configuration

# Stock Positioning (mm)
STOCK_CONFIG = {
    'post_center_x': 380,
    'post_top_z': -72,
    'post_diameter': 44,
    'post_diameter_delta': 4,  # Difference for cutout
}

# 3D Printer Specifications - Bambu Labs HD2 (mm)
PRINTER_CONFIG = {
    'build_x': 325,
    'build_y': 320,
    'build_z': 325,
    'max_print_size': 310,  # Build size minus 10mm safety margin
}

# Alignment Hole Configuration (mm) - Used for X and Y holes
HOLE_CONFIG = {
    'diameter': 6,          # Dowel diameter
    'depth': 25,            # Hole depth
    'y_offset': 3,          # Distance from Y=0 plane to hole center
}

# Foam Hole Configuration (mm) - Used for Z holes
FOAM_HOLE_CONFIG = {
    'diameter': 12,         # Foam injection hole diameter
    'depth': 25,            # Hole depth
    'y_offset': 3,          # Distance from Y=0 plane to hole center
}

# Hole Position Arrays (as fractions of dimension)
HOLE_POSITIONS = {
    'z_cut': [0.30, 0.45, 0.60, 0.90],          # Along chord width
    'x_cut': [0.1, 0.4, 0.6, 0.8],        # Along slice height
    'y_join_rows': [0.25, 0.75],          # Row positions in section height
    'y_join_cols': [0.1, 0.4, 0.6, 0.9],  # Along chord width
}

# Geometry Construction Parameters (mm)
GEOMETRY_CONFIG = {
    'slice_sample_thickness': 1.0,
    'boolean_box_extra': 200,      # Extra size for boolean operation boxes
    'boolean_box_offset': 100,     # Offset for boolean operation boxes
    'y_split_overlap': 0.01,       # Minimal overlap at Y=0 split for reliable boolean ops
    'cutting_box_extra': 10,       # Extra size for piece cutting boxes
    'cutting_box_offset': 5,       # Offset for piece cutting
}

# Visualization
VISUALIZATION_CONFIG = {
    'explosion_factor': 3,     # mm between pieces (0 = assembled view)
    'transparency': {
        'solid': 30,
        'hollowed': 70,
        'pieces': 20,
    },
    'colors': {
        'port_solid': (0.2, 0.5, 0.8),      # Blue
        'port_z_holes': (0.2, 0.5, 0.8),    # Blue
        'port_aligned': (0.1, 0.6, 0.3),    # Green
        'port_joined': (0.8, 0.3, 0.1),     # Orange
        'port_hollowed': (0.3, 0.3, 0.4),   # Dark grey
        'stock': (0.8, 0.8, 0.9),           # Light steel
    }
}

# File Paths - FIXED to properly expand all paths
PATHS = {
    'boat_folder': os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}"),
}
PATHS['output_folder'] = f"{PATHS['boat_folder']}/output"
PATHS['cut_foil_folder'] = f"{PATHS['output_folder']}/cut_foil"
PATHS['stock_folder'] = f"{PATHS['output_folder']}/stock"
PATHS['cutout_folder'] = f"{PATHS['output_folder']}/cutout"
PATHS['print_folder'] = f"{PATHS['output_folder']}/demo"

# Input Files
INPUT_FILES = {
    'cut_foil': f"{BOAT_NAME}_Cut_Foil.step",
    'stock': f"{BOAT_NAME}_Stock.step",
    'stock_cutout': f"{BOAT_NAME}_Stock_Cutout.step",
}

MACRO_NAME = f"Demo_Model_{BOAT_NAME}"

# ============================================================================
# HOLE OPERATION FUNCTIONS
# ============================================================================

def add_z_cut_alignment_pins(shape, z_cut_position):
    """Add alignment holes at a Z-cut position using FOAM_HOLE_CONFIG."""
    print(f"      Adding foam holes at Z={z_cut_position:.1f}")
    
    # Find chord bounds at this Z
    sample_slice = Part.makeBox(
        1000, 1000, GEOMETRY_CONFIG['slice_sample_thickness'],
        Vector(-500, -500, z_cut_position - GEOMETRY_CONFIG['slice_sample_thickness']/2)
    )
    
    try:
        cross_section = shape.common(sample_slice)
        chord_bbox = cross_section.BoundBox
        
        x_min = chord_bbox.XMin
        x_max = chord_bbox.XMax
        chord_width = x_max - x_min
        y_pos = 0 - FOAM_HOLE_CONFIG['y_offset'] - FOAM_HOLE_CONFIG['diameter']/2
        
        print(f"         Chord: X from {x_min:.1f} to {x_max:.1f} (width={chord_width:.1f})")
        
    except Exception as e:
        print(f"         ❌ FAILED to find chord at Z={z_cut_position:.1f}: {e}")
        return None
    
    # Calculate hole positions using configuration
    result_shape = shape
    successful_holes = 0
    total_holes = len(HOLE_POSITIONS['z_cut'])
    
    for i, fraction in enumerate(HOLE_POSITIONS['z_cut']):
        x_pos = x_min + (chord_width * fraction)
        pos = Vector(x_pos, y_pos, z_cut_position)
        
        hole_cylinder = Part.makeCylinder(
            FOAM_HOLE_CONFIG['diameter'] / 2, 
            FOAM_HOLE_CONFIG['depth'],
            pos - Vector(0, 0, FOAM_HOLE_CONFIG['depth']/2),
            Vector(0, 0, 1)
        )
        
        try:
            result_shape = result_shape.cut(hole_cylinder)
            successful_holes += 1
        except Exception as e:
            print(f"         ❌ FAILED to add foam hole {i+1}/{total_holes} at {fraction*100:.0f}%: {e}")
            return None
    
    if successful_holes != total_holes:
        print(f"         ❌ Only added {successful_holes}/{total_holes} foam holes - ABORTING")
        return None
        
    print(f"         ✅ Added {successful_holes}/{total_holes} foam holes ({FOAM_HOLE_CONFIG['diameter']}mm dia)")
    return result_shape


def add_x_cut_alignment_pins(shape, x_cut_position, z_start, z_end):
    """Add alignment holes at an X-cut position using HOLE_CONFIG."""
    print(f"      Adding X-cut alignment holes at X={x_cut_position:.1f}")
    
    slice_height = z_end - z_start
    y_pos = 0 - HOLE_CONFIG['y_offset'] - HOLE_CONFIG['diameter']/2
    
    print(f"         Slice from Z={z_start:.1f} to {z_end:.1f} (height={slice_height:.1f})")
    print(f"         Y position for holes: {y_pos:.1f}")
    
    result_shape = shape
    successful_holes = 0
    total_holes = len(HOLE_POSITIONS['x_cut'])
    
    for i, fraction in enumerate(HOLE_POSITIONS['x_cut']):
        z_pos = z_start + (slice_height * fraction)
        pos = Vector(x_cut_position, y_pos, z_pos)
        
        hole_cylinder = Part.makeCylinder(
            HOLE_CONFIG['diameter'] / 2, 
            HOLE_CONFIG['depth'],
            pos - Vector(HOLE_CONFIG['depth']/2, 0, 0),
            Vector(1, 0, 0)
        )
        
        try:
            result_shape = result_shape.cut(hole_cylinder)
            successful_holes += 1
        except Exception as e:
            print(f"         ❌ FAILED to add X-cut hole {i+1}/{total_holes} at {fraction*100:.0f}%: {e}")
            return None
    
    if successful_holes != total_holes:
        print(f"         ❌ Only added {successful_holes}/{total_holes} X-cut holes - ABORTING")
        return None
        
    print(f"         ✅ Added {successful_holes}/{total_holes} X-cut holes ({HOLE_CONFIG['diameter']}mm dia)")
    return result_shape


def add_y_half_joining_holes(shape, z_start, z_end, section_name):
    """Add horizontal holes in Y-direction for joining port and starboard halves using HOLE_CONFIG."""
    section_height = z_end - z_start
    print(f"      Adding Y-direction joining holes to {section_name}")
    print(f"         Section Z: {z_start:.1f} to {z_end:.1f} (height={section_height:.1f})")
    
    result_shape = shape
    total_holes = 0
    expected_holes = len(HOLE_POSITIONS['y_join_rows']) * len(HOLE_POSITIONS['y_join_cols'])
    
    for row_frac in HOLE_POSITIONS['y_join_rows']:
        z_position = z_start + (section_height * row_frac)
        print(f"         Row at Z={z_position:.1f} ({row_frac*100:.0f}% of section height)")
        
        sample_slice = Part.makeBox(
            1000, 1000, GEOMETRY_CONFIG['slice_sample_thickness'],
            Vector(-500, -500, z_position - GEOMETRY_CONFIG['slice_sample_thickness']/2)
        )
        
        try:
            cross_section = shape.common(sample_slice)
            chord_bbox = cross_section.BoundBox
            
            x_min = chord_bbox.XMin
            x_max = chord_bbox.XMax
            chord_width = x_max - x_min
            
            print(f"            Chord: X from {x_min:.1f} to {x_max:.1f} (width={chord_width:.1f})")
            
        except Exception as e:
            print(f"            ❌ FAILED to find chord at Z={z_position:.1f}: {e}")
            return None
        
        for x_frac in HOLE_POSITIONS['y_join_cols']:
            x_pos = x_min + (chord_width * x_frac)
            
            hole_cylinder = Part.makeCylinder(
                HOLE_CONFIG['diameter'] / 2, 
                HOLE_CONFIG['depth'],
                Vector(x_pos, -HOLE_CONFIG['depth']/2, z_position),
                Vector(0, -1, 0)
            )
            
            try:
                result_shape = result_shape.cut(hole_cylinder)
                total_holes += 1
            except Exception as e:
                print(f"            ❌ FAILED to add hole at X={x_pos:.1f}: {e}")
                return None
    
    if total_holes != expected_holes:
        print(f"         ❌ Only added {total_holes}/{expected_holes} joining holes - ABORTING")
        return None
        
    print(f"         ✅ Added {total_holes}/{expected_holes} joining holes ({HOLE_CONFIG['diameter']}mm dia)")
    return result_shape


def ensure_solid(shape, operation_name="operations"):
    """Ensure a shape is a solid, converting from compound if necessary."""
    print(f"\n🔧 Converting shape back to solid after {operation_name}...")
    
    if shape.ShapeType == "Solid":
        print(f"   ✅ Shape is already a solid")
        return shape
    
    if shape.ShapeType == "Compound":
        print(f"   Shape is compound, attempting to fuse into solid...")
        try:
            # Try to fuse the compound into a single solid
            fused_shape = shape.fuse([])  # Fuse with empty list to consolidate
            if fused_shape.ShapeType == "Solid":
                print(f"   ✅ Successfully converted to solid")
                return fused_shape
            else:
                print(f"   ❌ FAILED: Still {fused_shape.ShapeType} after fuse attempt")
                return None
        except Exception as e:
            print(f"   ❌ FAILED: Fuse operation failed: {e}")
            return None
    
    print(f"   ❌ FAILED: Shape is {shape.ShapeType}, cannot convert to solid")
    return None

# ============================================================================
# GLOBAL STATE
# ============================================================================

doc = None
cut_foil_obj = None
stock_obj = None
stock_cutout_obj = None
port_half = None
port_half_obj = None
port_plan = None
pieces = []
piece_objects = []

# ============================================================================
# MAIN WORKFLOW FUNCTIONS
# ============================================================================

def update_view():
    """Update document and view to show current state"""
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()


def initialize_and_setup():
    """Initialize document and validate STEP files"""
    global doc
    
    print(f"\n🎭 Demo Model Generator v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

    # Validate STEP files before import
    print(f"\n🔍 Validating STEP files...")
    
    files_to_validate = [
        (f"{PATHS['cut_foil_folder']}/{INPUT_FILES['cut_foil']}", "Cut Foil"),
        (f"{PATHS['stock_folder']}/{INPUT_FILES['stock']}", "Stock"),
        (f"{PATHS['cutout_folder']}/{INPUT_FILES['stock_cutout']}", "Stock Cutout"),
    ]
    
    for filepath, name in files_to_validate:
        validation = validate_step_file(filepath, verbose=False)
        if not validation['valid']:
            print(f"❌ Invalid {name} STEP file: {filepath}")
            print(f"   File exists: {validation['exists']}")
            print(f"   File size: {validation['size']} bytes")
            return False
        print(f"   ✅ {name} STEP file valid")
    
    return True


def import_step_files():
    """Import all STEP files"""
    global cut_foil_obj, stock_obj, stock_cutout_obj
    
    try:
        print(f"\n📥 Importing STEP files...")
        
        # Import cut foil
        cut_foil_path = f"{PATHS['cut_foil_folder']}/{INPUT_FILES['cut_foil']}"
        _, cut_foil_objects = load_step(cut_foil_path, MACRO_NAME, verbose=True)
        if not cut_foil_objects:
            raise StepFileError("No objects imported from cut foil file")
        cut_foil_obj = cut_foil_objects[0]
        cut_foil_obj.Label = f"{BOAT_NAME}_Cut_Foil"
        
        # Import stock
        stock_path = f"{PATHS['stock_folder']}/{INPUT_FILES['stock']}"
        _, stock_objects = load_step(stock_path, MACRO_NAME, verbose=True)
        if not stock_objects:
            raise StepFileError("No objects imported from stock file")
        stock_obj = stock_objects[0]
        stock_obj.Label = f"{BOAT_NAME}_Stock"
        
        # Import stock cutout
        stock_cutout_path = f"{PATHS['cutout_folder']}/{INPUT_FILES['stock_cutout']}"
        _, stock_cutout_objects = load_step(stock_cutout_path, MACRO_NAME, verbose=True)
        if not stock_cutout_objects:
            raise StepFileError("No objects imported from stock cutout file")
        stock_cutout_obj = stock_cutout_objects[0]
        stock_cutout_obj.Label = f"{BOAT_NAME}_Stock_Cutout"
        
        update_view()
        return True
        
    except StepFileError as e:
        print(f"❌ Failed to import STEP files: {e}")
        return False


def position_stock_components():
    """Position all stock components"""
    final_positions = position_all_stock_components(
        stock_obj, 
        stock_cutout_obj,
        STOCK_CONFIG['post_center_x'], 
        STOCK_CONFIG['post_top_z'], 
        STOCK_CONFIG['post_diameter'], 
        STOCK_CONFIG['post_diameter_delta']
    )
    
    # Make objects visible
    cut_foil_obj.ViewObject.Visibility = True
    stock_obj.ViewObject.Visibility = True
    stock_cutout_obj.ViewObject.Visibility = True
    
    print(f"\n🔄 Recomputing to ensure positioning is complete...")
    update_view()
    print(f"   ✅ Recompute done, ready for split operation")
    
    return True


def split_solid_foil_at_y_zero():
    """Split solid foil at Y=0 for port/starboard (BEFORE boolean cut)"""
    global port_half, port_half_obj
    
    print(f"\n✂️ Splitting solid foil at Y=0...")
    
    try:
        bbox = cut_foil_obj.Shape.BoundBox
        print(f"   Solid foil bounds:")
        print(f"      X: {bbox.XMin:.1f} to {bbox.XMax:.1f}")
        print(f"      Y: {bbox.YMin:.1f} to {bbox.YMax:.1f}")
        print(f"      Z: {bbox.ZMin:.1f} to {bbox.ZMax:.1f}")
        
        # Create box for negative Y side (port)
        extra = GEOMETRY_CONFIG['boolean_box_extra']
        offset = GEOMETRY_CONFIG['boolean_box_offset']
        overlap = GEOMETRY_CONFIG['y_split_overlap']
        
        box_negative_y = Part.makeBox(
            bbox.XLength + extra,
            abs(bbox.YMin) + offset + overlap,
            bbox.ZLength + extra,
            Vector(bbox.XMin - offset, bbox.YMin - offset, bbox.ZMin - offset)
        )
        
        # Extract port half only from SOLID foil
        print(f"   Creating port half from solid foil (will be mirrored for starboard)...")
        port_half = cut_foil_obj.Shape.common(box_negative_y)
        
        # Verify the split worked
        if port_half.isNull() or len(port_half.Faces) == 0:
            print(f"   ❌ FAILED: Port half is empty!")
            return False
        
        # Create FreeCAD object for port half visualization
        port_half_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_Port_Half_Solid")
        port_half_obj.Shape = port_half
        port_half_obj.ViewObject.Visibility = True
        port_half_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['port_solid']
        port_half_obj.ViewObject.Transparency = VISUALIZATION_CONFIG['transparency']['solid']
        port_half_obj.Label = f"{BOAT_NAME}_Port_Half_Solid"
        
        # Hide the original foil and stock for cleaner view
        cut_foil_obj.ViewObject.Visibility = False
        stock_obj.ViewObject.Visibility = False
        stock_cutout_obj.ViewObject.Visibility = False
        
        print(f"   ✅ Solid port half created with {len(port_half.Faces)} faces")
        print(f"   ℹ️ This solid half will have holes added, then be hollowed")
        
        update_view()
        return True
        
    except Exception as e:
        print(f"   ❌ FAILED: Processing failed: {e}")
        return False


def create_port_cutting_plan():
    """Create cutting plan for 3D printing"""
    global port_plan
    
    print(f"\n🗺️ Creating cutting plan for 3D printing...")
    print(f"🖨️ Printer: Bambu Labs HD2 (Build volume: {PRINTER_CONFIG['build_x']}x{PRINTER_CONFIG['build_y']}x{PRINTER_CONFIG['build_z']}mm)")
    
    try:
        port_plan = create_cutting_plan(port_half, "Port Half", PRINTER_CONFIG['max_print_size'])
        return True
    except Exception as e:
        print(f"   ❌ FAILED to create cutting plan: {e}")
        return False


def add_z_alignment_to_port():
    """Add Z-cut foam holes to solid port half"""
    global port_half
    
    positions_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['z_cut']])
    print(f"\n🔩 Adding Z-cut foam holes to solid port half...")
    print(f"   Adding {len(HOLE_POSITIONS['z_cut'])} foam holes ({FOAM_HOLE_CONFIG['diameter']}mm) at each Z-cut position")
    print(f"   Holes at {positions_str} of chord width")
    
    if port_plan['z_slices'] > 1:
        for i in range(1, port_plan['z_slices']):
            z_cut_position = port_plan['bbox'].ZMin + (i * port_plan['z_slice_height'])
            modified_shape = add_z_cut_alignment_pins(port_half, z_cut_position)
            if modified_shape is None:
                print(f"   ❌ FAILED to add Z-cut foam holes")
                return False
            port_half = modified_shape
    
    port_half_obj.Shape = port_half
    port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Z_holes"
    
    update_view()
    print(f"   🔄 View updated to show Z-cut foam holes in solid")
    
    return True


def add_x_alignment_to_port():
    """Add X-cut alignment pins to solid port half"""
    global port_half
    
    positions_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['x_cut']])
    print(f"\n🔧 Adding X-cut alignment holes to solid port half...")
    print(f"   Adding {len(HOLE_POSITIONS['x_cut'])} alignment holes ({HOLE_CONFIG['diameter']}mm) at each X-cut position")
    print(f"   Holes at {positions_str} of slice height")
    
    for slice_info in port_plan['slice_plans']:
        if slice_info['needs_x_split']:
            x_center = slice_info['x_center']
            z_start = slice_info['z_start']
            z_end = slice_info['z_end']
            modified_shape = add_x_cut_alignment_pins(port_half, x_center, z_start, z_end)
            if modified_shape is None:
                print(f"   ❌ FAILED to add X-cut alignment pins")
                return False
            port_half = modified_shape
    
    port_half_obj.Shape = port_half
    port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Alignment_Holes"
    port_half_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['port_aligned']
    
    update_view()
    print(f"   🔄 View updated to show all alignment holes in solid")
    print(f"   ✅ Solid port half ready with all alignment features")
    
    return True


def add_y_joining_to_port():
    """Add Y-direction holes for joining port and starboard halves"""
    global port_half
    
    rows = len(HOLE_POSITIONS['y_join_rows'])
    cols = len(HOLE_POSITIONS['y_join_cols'])
    row_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['y_join_rows']])
    col_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['y_join_cols']])
    
    print(f"\n🔩 Adding Y-direction holes for joining port and starboard halves...")
    print(f"   Adding {rows} rows per section at {row_str} of height")
    print(f"   Adding {cols} holes ({HOLE_CONFIG['diameter']}mm) per row at {col_str} of chord")
    print(f"   Holes oriented horizontally (Y-axis) for joining halves")
    
    for i, slice_info in enumerate(port_plan['slice_plans']):
        section_num = i + 1
        z_start = slice_info['z_start']
        z_end = slice_info['z_end']
        section_name = f"Section {section_num}"
        
        print(f"\n   Processing {section_name} (Z: {z_start:.0f} to {z_end:.0f}mm)")
        
        modified_shape = add_y_half_joining_holes(port_half, z_start, z_end, section_name)
        if modified_shape is None:
            print(f"   ❌ FAILED to add Y-joining holes")
            return False
        port_half = modified_shape
    
    # Ensure solid after all hole operations
    solid_shape = ensure_solid(port_half, "hole operations")
    if solid_shape is None:
        print(f"   ❌ FAILED to ensure solid shape")
        return False
    port_half = solid_shape
    
    port_half_obj.Shape = port_half
    port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Joining_Holes"
    port_half_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['port_joined']
    
    update_view()
    print(f"   🔄 View updated to show joining holes in solid")
    print(f"   ✅ Solid port half complete with alignment and joining features")
    
    return True


def pre_boolean_checks():
    """Perform pre-Boolean operation validation checks"""
    print(f"\n🔍 Performing pre-Boolean operation checks...")
    print(f"   Checking port half with holes vs stock cutout")
    
    # Check 1: Validate shapes
    if not port_half.isValid():
        print(f"❌ Port half shape is not valid!")
        return False
    
    if not stock_cutout_obj.Shape.isValid():
        print(f"❌ Stock cutout shape is not valid!")
        return False
    
    print(f"   ✅ Both shapes are valid")
    
    # Check 2: Ensure shapes are solids
    if not port_half.ShapeType == "Solid":
        print(f"❌ Port half is not a solid! (Type: {port_half.ShapeType})")
        return False
    
    if not stock_cutout_obj.Shape.ShapeType == "Solid":
        print(f"❌ Stock cutout is not a solid! (Type: {stock_cutout_obj.Shape.ShapeType})")
        return False
    
    print(f"   ✅ Both shapes are solids")
    
    # Check 3: Check for intersection
    try:
        common_volume = port_half.common(stock_cutout_obj.Shape)
        if common_volume.Volume < 0.001:
            print(f"❌ No meaningful intersection between shapes!")
            print(f"   Common volume: {common_volume.Volume:.6f} mm³")
            return False
    except Exception as e:
        print(f"❌ Failed to compute intersection: {e}")
        return False
    
    print(f"   ✅ Shapes intersect properly (common volume: {common_volume.Volume:.2f} mm³)")
    
    # Check 4: Check bounding box overlap
    port_bbox = port_half.BoundBox
    cutout_bbox = stock_cutout_obj.Shape.BoundBox
    
    if not (port_bbox.intersect(cutout_bbox)):
        print(f"❌ Bounding boxes do not intersect!")
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


def boolean_cut_operation():
    """Perform boolean cut to create hollowed port half"""
    global port_half
    
    print(f"\n🔧 Creating cavity with boolean cut on port half...")
    print(f"   ⏳ This may take a moment for complex geometry...")
    try:
        original_faces = len(port_half.Faces)
        hollowed_port_half = port_half.cut(stock_cutout_obj.Shape)
        
        # Verify the cut worked
        if hollowed_port_half.isNull() or len(hollowed_port_half.Faces) <= original_faces:
            print(f"   ❌ FAILED: Boolean cut produced invalid result")
            return False
        
        port_half = hollowed_port_half
        
        port_half_obj.Shape = port_half
        port_half_obj.Label = f"{BOAT_NAME}_Port_Half_Hollowed"
        port_half_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['port_hollowed']
        port_half_obj.ViewObject.Transparency = VISUALIZATION_CONFIG['transparency']['hollowed']
        
        stock_obj.ViewObject.Visibility = True
        stock_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['stock']
        
        print(f"   ✅ Cavity created successfully in port half")
        print(f"   Original port half faces: {original_faces}")
        print(f"   Hollowed port half faces: {len(port_half.Faces)}")
        
        update_view()
        return True
        
    except Exception as e:
        print(f"   ❌ FAILED: Boolean cut failed: {e}")
        return False


def cut_pieces():
    """Cut hollowed port half into pieces according to plan"""
    global pieces, piece_objects
    
    print(f"\n📐 Cutting pieces...")
    print(f"   Alignment and joining holes will be split automatically by cuts")
    
    port_half_obj.ViewObject.Visibility = False
    stock_obj.ViewObject.Visibility = False
    
    pieces = []
    piece_objects = []
    
    extra = GEOMETRY_CONFIG['boolean_box_extra']
    offset = GEOMETRY_CONFIG['boolean_box_offset']
    cut_extra = GEOMETRY_CONFIG['cutting_box_extra']
    cut_offset = GEOMETRY_CONFIG['cutting_box_offset']
    
    # Cut into Z slices
    for i, slice_info in enumerate(port_plan['slice_plans']):
        slice_num = i + 1
        z_start = slice_info['z_start']
        z_end = slice_info['z_end']
        
        print(f"\n   Processing slice {slice_num} (Z: {z_start:.0f} to {z_end:.0f}mm)")
        
        slice_bbox = port_half.BoundBox
        
        # Box to isolate this Z slice
        slice_box = Part.makeBox(
            slice_bbox.XLength + extra,
            slice_bbox.YLength + extra,
            z_end - z_start,
            Vector(slice_bbox.XMin - offset, slice_bbox.YMin - offset, z_start)
        )
        
        try:
            slice_shape = port_half.common(slice_box)
            
            if slice_shape.isNull() or len(slice_shape.Faces) == 0:
                print(f"      ❌ FAILED: Slice {slice_num} is empty")
                return False
            
            if slice_info['needs_x_split']:
                x_center = slice_info['x_center']
                print(f"      Splitting at X={x_center:.0f}mm")
                
                # Create boxes for left (A) and right (B) pieces
                left_box = Part.makeBox(
                    x_center - slice_bbox.XMin + cut_extra,
                    slice_bbox.YLength + extra,
                    z_end - z_start + cut_extra,
                    Vector(slice_bbox.XMin - cut_extra, slice_bbox.YMin - offset, z_start - cut_offset)
                )
                
                right_box = Part.makeBox(
                    slice_bbox.XMax - x_center + cut_extra,
                    slice_bbox.YLength + extra,
                    z_end - z_start + cut_extra,
                    Vector(x_center, slice_bbox.YMin - offset, z_start - cut_offset)
                )
                
                piece_a = slice_shape.common(left_box)
                piece_b = slice_shape.common(right_box)
                
                if piece_a.isNull() or piece_b.isNull():
                    print(f"      ❌ FAILED: X-split produced invalid pieces")
                    return False
                
                name_a = f"{slice_num}A"
                name_b = f"{slice_num}B"
                
                pieces.append((name_a, piece_a))
                pieces.append((name_b, piece_b))
                
                print(f"      ✅ Created pieces {name_a} and {name_b}")
                
                # Create FreeCAD objects
                for name, piece, x_offset in [(name_a, piece_a, -1), (name_b, piece_b, 1)]:
                    obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name}")
                    obj.Shape = piece
                    obj.ViewObject.ShapeColor = (0.2 + i*0.15, 0.4, 0.6)
                    obj.ViewObject.Transparency = VISUALIZATION_CONFIG['transparency']['pieces']
                    
                    if VISUALIZATION_CONFIG['explosion_factor'] > 0:
                        obj.Placement.Base.x += x_offset * VISUALIZATION_CONFIG['explosion_factor']
                        obj.Placement.Base.z += i * VISUALIZATION_CONFIG['explosion_factor']
                    
                    piece_objects.append(obj)
                
            else:
                name = f"{slice_num}A"
                pieces.append((name, slice_shape))
                
                print(f"      ✅ Created piece {name} (no X-split needed)")
                
                obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name}")
                obj.Shape = slice_shape
                obj.ViewObject.ShapeColor = (0.2 + i*0.15, 0.4, 0.6)
                obj.ViewObject.Transparency = VISUALIZATION_CONFIG['transparency']['pieces']
                
                if VISUALIZATION_CONFIG['explosion_factor'] > 0:
                    obj.Placement.Base.z += i * VISUALIZATION_CONFIG['explosion_factor']
                
                piece_objects.append(obj)
                
        except Exception as e:
            print(f"      ❌ FAILED to create slice: {e}")
            return False
    
    if len(pieces) == 0:
        print(f"   ❌ FAILED: No pieces were created")
        return False
    
    update_view()
    return True


def export_pieces():
    """Export individual pieces to STEP files"""
    print(f"\n💾 Exporting individual pieces with alignment and joining features...")
    pieces_folder = f"{PATHS['print_folder']}/pieces_for_mirroring"
    os.makedirs(pieces_folder, exist_ok=True)
    
    exported_count = 0
    
    for piece_name, piece_shape in pieces:
        try:
            temp_obj = doc.addObject("Part::Feature", f"temp_{piece_name}")
            temp_obj.Shape = piece_shape
            
            piece_path = f"{pieces_folder}/{BOAT_NAME}_{piece_name}.step"
            save_step(temp_obj, piece_path, verbose=False)
            
            doc.removeObject(temp_obj.Name)
            
            print(f"   ✅ Exported: {piece_name}")
            exported_count += 1
            
        except Exception as e:
            print(f"   ❌ FAILED to export {piece_name}: {e}")
            # Clean up temp object if it exists
            if f"temp_{piece_name}" in [obj.Name for obj in doc.Objects]:
                doc.removeObject(f"temp_{piece_name}")
            return False
    
    if exported_count != len(pieces):
        print(f"   ❌ FAILED: Only exported {exported_count}/{len(pieces)} pieces")
        return False
    
    print(f"\n   📦 Successfully exported {exported_count}/{len(pieces)} pieces")
    return True


def final_view_and_summary():
    """Update view and print final summary"""
    update_view()
    
    # Format position arrays for display
    z_pos_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['z_cut']])
    x_pos_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['x_cut']])
    y_row_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['y_join_rows']])
    y_col_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['y_join_cols']])
    
    print(f"\n📋 FINAL SUMMARY:")
    print(f"   🔄 MIRRORING WORKFLOW:")
    print(f"      1. Import pieces into Bambu Studio")
    print(f"      2. Print one set as-is (port half)")
    print(f"      3. Mirror and print again (creates starboard half)")
    print(f"      4. Join pieces using {HOLE_CONFIG['diameter']}mm dowels (X and Y holes)")
    print(f"      5. Join port and starboard halves using Y-direction joining holes")
    print(f"   Alignment features:")
    print(f"      • Z-cuts: {len(HOLE_POSITIONS['z_cut'])} holes at {z_pos_str} of chord")
    print(f"        - {FOAM_HOLE_CONFIG['diameter']}mm diameter foam injection holes")
    print(f"        - {FOAM_HOLE_CONFIG['depth']}mm depth")
    print(f"      • X-cuts: {len(HOLE_POSITIONS['x_cut'])} holes at {x_pos_str} of slice height")
    print(f"        - {HOLE_CONFIG['diameter']}mm diameter alignment holes")
    print(f"        - {HOLE_CONFIG['depth']}mm depth")
    print(f"      • Z-holes: vertical (perpendicular to Z-cut plane)")
    print(f"      • X-holes: horizontal (perpendicular to X-cut plane)")
    print(f"   Half-joining features:")
    total_y_holes = len(HOLE_POSITIONS['y_join_rows']) * len(HOLE_POSITIONS['y_join_cols'])
    print(f"      • Y-direction holes: {total_y_holes} holes per section ({len(HOLE_POSITIONS['y_join_rows'])} rows × {len(HOLE_POSITIONS['y_join_cols'])} holes)")
    print(f"      • Rows at {y_row_str} of section height")
    print(f"      • Holes at {y_col_str} of chord width")
    print(f"      • {HOLE_CONFIG['diameter']}mm diameter, {HOLE_CONFIG['depth']}mm depth")
    print(f"      • Horizontal holes for joining port and starboard halves")
    print(f"   Processing approach:")
    print(f"      • Split solid foil first (more reliable)")
    print(f"      • Add all holes to solid geometry (cleaner cuts)")
    print(f"      • Boolean cut last (on port half only)")
    print(f"   Pieces created (to be mirrored):")
    piece_list = [name for name, _ in pieces]
    piece_list.sort()
    for piece_name in piece_list:
        print(f"      • {piece_name}")
    print(f"   📦 UNIQUE PIECES: {len(pieces)}")
    print(f"   📦 TOTAL AFTER MIRRORING: {len(pieces) * 2}")
    
    pieces_folder = f"{PATHS['print_folder']}/pieces_for_mirroring"
    print(f"\n✅ Complete! Pieces ready for mirroring in slicer.")
    print(f"📁 Files saved to: {pieces_folder}")
    
    return True


def run():
    """Execute all operations in sequence - fail fast on any error"""
    
    print("Imports the Cut Foil and Stock and prepares for demo print")
    
    operations = [
        ("Initializing and validating", initialize_and_setup),
        ("Importing STEP files", import_step_files),
        ("Positioning stock components", position_stock_components),
        ("Splitting solid foil at Y=0", split_solid_foil_at_y_zero),
        ("Creating cutting plan", create_port_cutting_plan),
        ("Adding Z-cut foam holes", add_z_alignment_to_port),
        ("Adding X-cut alignment pins", add_x_alignment_to_port),
        ("Adding Y-joining holes", add_y_joining_to_port),
        ("Performing pre-Boolean checks", pre_boolean_checks),
        ("Performing Boolean cut", boolean_cut_operation),
        ("Cutting pieces", cut_pieces),
        ("Exporting pieces", export_pieces),
    ]
    
    for step_name, operation in operations:
        if not operation():
            print(f"\n💥 CRITICAL FAILURE: {step_name} failed")
            print(f"   Aborting demo model generation")
            return False
    
    final_view_and_summary()
    return True


# Run the script
if __name__ == "__main__":
    success = run()
    if not success:
        print("\n❌ Demo model generation FAILED")
        sys.exit(1)