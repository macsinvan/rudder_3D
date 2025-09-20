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
VERSION = "2.5.6"  # Adaptive hole positioning to prevent breakthrough

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
    'y_offset': 3,          # Distance from Y=0 plane to hole center (used only if adaptive positioning disabled)
    'min_wall_thickness': 2,  # Minimum material thickness on each side of hole
}

# Foam Hole Configuration (mm) - Used for Z holes
FOAM_HOLE_CONFIG = {
    'diameter': 12,         # Foam injection hole diameter
    'depth': 25,            # Hole depth
    'y_offset': 3,          # Distance from Y=0 plane to hole center (used only if adaptive positioning disabled)
    'min_wall_thickness': 2,  # Minimum material thickness on each side of hole
}

# Hole Position Arrays (as fractions of dimension)
HOLE_POSITIONS = {
    'z_cut': [0.35, 0.45, 0.60, 0.80],          # Along chord width
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
    'sample_box_size': 1000,       # Size of sampling boxes for chord detection
    'sample_box_center': 500,      # Center offset for sampling boxes
    'cache_rounding_precision': 2,  # Decimal places for cache key rounding
    'adaptive_positioning': True,  # Use adaptive hole positioning to center in material
}

# Validation Parameters
VALIDATION_CONFIG = {
    'min_intersection_volume': 0.001,  # Minimum volume (mm³) for meaningful intersection
    'high_face_count_warning': 10000,  # Warning threshold for face count
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
# APPLICATION STATE CLASS
# ============================================================================

class DemoModelState:
    """Holds all application state to avoid global variables"""
    def __init__(self):
        self.doc = None
        self.cut_foil_obj = None
        self.stock_obj = None
        self.stock_cutout_obj = None
        self.port_half = None
        self.port_half_obj = None
        self.port_plan = None
        self.pieces = []
        self.piece_objects = []
        self.chord_bounds_cache = {}
    
    def clear_chord_cache(self):
        """Clear the chord bounds cache"""
        self.chord_bounds_cache = {}
        print(f"   Cleared chord bounds cache")

# Create single state instance
state = DemoModelState()

# ============================================================================
# CHORD BOUNDS CACHE
# ============================================================================

def get_chord_bounds_at_z(shape, z_position):
    """Get chord bounds at a Z position, using cache if available."""
    # Round Z position to avoid floating point comparison issues
    z_key = round(z_position, GEOMETRY_CONFIG['cache_rounding_precision'])
    
    if z_key in state.chord_bounds_cache:
        print(f"         Using cached chord bounds for Z={z_position:.1f}")
        return state.chord_bounds_cache[z_key]
    
    print(f"         Computing chord bounds at Z={z_position:.1f}")
    
    box_size = GEOMETRY_CONFIG['sample_box_size']
    box_center = GEOMETRY_CONFIG['sample_box_center']
    
    sample_slice = Part.makeBox(
        box_size, box_size, GEOMETRY_CONFIG['slice_sample_thickness'],
        Vector(-box_center, -box_center, z_position - GEOMETRY_CONFIG['slice_sample_thickness']/2)
    )
    
    try:
        cross_section = shape.common(sample_slice)
        chord_bbox = cross_section.BoundBox
        
        bounds = {
            'x_min': chord_bbox.XMin,
            'x_max': chord_bbox.XMax,
            'width': chord_bbox.XMax - chord_bbox.XMin
        }
        
        # Cache the result
        state.chord_bounds_cache[z_key] = bounds
        
        print(f"         Chord: X from {bounds['x_min']:.1f} to {bounds['x_max']:.1f} (width={bounds['width']:.1f})")
        return bounds
        
    except Exception as e:
        print(f"         ❌ FAILED to find chord at Z={z_position:.1f}: {e}")
        return None

def get_y_bounds_at_position(shape, x_position, z_position):
    """Get Y bounds of material at a specific X,Z position (from Y=0 to outer surface)."""
    print(f"            Sampling Y bounds at X={x_position:.1f}, Z={z_position:.1f}")
    
    # Create a small vertical sample box at the X,Z position
    # Extended in -Z direction to ensure we catch geometry at cut planes
    sample_size = 5.0  # Increased from 1mm to 5mm for better detection
    sample_z_extend = 10.0  # Extend 10mm in -Z direction to avoid cut plane issues
    sample_height = 100.0  # Should cover the full Y extent
    
    # Create sample box that extends from positive Y through 0 to negative Y
    # and extends backward in Z to catch narrower chord
    sample_box = Part.makeBox(
        sample_size,
        sample_height * 2,  # Double height to cover both sides
        sample_size + sample_z_extend,  # Extended in Z
        Vector(x_position - sample_size/2, -sample_height, z_position - sample_z_extend)
    )
    
    try:
        # Find intersection with shape
        intersection = shape.common(sample_box)
        if intersection.isNull() or len(intersection.Faces) == 0:
            print(f"            No material at this position")
            return None
            
        # Get Y bounds of intersection
        bbox = intersection.BoundBox
        y_min = bbox.YMin  # Outer surface (negative for port half)
        y_max = bbox.YMax  # Should be close to 0 (split plane)
        
        # For port half: material extends from Y=0 to negative Y
        # The thickness is the distance from the split plane (0) to the outer surface
        available_thickness = abs(y_min)  # Since y_min is negative for port half
        
        print(f"            Y bounds: {y_min:.1f} to {y_max:.1f} (thickness={available_thickness:.1f}mm)")
        return {
            'y_inner': 0,  # Split plane
            'y_outer': y_min,  # Outer surface (negative for port)
            'thickness': available_thickness
        }
        
    except Exception as e:
        print(f"            ❌ Failed to sample Y bounds: {e}")
        return None
    
# ============================================================================
# GENERIC HOLE OPERATION FUNCTION
# ============================================================================

def create_holes_generic(shape, hole_positions, hole_config, hole_params):
    """
    Generic function to create holes in a shape at specified positions.
    
    Args:
        shape: The shape to add holes to
        hole_positions: List of position data for holes
        hole_config: Configuration dict with 'diameter' and 'depth' keys
        hole_params: Dict with orientation-specific parameters:
            - 'orientation': 'Z', 'X', or 'Y' for hole direction
            - 'description': String describing the hole operation
            - 'hole_type': Type name for error messages (e.g., "foam hole", "X-cut hole")
            - 'use_adaptive': Boolean to enable adaptive positioning (optional, default False)
    
    Returns:
        Modified shape with holes, or None if operation failed
    """
    orientation = hole_params['orientation']
    description = hole_params['description']
    hole_type = hole_params['hole_type']
    use_adaptive = hole_params.get('use_adaptive', False) and GEOMETRY_CONFIG['adaptive_positioning']
    
    print(f"      {description}")
    if use_adaptive:
        print(f"         Using adaptive positioning (centering in material)")
    
    result_shape = shape
    successful_holes = 0
    skipped_holes = 0
    total_holes = len(hole_positions)
    
    for i, pos_data in enumerate(hole_positions):
        position = pos_data['position']
        fraction_desc = pos_data.get('fraction_desc', '')
        
        # Adaptive positioning for Y-oriented holes
        if use_adaptive and (orientation == 'Z' or orientation == 'X' or orientation == 'Y'):
            y_bounds = get_y_bounds_at_position(shape, position.x, position.z)
            
            if y_bounds is None:
                print(f"            Skipping hole {i+1}: No material at position")
                skipped_holes += 1
                continue
            
            # Check if there's enough material for the hole
            min_wall = hole_config.get('min_wall_thickness', 2)
            required_thickness = hole_config['diameter'] + (2 * min_wall)
            
            if y_bounds['thickness'] < required_thickness:
                print(f"            Skipping hole {i+1}: Insufficient material")
                print(f"              Available: {y_bounds['thickness']:.1f}mm, Required: {required_thickness:.1f}mm")
                skipped_holes += 1
                continue
            
            # Center the hole in the available material
            # For port half: y_outer is negative, so center is at -thickness/2
            y_center = y_bounds['y_inner'] - y_bounds['thickness'] / 2
            
            # Update position based on orientation
            if orientation == 'Z':
                position = Vector(position.x, y_center, position.z)
            elif orientation == 'X':
                position = Vector(position.x, y_center, position.z)
            elif orientation == 'Y':
                # For Y holes, we already have the correct X,Z, just need to ensure proper Y positioning
                pass  # Y position is handled in cylinder creation
                
            print(f"            Hole {i+1}: Centered at Y={y_center:.1f} (thickness={y_bounds['thickness']:.1f}mm)")
        
        # Create cylinder based on orientation
        if orientation == 'Z':
            # Vertical hole (along Z-axis)
            cylinder = Part.makeCylinder(
                hole_config['diameter'] / 2,
                hole_config['depth'],
                position - Vector(0, 0, hole_config['depth']/2),
                Vector(0, 0, 1)
            )
        elif orientation == 'X':
            # Horizontal hole along X-axis
            cylinder = Part.makeCylinder(
                hole_config['diameter'] / 2,
                hole_config['depth'],
                position - Vector(hole_config['depth']/2, 0, 0),
                Vector(1, 0, 0)
            )
        elif orientation == 'Y':
            # Horizontal hole along Y-axis
            cylinder = Part.makeCylinder(
                hole_config['diameter'] / 2,
                hole_config['depth'],
                Vector(position.x, -hole_config['depth']/2, position.z),
                Vector(0, -1, 0)
            )
        else:
            print(f"         ❌ Unknown orientation: {orientation}")
            return None
        
        try:
            result_shape = result_shape.cut(cylinder)
            successful_holes += 1
        except Exception as e:
            error_msg = f"         ❌ FAILED to add {hole_type} {i+1}/{total_holes}"
            if fraction_desc:
                error_msg += f" at {fraction_desc}"
            error_msg += f": {e}"
            print(error_msg)
            return None
    
    # Report results
    if skipped_holes > 0:
        print(f"         ⚠️ Skipped {skipped_holes}/{total_holes} holes due to insufficient material")
    
    if successful_holes == 0:
        print(f"         ❌ No holes were created - all positions had insufficient material")
        return None
    
    print(f"         ✅ Added {successful_holes}/{total_holes} {hole_type}s ({hole_config['diameter']}mm dia)")
    return result_shape

# ============================================================================
# HOLE OPERATION FUNCTIONS
# ============================================================================

def add_z_cut_alignment_pins(shape, z_cut_position):
    """Add alignment holes at a Z-cut position using FOAM_HOLE_CONFIG."""
    # Get chord bounds using cache
    bounds = get_chord_bounds_at_z(shape, z_cut_position)
    if bounds is None:
        return None
    
    x_min = bounds['x_min']
    chord_width = bounds['width']
    
    # If adaptive positioning is enabled, use Y=0 as placeholder
    # Otherwise, use the fixed offset
    if GEOMETRY_CONFIG['adaptive_positioning']:
        y_pos = 0  # Will be replaced by adaptive positioning
    else:
        y_pos = 0 - FOAM_HOLE_CONFIG['y_offset'] - FOAM_HOLE_CONFIG['diameter']/2
    
    # Build position data for generic function
    hole_positions = []
    for fraction in HOLE_POSITIONS['z_cut']:
        x_pos = x_min + (chord_width * fraction)
        hole_positions.append({
            'position': Vector(x_pos, y_pos, z_cut_position),
            'fraction_desc': f"{fraction*100:.0f}%"
        })
    
    hole_params = {
        'orientation': 'Z',
        'description': f"Adding foam holes at Z={z_cut_position:.1f}",
        'hole_type': "foam hole",
        'use_adaptive': True  # Enable adaptive positioning
    }
    
    return create_holes_generic(shape, hole_positions, FOAM_HOLE_CONFIG, hole_params)


def add_x_cut_alignment_pins(shape, x_cut_position, z_start, z_end):
    """Add alignment holes at an X-cut position using HOLE_CONFIG."""
    slice_height = z_end - z_start
    
    # If adaptive positioning is enabled, use Y=0 as placeholder
    # Otherwise, use the fixed offset
    if GEOMETRY_CONFIG['adaptive_positioning']:
        y_pos = 0  # Will be replaced by adaptive positioning
    else:
        y_pos = 0 - HOLE_CONFIG['y_offset'] - HOLE_CONFIG['diameter']/2
    
    print(f"         Slice from Z={z_start:.1f} to {z_end:.1f} (height={slice_height:.1f})")
    
    # Build position data for generic function
    hole_positions = []
    for fraction in HOLE_POSITIONS['x_cut']:
        z_pos = z_start + (slice_height * fraction)
        hole_positions.append({
            'position': Vector(x_cut_position, y_pos, z_pos),
            'fraction_desc': f"{fraction*100:.0f}%"
        })
    
    hole_params = {
        'orientation': 'X',
        'description': f"Adding X-cut alignment holes at X={x_cut_position:.1f}",
        'hole_type': "X-cut hole",
        'use_adaptive': True  # Enable adaptive positioning
    }
    
    return create_holes_generic(shape, hole_positions, HOLE_CONFIG, hole_params)


def add_y_half_joining_holes(shape, z_start, z_end, section_name):
    """Add horizontal holes in Y-direction for joining port and starboard halves using HOLE_CONFIG."""
    section_height = z_end - z_start
    print(f"      Adding Y-direction joining holes to {section_name}")
    print(f"         Section Z: {z_start:.1f} to {z_end:.1f} (height={section_height:.1f})")
    
    # Build position data for all holes
    hole_positions = []
    
    for row_frac in HOLE_POSITIONS['y_join_rows']:
        z_position = z_start + (section_height * row_frac)
        print(f"         Row at Z={z_position:.1f} ({row_frac*100:.0f}% of section height)")
        
        # Get chord bounds using cache
        bounds = get_chord_bounds_at_z(shape, z_position)
        if bounds is None:
            return None
        
        x_min = bounds['x_min']
        chord_width = bounds['width']
        
        for x_frac in HOLE_POSITIONS['y_join_cols']:
            x_pos = x_min + (chord_width * x_frac)
            hole_positions.append({
                'position': Vector(x_pos, 0, z_position),  # Y position handled by cylinder creation
                'fraction_desc': None  # Not needed for Y holes
            })
    
    hole_params = {
        'orientation': 'Y',
        'description': "",  # Already printed above
        'hole_type': "joining hole",
        'use_adaptive': True  # Enable adaptive positioning
    }
    
    return create_holes_generic(shape, hole_positions, HOLE_CONFIG, hole_params)


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
# MAIN WORKFLOW FUNCTIONS
# ============================================================================

def update_view():
    """Update document and view to show current state"""
    state.doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()


def initialize_and_setup():
    """Initialize document and validate STEP files"""
    
    print(f"\n🎭 Demo Model Generator v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    state.doc = App.newDocument(MACRO_NAME)
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
    
    try:
        print(f"\n📥 Importing STEP files...")
        
        # Import cut foil
        cut_foil_path = f"{PATHS['cut_foil_folder']}/{INPUT_FILES['cut_foil']}"
        _, cut_foil_objects = load_step(cut_foil_path, MACRO_NAME, verbose=True)
        if not cut_foil_objects:
            raise StepFileError("No objects imported from cut foil file")
        state.cut_foil_obj = cut_foil_objects[0]
        state.cut_foil_obj.Label = f"{BOAT_NAME}_Cut_Foil"
        
        # Import stock
        stock_path = f"{PATHS['stock_folder']}/{INPUT_FILES['stock']}"
        _, stock_objects = load_step(stock_path, MACRO_NAME, verbose=True)
        if not stock_objects:
            raise StepFileError("No objects imported from stock file")
        state.stock_obj = stock_objects[0]
        state.stock_obj.Label = f"{BOAT_NAME}_Stock"
        
        # Import stock cutout
        stock_cutout_path = f"{PATHS['cutout_folder']}/{INPUT_FILES['stock_cutout']}"
        _, stock_cutout_objects = load_step(stock_cutout_path, MACRO_NAME, verbose=True)
        if not stock_cutout_objects:
            raise StepFileError("No objects imported from stock cutout file")
        state.stock_cutout_obj = stock_cutout_objects[0]
        state.stock_cutout_obj.Label = f"{BOAT_NAME}_Stock_Cutout"
        
        update_view()
        return True
        
    except StepFileError as e:
        print(f"❌ Failed to import STEP files: {e}")
        return False


def position_stock_components():
    """Position all stock components"""
    final_positions = position_all_stock_components(
        state.stock_obj, 
        state.stock_cutout_obj,
        STOCK_CONFIG['post_center_x'], 
        STOCK_CONFIG['post_top_z'], 
        STOCK_CONFIG['post_diameter'], 
        STOCK_CONFIG['post_diameter_delta']
    )
    
    # Make objects visible
    state.cut_foil_obj.ViewObject.Visibility = True
    state.stock_obj.ViewObject.Visibility = True
    state.stock_cutout_obj.ViewObject.Visibility = True
    
    print(f"\n🔄 Recomputing to ensure positioning is complete...")
    update_view()
    print(f"   ✅ Recompute done, ready for split operation")
    
    return True


def split_solid_foil_at_y_zero():
    """Split solid foil at Y=0 for port/starboard (BEFORE boolean cut)"""
    
    print(f"\n✂️ Splitting solid foil at Y=0...")
    
    try:
        bbox = state.cut_foil_obj.Shape.BoundBox
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
        state.port_half = state.cut_foil_obj.Shape.common(box_negative_y)
        
        # Verify the split worked
        if state.port_half.isNull() or len(state.port_half.Faces) == 0:
            print(f"   ❌ FAILED: Port half is empty!")
            return False
        
        # Create FreeCAD object for port half visualization
        state.port_half_obj = state.doc.addObject("Part::Feature", f"{BOAT_NAME}_Port_Half_Solid")
        state.port_half_obj.Shape = state.port_half
        state.port_half_obj.ViewObject.Visibility = True
        state.port_half_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['port_solid']
        state.port_half_obj.ViewObject.Transparency = VISUALIZATION_CONFIG['transparency']['solid']
        state.port_half_obj.Label = f"{BOAT_NAME}_Port_Half_Solid"
        
        # Hide the original foil and stock for cleaner view
        state.cut_foil_obj.ViewObject.Visibility = False
        state.stock_obj.ViewObject.Visibility = False
        state.stock_cutout_obj.ViewObject.Visibility = False
        
        print(f"   ✅ Solid port half created with {len(state.port_half.Faces)} faces")
        print(f"   ℹ️ This solid half will have holes added, then be hollowed")
        
        update_view()
        return True
        
    except Exception as e:
        print(f"   ❌ FAILED: Processing failed: {e}")
        return False


def create_port_cutting_plan():
    """Create cutting plan for 3D printing"""
    
    print(f"\n🗺️ Creating cutting plan for 3D printing...")
    print(f"🖨️ Printer: Bambu Labs HD2 (Build volume: {PRINTER_CONFIG['build_x']}x{PRINTER_CONFIG['build_y']}x{PRINTER_CONFIG['build_z']}mm)")
    
    try:
        state.port_plan = create_cutting_plan(state.port_half, "Port Half", PRINTER_CONFIG['max_print_size'])
        return True
    except Exception as e:
        print(f"   ❌ FAILED to create cutting plan: {e}")
        return False


def add_z_alignment_to_port():
    """Add Z-cut foam holes to solid port half"""
    
    # Clear cache before starting hole operations
    state.clear_chord_cache()
    
    positions_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['z_cut']])
    print(f"\n🔩 Adding Z-cut foam holes to solid port half...")
    print(f"   Adding {len(HOLE_POSITIONS['z_cut'])} foam holes ({FOAM_HOLE_CONFIG['diameter']}mm) at each Z-cut position")
    print(f"   Holes at {positions_str} of chord width")
    if GEOMETRY_CONFIG['adaptive_positioning']:
        print(f"   Using adaptive positioning with {FOAM_HOLE_CONFIG['min_wall_thickness']}mm minimum wall thickness")
    
    if state.port_plan['z_slices'] > 1:
        for i in range(1, state.port_plan['z_slices']):
            z_cut_position = state.port_plan['bbox'].ZMin + (i * state.port_plan['z_slice_height'])
            modified_shape = add_z_cut_alignment_pins(state.port_half, z_cut_position)
            if modified_shape is None:
                print(f"   ❌ FAILED to add Z-cut foam holes")
                return False
            state.port_half = modified_shape
    
    state.port_half_obj.Shape = state.port_half
    state.port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Z_holes"
    
    update_view()
    print(f"   🔄 View updated to show Z-cut foam holes in solid")
    
    return True


def add_x_alignment_to_port():
    """Add X-cut alignment pins to solid port half"""
    
    positions_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['x_cut']])
    print(f"\n🔧 Adding X-cut alignment holes to solid port half...")
    print(f"   Adding {len(HOLE_POSITIONS['x_cut'])} alignment holes ({HOLE_CONFIG['diameter']}mm) at each X-cut position")
    print(f"   Holes at {positions_str} of slice height")
    if GEOMETRY_CONFIG['adaptive_positioning']:
        print(f"   Using adaptive positioning with {HOLE_CONFIG['min_wall_thickness']}mm minimum wall thickness")
    
    for slice_info in state.port_plan['slice_plans']:
        if slice_info['needs_x_split']:
            x_center = slice_info['x_center']
            z_start = slice_info['z_start']
            z_end = slice_info['z_end']
            modified_shape = add_x_cut_alignment_pins(state.port_half, x_center, z_start, z_end)
            if modified_shape is None:
                print(f"   ❌ FAILED to add X-cut alignment pins")
                return False
            state.port_half = modified_shape
    
    state.port_half_obj.Shape = state.port_half
    state.port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Alignment_Holes"
    state.port_half_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['port_aligned']
    
    update_view()
    print(f"   🔄 View updated to show all alignment holes in solid")
    print(f"   ✅ Solid port half ready with all alignment features")
    
    return True


def add_y_joining_to_port():
    """Add Y-direction holes for joining port and starboard halves"""
    
    rows = len(HOLE_POSITIONS['y_join_rows'])
    cols = len(HOLE_POSITIONS['y_join_cols'])
    row_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['y_join_rows']])
    col_str = ', '.join([f"{p*100:.0f}%" for p in HOLE_POSITIONS['y_join_cols']])
    
    print(f"\n🔩 Adding Y-direction holes for joining port and starboard halves...")
    print(f"   Adding {rows} rows per section at {row_str} of height")
    print(f"   Adding {cols} holes ({HOLE_CONFIG['diameter']}mm) per row at {col_str} of chord")
    print(f"   Holes oriented horizontally (Y-axis) for joining halves")
    if GEOMETRY_CONFIG['adaptive_positioning']:
        print(f"   Using adaptive positioning with {HOLE_CONFIG['min_wall_thickness']}mm minimum wall thickness")
    
    for i, slice_info in enumerate(state.port_plan['slice_plans']):
        section_num = i + 1
        z_start = slice_info['z_start']
        z_end = slice_info['z_end']
        section_name = f"Section {section_num}"
        
        print(f"\n   Processing {section_name} (Z: {z_start:.0f} to {z_end:.0f}mm)")
        
        modified_shape = add_y_half_joining_holes(state.port_half, z_start, z_end, section_name)
        if modified_shape is None:
            print(f"   ❌ FAILED to add Y-joining holes")
            return False
        state.port_half = modified_shape
    
    # Ensure solid after all hole operations
    solid_shape = ensure_solid(state.port_half, "hole operations")
    if solid_shape is None:
        print(f"   ❌ FAILED to ensure solid shape")
        return False
    state.port_half = solid_shape
    
    state.port_half_obj.Shape = state.port_half
    state.port_half_obj.Label = f"{BOAT_NAME}_Port_Half_with_Joining_Holes"
    state.port_half_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['port_joined']
    
    update_view()
    print(f"   🔄 View updated to show joining holes in solid")
    print(f"   ✅ Solid port half complete with alignment and joining features")
    
    return True


def pre_boolean_checks():
    """Perform pre-Boolean operation validation checks"""
    print(f"\n🔍 Performing pre-Boolean operation checks...")
    print(f"   Checking port half with holes vs stock cutout")
    
    # Check 1: Validate shapes
    if not state.port_half.isValid():
        print(f"❌ Port half shape is not valid!")
        return False
    
    if not state.stock_cutout_obj.Shape.isValid():
        print(f"❌ Stock cutout shape is not valid!")
        return False
    
    print(f"   ✅ Both shapes are valid")
    
    # Check 2: Ensure shapes are solids
    if not state.port_half.ShapeType == "Solid":
        print(f"❌ Port half is not a solid! (Type: {state.port_half.ShapeType})")
        return False
    
    if not state.stock_cutout_obj.Shape.ShapeType == "Solid":
        print(f"❌ Stock cutout is not a solid! (Type: {state.stock_cutout_obj.Shape.ShapeType})")
        return False
    
    print(f"   ✅ Both shapes are solids")
    
    # Check 3: Check for intersection
    try:
        common_volume = state.port_half.common(state.stock_cutout_obj.Shape)
        if common_volume.Volume < VALIDATION_CONFIG['min_intersection_volume']:
            print(f"❌ No meaningful intersection between shapes!")
            print(f"   Common volume: {common_volume.Volume:.6f} mm³")
            return False
    except Exception as e:
        print(f"❌ Failed to compute intersection: {e}")
        return False
    
    print(f"   ✅ Shapes intersect properly (common volume: {common_volume.Volume:.2f} mm³)")
    
    # Check 4: Check bounding box overlap
    port_bbox = state.port_half.BoundBox
    cutout_bbox = state.stock_cutout_obj.Shape.BoundBox
    
    if not (port_bbox.intersect(cutout_bbox)):
        print(f"❌ Bounding boxes do not intersect!")
        return False
    
    print(f"   ✅ Bounding boxes overlap correctly")
    
    # Check 5: Check shape complexity
    print(f"   ℹ️ Shape complexity:")
    print(f"      Port half with holes: {len(state.port_half.Faces)} faces, {len(state.port_half.Edges)} edges")
    print(f"      Stock cutout: {len(state.stock_cutout_obj.Shape.Faces)} faces, {len(state.stock_cutout_obj.Shape.Edges)} edges")
    
    if len(state.port_half.Faces) > VALIDATION_CONFIG['high_face_count_warning'] or \
       len(state.stock_cutout_obj.Shape.Faces) > VALIDATION_CONFIG['high_face_count_warning']:
        print(f"   ⚠️ Warning: High face count detected. Boolean operation may be slow.")
    
    print(f"\n✅ All pre-Boolean checks passed successfully!")
    return True


def boolean_cut_operation():
    """Perform boolean cut to create hollowed port half"""
    
    print(f"\n🔧 Creating cavity with boolean cut on port half...")
    print(f"   ⏳ This may take a moment for complex geometry...")
    try:
        original_faces = len(state.port_half.Faces)
        hollowed_port_half = state.port_half.cut(state.stock_cutout_obj.Shape)
        
        # Verify the cut worked
        if hollowed_port_half.isNull() or len(hollowed_port_half.Faces) <= original_faces:
            print(f"   ❌ FAILED: Boolean cut produced invalid result")
            return False
        
        state.port_half = hollowed_port_half
        
        state.port_half_obj.Shape = state.port_half
        state.port_half_obj.Label = f"{BOAT_NAME}_Port_Half_Hollowed"
        state.port_half_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['port_hollowed']
        state.port_half_obj.ViewObject.Transparency = VISUALIZATION_CONFIG['transparency']['hollowed']
        
        state.stock_obj.ViewObject.Visibility = True
        state.stock_obj.ViewObject.ShapeColor = VISUALIZATION_CONFIG['colors']['stock']
        
        print(f"   ✅ Cavity created successfully in port half")
        print(f"   Original port half faces: {original_faces}")
        print(f"   Hollowed port half faces: {len(state.port_half.Faces)}")
        
        update_view()
        return True
        
    except Exception as e:
        print(f"   ❌ FAILED: Boolean cut failed: {e}")
        return False


def cut_pieces():
    """Cut hollowed port half into pieces according to plan"""
    
    print(f"\n📐 Cutting pieces...")
    print(f"   Alignment and joining holes will be split automatically by cuts")
    
    state.port_half_obj.ViewObject.Visibility = False
    state.stock_obj.ViewObject.Visibility = False
    
    state.pieces = []
    state.piece_objects = []
    
    extra = GEOMETRY_CONFIG['boolean_box_extra']
    offset = GEOMETRY_CONFIG['boolean_box_offset']
    cut_extra = GEOMETRY_CONFIG['cutting_box_extra']
    cut_offset = GEOMETRY_CONFIG['cutting_box_offset']
    
    # Cut into Z slices
    for i, slice_info in enumerate(state.port_plan['slice_plans']):
        slice_num = i + 1
        z_start = slice_info['z_start']
        z_end = slice_info['z_end']
        
        print(f"\n   Processing slice {slice_num} (Z: {z_start:.0f} to {z_end:.0f}mm)")
        
        slice_bbox = state.port_half.BoundBox
        
        # Box to isolate this Z slice
        slice_box = Part.makeBox(
            slice_bbox.XLength + extra,
            slice_bbox.YLength + extra,
            z_end - z_start,
            Vector(slice_bbox.XMin - offset, slice_bbox.YMin - offset, z_start)
        )
        
        try:
            slice_shape = state.port_half.common(slice_box)
            
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
                
                state.pieces.append((name_a, piece_a))
                state.pieces.append((name_b, piece_b))
                
                print(f"      ✅ Created pieces {name_a} and {name_b}")
                
                # Create FreeCAD objects
                for name, piece, x_offset in [(name_a, piece_a, -1), (name_b, piece_b, 1)]:
                    obj = state.doc.addObject("Part::Feature", f"{BOAT_NAME}_{name}")
                    obj.Shape = piece
                    obj.ViewObject.ShapeColor = (0.2 + i*0.15, 0.4, 0.6)
                    obj.ViewObject.Transparency = VISUALIZATION_CONFIG['transparency']['pieces']
                    
                    if VISUALIZATION_CONFIG['explosion_factor'] > 0:
                        obj.Placement.Base.x += x_offset * VISUALIZATION_CONFIG['explosion_factor']
                        obj.Placement.Base.z += i * VISUALIZATION_CONFIG['explosion_factor']
                    
                    state.piece_objects.append(obj)
                
            else:
                name = f"{slice_num}A"
                state.pieces.append((name, slice_shape))
                
                print(f"      ✅ Created piece {name} (no X-split needed)")
                
                obj = state.doc.addObject("Part::Feature", f"{BOAT_NAME}_{name}")
                obj.Shape = slice_shape
                obj.ViewObject.ShapeColor = (0.2 + i*0.15, 0.4, 0.6)
                obj.ViewObject.Transparency = VISUALIZATION_CONFIG['transparency']['pieces']
                
                if VISUALIZATION_CONFIG['explosion_factor'] > 0:
                    obj.Placement.Base.z += i * VISUALIZATION_CONFIG['explosion_factor']
                
                state.piece_objects.append(obj)
                
        except Exception as e:
            print(f"      ❌ FAILED to create slice: {e}")
            return False
    
    if len(state.pieces) == 0:
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
    
    for piece_name, piece_shape in state.pieces:
        try:
            temp_obj = state.doc.addObject("Part::Feature", f"temp_{piece_name}")
            temp_obj.Shape = piece_shape
            
            piece_path = f"{pieces_folder}/{BOAT_NAME}_{piece_name}.step"
            save_step(temp_obj, piece_path, verbose=False)
            
            state.doc.removeObject(temp_obj.Name)
            
            print(f"   ✅ Exported: {piece_name}")
            exported_count += 1
            
        except Exception as e:
            print(f"   ❌ FAILED to export {piece_name}: {e}")
            # Clean up temp object if it exists
            if f"temp_{piece_name}" in [obj.Name for obj in state.doc.Objects]:
                state.doc.removeObject(f"temp_{piece_name}")
            return False
    
    if exported_count != len(state.pieces):
        print(f"   ❌ FAILED: Only exported {exported_count}/{len(state.pieces)} pieces")
        return False
    
    print(f"\n   📦 Successfully exported {exported_count}/{len(state.pieces)} pieces")
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
    if GEOMETRY_CONFIG['adaptive_positioning']:
        print(f"   Adaptive positioning:")
        print(f"      • Holes centered in available material thickness")
        print(f"      • Minimum wall thickness: {HOLE_CONFIG['min_wall_thickness']}mm")
        print(f"      • Holes skipped where material is insufficient")
    print(f"   Processing approach:")
    print(f"      • Split solid foil first (more reliable)")
    print(f"      • Add all holes to solid geometry (cleaner cuts)")
    print(f"      • Boolean cut last (on port half only)")
    print(f"   Chord bounds caching:")
    print(f"      • Cached {len(state.chord_bounds_cache)} unique Z positions")
    print(f"      • Reduced redundant geometry sampling operations")
    print(f"   Pieces created (to be mirrored):")
    piece_list = [name for name, _ in state.pieces]
    piece_list.sort()
    for piece_name in piece_list:
        print(f"      • {piece_name}")
    print(f"   📦 UNIQUE PIECES: {len(state.pieces)}")
    print(f"   📦 TOTAL AFTER MIRRORING: {len(state.pieces) * 2}")
    
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