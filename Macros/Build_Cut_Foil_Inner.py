import FreeCAD
import FreeCADGui
import Import
import Part
import json
import os
import time
import sys
import shutil

# Foil Mold Importer for Boat Manufacturing - FreeCAD 1.1 Compatible
# VERSION: 3.5.0 - DUAL CUT PLATES

print("=== FREECAD MOLD IMPORTER VERSION 3.5.0 - DUAL CUT PLATES ===")
FreeCAD.Console.PrintMessage("=== FREECAD MOLD IMPORTER VERSION 3.5.0 - DUAL CUT PLATES ===\n")

# Stock positioning parameters
POST_CENTRE_X = 323  # mm - X position for post centre
POST_TOP_Z = -79     # mm - Z position for top of post
POST_DIAMETER = 44   # mm - diameter of the post
POST_DIAMETER_DELTA = 4  # mm - difference in post diameter for cutout stock

# System configuration (not user parameters)
helpers_path = os.path.expanduser("~/Rudder_Code/helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)

try:
    import hole_array_helper
    FreeCAD.Console.PrintMessage("Successfully imported hole_array_helper module\n")
except ImportError as e:
    FreeCAD.Console.PrintError(f"Could not import hole_array_helper: {str(e)}\n")
    hole_array_helper = None

def create_circular_perforation_pattern(length, width, thickness, hole_diameter=10.0, spacing=15.0):
    """Create a plate with circular perforation pattern
    
    Args:
        length: Plate length in mm
        width: Plate width in mm  
        thickness: Plate thickness in mm
        hole_diameter: Diameter of circular holes in mm
        spacing: Center-to-center spacing between holes in mm
        
    Returns:
        Tuple of (perforated_shape, info_dict)
    """
    try:
        # Create base plate
        base_plate = Part.makeBox(length, width, thickness)
        
        # Calculate hole array dimensions
        margin = spacing / 2  # Margin from edges
        
        # Calculate number of holes that fit
        nx = int((length - 2 * margin) / spacing) + 1
        ny = int((width - 2 * margin) / spacing) + 1
        
        # Adjust spacing to fit evenly
        actual_spacing_x = (length - 2 * margin) / max(1, (nx - 1)) if nx > 1 else 0
        actual_spacing_y = (width - 2 * margin) / max(1, (ny - 1)) if ny > 1 else 0
        
        # Create holes to subtract
        holes = []
        hole_count = 0
        
        for i in range(nx):
            for j in range(ny):
                x = margin + i * actual_spacing_x if nx > 1 else length / 2
                y = margin + j * actual_spacing_y if ny > 1 else width / 2
                
                # Only create hole if it's fully within the plate (with small buffer)
                if (x - hole_diameter/2 > 1 and x + hole_diameter/2 < length - 1 and
                    y - hole_diameter/2 > 1 and y + hole_diameter/2 < width - 1):
                    
                    # Create cylinder for hole
                    cylinder = Part.makeCylinder(
                        hole_diameter / 2,
                        thickness + 2,  # Slightly taller than plate
                        FreeCAD.Vector(x, y, -1),  # Start below plate
                        FreeCAD.Vector(0, 0, 1)
                    )
                    holes.append(cylinder)
                    hole_count += 1
        
        # Subtract all holes from base plate
        if holes:
            FreeCAD.Console.PrintMessage(f"      Creating {hole_count} circular holes...\n")
            
            # Fuse all holes first for efficiency
            if len(holes) > 1:
                holes_union = holes[0]
                for hole in holes[1:]:
                    holes_union = holes_union.fuse(hole)
            else:
                holes_union = holes[0]
            
            # Subtract from base plate
            perforated = base_plate.cut(holes_union)
        else:
            perforated = base_plate
            FreeCAD.Console.PrintWarning("      No holes created (plate too small)\n")
        
        # Create info dict similar to hex pattern
        info = {
            'total_holes': hole_count,
            'hole_diameter': hole_diameter,
            'spacing': spacing,
            'pattern': 'circular',
            'grid': f'{nx}x{ny}'
        }
        
        return perforated, info
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error creating circular perforation: {str(e)}\n")
        # Return solid plate as fallback
        return Part.makeBox(length, width, thickness), {'total_holes': 0, 'pattern': 'solid'}

def create_perforation_pattern(length, width, thickness, pattern_type='hex',
                              hex_radius=5.0, hex_wall_thickness=3.0,
                              hole_diameter=10.0, hole_spacing=15.0):
    """Create a perforated plate with either hex or circular pattern
    
    Args:
        length, width, thickness: Plate dimensions
        pattern_type: 'hex', 'circle', or 'solid'
        hex_radius, hex_wall_thickness: Parameters for hex pattern
        hole_diameter, hole_spacing: Parameters for circular pattern
        
    Returns:
        Tuple of (shape, info_dict)
    """
    if pattern_type == 'hex' and hex_array_helper:
        FreeCAD.Console.PrintMessage(f"    Creating hex perforation pattern...\n")
        return hex_array_helper.create_honeycomb_geometry(
            length=length,
            width=width,
            thickness=thickness,
            hex_radius=hex_radius,
            wall_thickness=hex_wall_thickness
        )
    elif pattern_type == 'circle' and hole_array_helper:
        FreeCAD.Console.PrintMessage(f"    Creating circular perforation pattern (using hole_array_helper)...\n")
        return hole_array_helper.create_circular_perforation_pattern(
            length=length,
            width=width,
            thickness=thickness,
            hole_diameter=hole_diameter,
            spacing=hole_spacing
        )
    elif pattern_type == 'circle':
        FreeCAD.Console.PrintMessage(f"    Creating circular perforation pattern (built-in)...\n")
        return create_circular_perforation_pattern(
            length=length,
            width=width,
            thickness=thickness,
            hole_diameter=hole_diameter,
            spacing=hole_spacing
        )
    else:  # solid
        FreeCAD.Console.PrintMessage(f"    Creating solid plate (no perforations)...\n")
        return Part.makeBox(length, width, thickness), {'pattern': 'solid', 'total_holes': 0}

def import_foil(boat_name):
    """Import the cutting plan JSON and foil STEP file"""
    # Construct file paths
    boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
    output_folder = f"{boat_folder}/output"
    cut_foil_folder = f"{output_folder}/cut_foil"
    cutting_plan_file = f"{cut_foil_folder}/{boat_name}_Cut_Foil_cutting_plan.json"
    foil_step_file = f"{cut_foil_folder}/{boat_name}_Cut_Foil.step"
    
    if not os.path.exists(cutting_plan_file):
        FreeCAD.Console.PrintError(f"Cutting plan file not found: {cutting_plan_file}\n")
        return None, None
        
    if not os.path.exists(foil_step_file):
        FreeCAD.Console.PrintError(f"Foil STEP file not found: {foil_step_file}\n")
        return None, None
    
    try:
        with open(cutting_plan_file, 'r') as f:
            cutting_plan = json.load(f)
        FreeCAD.Console.PrintMessage(f"Loaded cutting plan: {cutting_plan_file}\n")
        print("Cutting plan data:")
        print(f"  Z-cuts: {cutting_plan['cutting_plan']['z_cuts']}")
        print(f"  X-cuts: {cutting_plan['cutting_plan']['x_cuts']}")
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error loading cutting plan: {str(e)}\n")
        return None, None
    
    try:
        Import.insert(foil_step_file, FreeCAD.ActiveDocument.Name)
        FreeCAD.Console.PrintMessage(f"Imported foil STEP file: {foil_step_file}\n")
        
        foil_object = FreeCAD.ActiveDocument.Objects[-1]
        foil_object.Label = f"{boat_name}_Foil"
        
        FreeCAD.ActiveDocument.recompute()
        time.sleep(0.5)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error importing foil STEP file: {str(e)}\n")
        return cutting_plan, None
    
    return cutting_plan, foil_object

def import_foil_shell(boat_name):
    """Import the foil shell STL if it exists"""
    try:
        boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
        shell_file = f"{boat_folder}/output/cut_foil/{boat_name}_Shell_Foil.stl"
        
        if os.path.exists(shell_file):
            import Mesh
            mesh = Mesh.read(shell_file)
            shell_object = FreeCAD.ActiveDocument.addObject("Mesh::Feature", "FoilShell")
            shell_object.Mesh = mesh
            shell_object.Label = f"{boat_name}_Foil_Shell"
            
            if hasattr(shell_object, 'ViewObject') and shell_object.ViewObject:
                shell_object.ViewObject.Transparency = 50
            
            FreeCAD.Console.PrintMessage(f"✅ Imported foil shell: {boat_name}_Shell_Foil.stl\n")
            return shell_object
        else:
            FreeCAD.Console.PrintMessage(f"ℹ️ No foil shell found at: {shell_file}\n")
            return None
            
    except Exception as e:
        FreeCAD.Console.PrintError(f"Failed to import foil shell: {str(e)}\n")
        return None

def import_stock_cutout(boat_name):
    """Import and position the stock cutout STEP file"""
    try:
        boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
        cutout_folder = f"{boat_folder}/output/cutout"
        stock_cutout_file = f"{cutout_folder}/{boat_name}_Stock_Cutout.step"
        
        if not os.path.exists(stock_cutout_file):
            FreeCAD.Console.PrintMessage(f"ℹ️ No stock cutout found at: {stock_cutout_file}\n")
            return None
        
        FreeCAD.Console.PrintMessage(f"\n=== Importing Stock Cutout ===\n")
        
        # Import the STEP file
        imported_shape = Part.read(stock_cutout_file)
        
        # Create object in document
        stock_cutout_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", f"{boat_name}_Stock_Cutout")
        stock_cutout_obj.Shape = imported_shape
        
        FreeCAD.Console.PrintMessage(f"✅ Imported stock cutout\n")
        FreeCAD.Console.PrintMessage(f"   Bounds: {stock_cutout_obj.Shape.BoundBox}\n")
        
        # Rotate stock cutout 180° around Z-axis to orient tangs toward trailing edge
        FreeCAD.Console.PrintMessage(f"🔄 Rotating stock cutout 180° to orient tangs correctly...\n")
        stock_cutout_matrix = FreeCAD.Matrix()
        stock_cutout_matrix.rotateZ(3.14159)  # 180° in radians
        rotated_cutout_shape = stock_cutout_obj.Shape.transformGeometry(stock_cutout_matrix)
        stock_cutout_obj.Shape = rotated_cutout_shape
        FreeCAD.Console.PrintMessage(f"   ✅ Stock cutout rotated - tangs now point toward trailing edge\n")
        
        # Position the stock cutout based on post location
        FreeCAD.Console.PrintMessage(f"📍 Positioning stock cutout based on post location...\n")
        cutout_post_diameter = POST_DIAMETER + POST_DIAMETER_DELTA
        cutout_target_x = POST_CENTRE_X  # Use the same X as regular stock
        FreeCAD.Console.PrintMessage(f"   Post centre target: X={cutout_target_x}mm\n")
        FreeCAD.Console.PrintMessage(f"   Post top target: Z={POST_TOP_Z}mm\n")
        FreeCAD.Console.PrintMessage(f"   Post diameter for cutout: {cutout_post_diameter}mm\n")
        
        # Get current bounding box of stock cutout
        current_cutout_bbox = stock_cutout_obj.Shape.BoundBox
        
        # Calculate post centre X position for cutout
        current_cutout_post_centre_x = current_cutout_bbox.XMax - (cutout_post_diameter / 2)
        current_cutout_post_top_z = current_cutout_bbox.ZMax
        
        FreeCAD.Console.PrintMessage(f"   Current cutout post centre X: {current_cutout_post_centre_x:.1f}mm\n")
        FreeCAD.Console.PrintMessage(f"   Current cutout post top Z: {current_cutout_post_top_z:.1f}mm\n")
        
        # Calculate offset needed to move cutout post to target position
        cutout_offset = FreeCAD.Vector(
            cutout_target_x - current_cutout_post_centre_x,  # Move post centre to target X
            0,                                                # Keep Y unchanged
            POST_TOP_Z - current_cutout_post_top_z           # Move post top to specified Z
        )
        
        # Apply translation to cutout
        cutout_translation_matrix = FreeCAD.Matrix()
        cutout_translation_matrix.move(cutout_offset)
        positioned_cutout_shape = stock_cutout_obj.Shape.transformGeometry(cutout_translation_matrix)
        stock_cutout_obj.Shape = positioned_cutout_shape
        
        # Report final cutout position
        final_cutout_bbox = stock_cutout_obj.Shape.BoundBox
        final_cutout_post_centre_x = final_cutout_bbox.XMax - (cutout_post_diameter / 2)
        final_cutout_post_top_z = final_cutout_bbox.ZMax
        
        FreeCAD.Console.PrintMessage(f"   ✅ Stock cutout positioned:\n")
        FreeCAD.Console.PrintMessage(f"      Post centre X: {final_cutout_post_centre_x:.1f}mm (target: {cutout_target_x}mm)\n")
        FreeCAD.Console.PrintMessage(f"      Post top Z: {final_cutout_post_top_z:.1f}mm (target: {POST_TOP_Z}mm)\n")
        
        # Make visible with transparency
        if hasattr(stock_cutout_obj, 'ViewObject') and stock_cutout_obj.ViewObject:
            stock_cutout_obj.ViewObject.Visibility = True
            stock_cutout_obj.ViewObject.Transparency = 70
            stock_cutout_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red tint to distinguish
        
        return stock_cutout_obj
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Failed to import stock cutout: {str(e)}\n")
        return None

def configure_display(foil_object, cutting_plan):
    """Configure FreeCAD display for optimal viewing"""
    try:
        if not hasattr(FreeCADGui, 'ActiveDocument') or not FreeCADGui.ActiveDocument:
            FreeCAD.Console.PrintWarning("No GUI available - skipping display configuration\n")
            return
            
        try:
            if hasattr(foil_object, 'ViewObject') and foil_object.ViewObject:
                foil_object.ViewObject.Transparency = 70
                FreeCAD.ActiveDocument.recompute()
                FreeCADGui.updateGui()
                FreeCAD.Console.PrintMessage("Set foil transparency to 70%\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error setting transparency: {str(e)}\n")
        
        try:
            view = FreeCADGui.activeView()
            if view:
                try:
                    view.viewIsometric()
                    FreeCAD.Console.PrintMessage("Set isometric view\n")
                except:
                    try:
                        view.setViewDirection((1, 1, 1))
                        FreeCAD.Console.PrintMessage("Set isometric view (alternative method)\n")
                    except:
                        FreeCAD.Console.PrintWarning("Could not set isometric view\n")
                
                try:
                    view.fitAll()
                    FreeCAD.Console.PrintMessage("Fitted all objects to view\n")
                except:
                    FreeCAD.Console.PrintWarning("Could not fit view\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error configuring view: {str(e)}\n")
        
        # Print cutting summary
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("CUTTING PLAN SUMMARY:\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        
        FreeCAD.Console.PrintMessage(f"Z-CUTS (horizontal):\n")
        for i, z_pos in enumerate(z_cuts):
            FreeCAD.Console.PrintMessage(f"  Cut {i+1}: Z = {z_pos:.2f} mm\n")
            
        FreeCAD.Console.PrintMessage(f"\nY-CUT (centerline):\n")
        FreeCAD.Console.PrintMessage(f"  Cut 1: Y = 0.00 mm\n")
        
        FreeCAD.Console.PrintMessage(f"\nX-CUTS (vertical):\n")
        for i, x_pos in enumerate(x_cuts):
            FreeCAD.Console.PrintMessage(f"  Cut {i+1}: X = {x_pos:.2f} mm\n")
            
        FreeCAD.Console.PrintMessage(f"\nTotal segments: {(len(z_cuts)+1)*2*(len(x_cuts)+1)} pieces\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error configuring display: {str(e)}\n")

def prepare_foil_for_boolean(foil_object):
    """Ensure foil is a solid for boolean operations"""
    num_solids = len(foil_object.Shape.Solids)
    
    if num_solids == 0:
        FreeCAD.Console.PrintMessage("Foil has no solids - attempting to create solid...\n")
        try:
            num_shells = len(foil_object.Shape.Shells)
            if num_shells > 0:
                solid_shape = Part.makeSolid(foil_object.Shape.Shells[0])
                if len(solid_shape.Solids) > 0:
                    FreeCAD.Console.PrintMessage("Successfully created solid from foil shell!\n")
                    return solid_shape
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error making solid: {str(e)}\n")
    
    return foil_object.Shape

def calculate_support_plate_positions(z_cuts, foil_bbox, plate_spacing):
    """Calculate positions for support plates"""
    support_positions = []
    z_min = foil_bbox.ZMin
    z_max = foil_bbox.ZMax
    z_cuts_sorted = sorted(z_cuts)
    all_boundaries = [z_min] + z_cuts_sorted + [z_max]
    
    for i in range(len(all_boundaries) - 1):
        segment_start = all_boundaries[i]
        segment_end = all_boundaries[i + 1]
        segment_length = segment_end - segment_start
        num_supports = int(segment_length / plate_spacing)
        
        if num_supports > 1:
            actual_spacing = segment_length / (num_supports + 1)
            
            for j in range(1, num_supports + 1):
                support_z = segment_start + (j * actual_spacing)
                
                too_close = False
                for cut_z in z_cuts_sorted:
                    if abs(support_z - cut_z) < 10:
                        too_close = True
                        break
                
                if not too_close:
                    support_positions.append(support_z)
    
    return sorted(support_positions)

def calculate_x_support_positions(x_cuts, foil_bbox, x_support_spacing):
    """Calculate positions for X-direction support plates"""
    support_positions = []
    x_min = foil_bbox.XMin
    x_max = foil_bbox.XMax
    x_cuts_sorted = sorted(x_cuts)
    all_boundaries = [x_min] + x_cuts_sorted + [x_max]
    
    for i in range(len(all_boundaries) - 1):
        segment_start = all_boundaries[i]
        segment_end = all_boundaries[i + 1]
        segment_length = segment_end - segment_start
        num_supports = int(segment_length / x_support_spacing)
        
        if num_supports > 1:
            actual_spacing = segment_length / (num_supports + 1)
            
            for j in range(1, num_supports + 1):
                support_x = segment_start + (j * actual_spacing)
                
                too_close = False
                for cut_x in x_cuts_sorted:
                    if abs(support_x - cut_x) < 10:
                        too_close = True
                        break
                
                if not too_close:
                    support_positions.append(support_x)
    
    return sorted(support_positions)

def create_z_cut_plates(foil_object, cutting_plan, boat_name, plate_thickness, bounding_margin, 
                       hex_radius, hex_wall_thickness, pattern_type='hex', 
                       hole_diameter=10.0, hole_spacing=15.0, stock_cutout=None):
    """Create Z-cut plates (horizontal - XY plane) - DUAL PLATES"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Z-Cut Plates (Dual Half-Thickness) ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        FreeCAD.Console.PrintMessage(f"Foil bounding box: X({foil_bbox.XMin:.2f} to {foil_bbox.XMax:.2f}), "
                                   f"Y({foil_bbox.YMin:.2f} to {foil_bbox.YMax:.2f}), "
                                   f"Z({foil_bbox.ZMin:.2f} to {foil_bbox.ZMax:.2f})\n")
        
        working_shape = prepare_foil_for_boolean(foil_object)
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        
        # Half the plate thickness for dual plates
        half_thickness = plate_thickness / 2
        
        FreeCAD.Console.PrintMessage(f"Creating {len(z_cuts)*2} Z-cut plates ({half_thickness}mm thick each)...\n")
        FreeCADGui.updateGui()
        
        for i, z_pos in enumerate(z_cuts):
            # Create two plates - one above and one below the cut line
            for side in ["Lower", "Upper"]:
                try:
                    # CORRECTED: Plates meet exactly at the cut line
                    plate_z = z_pos - half_thickness/2 if side == "Lower" else z_pos + half_thickness/2
                    FreeCAD.Console.PrintMessage(f"  [Plate {i+1}{side[0]}] Creating {side} Z-cut plate at Z={plate_z:.2f}...\n")
                    FreeCADGui.updateGui()
                    
                    plate_x_size = (foil_bbox.XMax - foil_bbox.XMin) + 2 * bounding_margin
                    plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                    
                    # Create perforated or solid plate based on pattern_type
                    perf_shape, perf_info = create_perforation_pattern(
                        plate_x_size, plate_y_size, half_thickness,
                        pattern_type, hex_radius, hex_wall_thickness,
                        hole_diameter, hole_spacing
                    )
                    
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Z_CutPlate_{i+1}_{side}")
                    plate.Shape = perf_shape
                    
                    if 'total_hexagons' in perf_info:
                        FreeCAD.Console.PrintMessage(f"    Hex pattern: {perf_info['total_hexagons']} hexagons\n")
                    elif 'total_holes' in perf_info:
                        FreeCAD.Console.PrintMessage(f"    Circular pattern: {perf_info['total_holes']} holes\n")
                    
                    plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
                    plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                    
                    plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z)
                    
                    FreeCAD.Console.PrintMessage(f"    Performing boolean intersection...\n")
                    FreeCADGui.updateGui()
                    
                    try:
                        shaped = plate.Shape.common(working_shape)
                        if shaped.Volume > 0:
                            plate.Shape = shaped
                            FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
                            
                            # Cut out stock if provided
                            if stock_cutout and stock_cutout.Shape:
                                FreeCAD.Console.PrintMessage(f"    Cutting out stock from plate...\n")
                                plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                                FreeCAD.Console.PrintMessage(f"    Stock cutout complete\n")
                        else:
                            FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
                    except Exception as e:
                        FreeCAD.Console.PrintError(f"    Boolean operation failed: {str(e)}\n")
                        raise
                    
                    plate.Label = f"{boat_name}_Z_CutPlate_{i+1}_{side}_at_Z{z_pos:.1f}"
                    plates.append(plate)
                    
                    FreeCAD.Console.PrintMessage(f"  [Plate {i+1}{side[0]}] Completed\n")
                    
                    # Breathing room after each plate
                    FreeCADGui.updateGui()
                    FreeCAD.ActiveDocument.recompute()
                    time.sleep(0.2)
                    
                except Exception as e:
                    FreeCAD.Console.PrintError(f"FATAL: Failed creating Z-cut plate {i+1} {side}: {str(e)}\n")
                    raise
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_z_cut_plates failed: {str(e)}\n")
        raise
    
    return plates

def create_z_support_plates(foil_object, cutting_plan, boat_name, support_plate_thickness, plate_spacing, 
                           bounding_margin, hex_radius, hex_wall_thickness, pattern_type='hex',
                           hole_diameter=10.0, hole_spacing=15.0, stock_cutout=None):
    """Create Z support plates (3mm thick) - SINGLE PLATES AS BEFORE"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Z-Support Plates ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        support_z_positions = calculate_support_plate_positions(z_cuts, foil_bbox, plate_spacing)
        FreeCAD.Console.PrintMessage(f"Creating {len(support_z_positions)} Z-support plates ({support_plate_thickness}mm thick)...\n")
        FreeCADGui.updateGui()
        
        for i, z_pos in enumerate(support_z_positions):
            try:
                FreeCAD.Console.PrintMessage(f"  [Support {i+1}/{len(support_z_positions)}] Creating at Z={z_pos:.2f}...\n")
                FreeCADGui.updateGui()
                
                plate_x_size = (foil_bbox.XMax - foil_bbox.XMin) + 2 * bounding_margin
                plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                
                # Create perforated or solid plate
                perf_shape, perf_info = create_perforation_pattern(
                    plate_x_size, plate_y_size, support_plate_thickness,
                    pattern_type, hex_radius, hex_wall_thickness,
                    hole_diameter, hole_spacing
                )
                
                plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Z_SupportPlate_{i+1}")
                plate.Shape = perf_shape
                FreeCAD.Console.PrintMessage(f"    Created {perf_info.get('pattern', 'unknown')} support plate\n")
                
                plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = z_pos - support_plate_thickness / 2
                
                plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
                        
                        # Cut out stock if provided
                        if stock_cutout and stock_cutout.Shape:
                            FreeCAD.Console.PrintMessage(f"    Cutting out stock from support plate...\n")
                            plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                            FreeCAD.Console.PrintMessage(f"    Stock cutout complete\n")
                except Exception as e:
                    FreeCAD.Console.PrintError(f"    Boolean operation failed: {str(e)}\n")
                    raise
                
                plate.Label = f"{boat_name}_Z_Support_{i+1}_at_Z{z_pos:.1f}"
                
                if hasattr(plate, 'ViewObject') and plate.ViewObject:
                    plate.ViewObject.Transparency = 85
                
                plates.append(plate)
                
                FreeCAD.Console.PrintMessage(f"  [Support {i+1}/{len(support_z_positions)}] Completed\n")
                
                # Breathing room after each plate
                FreeCADGui.updateGui()
                FreeCAD.ActiveDocument.recompute()
                time.sleep(0.2)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"FATAL: Failed creating Z-support plate {i+1}: {str(e)}\n")
                raise
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_z_support_plates failed: {str(e)}\n")
        raise
    
    return plates

def create_x_support_plates(foil_object, cutting_plan, boat_name, support_plate_thickness, x_support_spacing, 
                           bounding_margin, hex_radius, hex_wall_thickness, pattern_type='hex',
                           hole_diameter=10.0, hole_spacing=15.0, stock_cutout=None):
    """Create X support plates (3mm thick) at 50mm spacing - SINGLE PLATES AS BEFORE"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating X-Support Plates ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        support_x_positions = calculate_x_support_positions(x_cuts, foil_bbox, x_support_spacing)
        FreeCAD.Console.PrintMessage(f"Creating {len(support_x_positions)} X-support plates ({support_plate_thickness}mm thick) at {x_support_spacing}mm spacing...\n")
        FreeCADGui.updateGui()
        
        for i, x_pos in enumerate(support_x_positions):
            try:
                FreeCAD.Console.PrintMessage(f"  [X-Support {i+1}/{len(support_x_positions)}] Creating at X={x_pos:.2f}...\n")
                FreeCADGui.updateGui()
                
                plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                plate_z_size = (foil_bbox.ZMax - foil_bbox.ZMin) + 2 * bounding_margin
                
                # Create perforated or solid plate - note orientation is different for X plates
                perf_shape, perf_info = create_perforation_pattern(
                    plate_z_size, plate_y_size, support_plate_thickness,
                    pattern_type, hex_radius, hex_wall_thickness,
                    hole_diameter, hole_spacing
                )
                
                plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"X_SupportPlate_{i+1}")
                plate.Shape = perf_shape
                
                # Rotate 90 degrees around Y axis for vertical orientation
                rotation = FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90)
                plate.Placement.Rotation = rotation
                
                FreeCAD.Console.PrintMessage(f"    Created {perf_info.get('pattern', 'unknown')} X-support plate\n")
                
                plate_x_center = x_pos - support_plate_thickness / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 - plate_z_size / 2
                
                current_placement = plate.Placement
                current_placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center + plate_z_size)
                plate.Placement = current_placement
                
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
                        
                        # Cut out stock if provided
                        if stock_cutout and stock_cutout.Shape:
                            FreeCAD.Console.PrintMessage(f"    Cutting out stock from X-support plate...\n")
                            plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                            FreeCAD.Console.PrintMessage(f"    Stock cutout complete\n")
                except Exception as e:
                    FreeCAD.Console.PrintError(f"    Boolean operation failed: {str(e)}\n")
                    raise
                
                plate.Label = f"{boat_name}_X_Support_{i+1}_at_X{x_pos:.1f}"
                
                if hasattr(plate, 'ViewObject') and plate.ViewObject:
                    plate.ViewObject.Transparency = 85
                
                plates.append(plate)
                
                FreeCAD.Console.PrintMessage(f"  [X-Support {i+1}/{len(support_x_positions)}] Completed\n")
                
                # Breathing room after each plate
                FreeCADGui.updateGui()
                FreeCAD.ActiveDocument.recompute()
                time.sleep(0.2)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"FATAL: Failed creating X-support plate {i+1}: {str(e)}\n")
                raise
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_x_support_plates failed: {str(e)}\n")
        raise
    
    return plates

def create_y_cut_plate(foil_object, cutting_plan, boat_name, plate_thickness, bounding_margin, 
                      hex_wall_thickness, pattern_type='hex',
                      hole_diameter=16.0, hole_spacing=20.0, stock_cutout=None):
    """Create Y-cut plates (centerline - XZ plane) at Y=0 - DUAL PLATES"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Y-Cut Plates (Dual Half-Thickness) ===\n")
        FreeCAD.Console.PrintMessage("Creating Y-cut plates at Y=0...\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        plate_x_size = (foil_bbox.XMax - foil_bbox.XMin) + 2 * bounding_margin
        plate_z_size = (foil_bbox.ZMax - foil_bbox.ZMin) + 2 * bounding_margin
        
        # Half the plate thickness for dual plates
        half_thickness = plate_thickness / 2
        
        # Create two plates - one on each side of Y=0
        for side in ["Left", "Right"]:
            # CORRECTED: Plates meet exactly at Y=0
            plate_y = -half_thickness/2 if side == "Left" else half_thickness/2
            FreeCAD.Console.PrintMessage(f"  Creating {side} Y-cut plate at Y={plate_y:.2f}...\n")
            
            # Y-cut plate often prints flat, so can use larger holes
            if pattern_type == 'hex' and hex_array_helper:
                hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                    length=plate_x_size,
                    width=plate_z_size,
                    thickness=half_thickness,
                    hex_radius=8.0,  # Larger hex since this prints flat
                    wall_thickness=hex_wall_thickness
                )
                perf_shape = hex_shape
                perf_info = hex_info
            elif pattern_type == 'circle':
                # Use larger holes for Y-cut since it prints flat
                perf_shape, perf_info = create_perforation_pattern(
                    plate_x_size, plate_z_size, half_thickness,
                    pattern_type, 8.0, hex_wall_thickness,
                    hole_diameter, hole_spacing
                )
            else:
                perf_shape = Part.makeBox(plate_x_size, plate_z_size, half_thickness)                    
                perf_info = {'pattern': 'solid'}
            
            plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Y_CutPlate_{side}")
            plate.Shape = perf_shape
            
            # Always rotate 90 degrees around X axis for vertical orientation (all pattern types)
            rotation = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 90)
            plate.Placement.Rotation = rotation
            
            FreeCAD.Console.PrintMessage(f"  Y-Cut Plate {side}: {plate_x_size:.1f} × {half_thickness:.1f} × {plate_z_size:.1f} mm\n")
            if 'total_hexagons' in perf_info:
                FreeCAD.Console.PrintMessage(f"    Hex pattern: {perf_info['total_hexagons']} hexagons (8mm radius)\n")
            elif 'total_holes' in perf_info:
                FreeCAD.Console.PrintMessage(f"    Circular pattern: {perf_info['total_holes']} holes\n")
            
            plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
            plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 - plate_z_size / 2
            
            current_placement = plate.Placement
            current_placement.Base = FreeCAD.Vector(plate_x_center, plate_y, plate_z_center)
            plate.Placement = current_placement
            
            try:
                shaped = plate.Shape.common(working_shape)
                if shaped.Volume > 0:
                    plate.Shape = shaped
                    FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
                    
                    # Cut out stock if provided
                    if stock_cutout and stock_cutout.Shape:
                        FreeCAD.Console.PrintMessage(f"    Cutting out stock from Y-cut plate...\n")
                        plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                        FreeCAD.Console.PrintMessage(f"    Stock cutout complete\n")
                else:
                    FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
            except Exception as e:
                FreeCAD.Console.PrintError(f"    Boolean operation failed: {str(e)}\n")
                raise
            
            plate.Label = f"{boat_name}_Y_CutPlate_{side}_at_Y0"
            plates.append(plate)
            
            FreeCAD.Console.PrintMessage(f"  Y-Cut Plate {side} Completed\n")
            
            # Breathing room after plate
            FreeCADGui.updateGui()
            FreeCAD.ActiveDocument.recompute()
            time.sleep(0.2)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_y_cut_plate failed: {str(e)}\n")
        raise
    
    return plates

def create_x_cut_plates(foil_object, cutting_plan, boat_name, plate_thickness, bounding_margin, 
                       hex_radius, hex_wall_thickness, pattern_type='hex',
                       hole_diameter=10.0, hole_spacing=15.0, stock_cutout=None):
    """Create X-cut plates (vertical - YZ plane) - DUAL PLATES"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating X-Cut Plates (Dual Half-Thickness) ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        
        # Half the plate thickness for dual plates
        half_thickness = plate_thickness / 2
        
        FreeCAD.Console.PrintMessage(f"Creating {len(x_cuts)*2} X-cut plates ({half_thickness}mm thick each)...\n")
        FreeCADGui.updateGui()
        
        for i, x_pos in enumerate(x_cuts):
            # Create two plates - one on each side of the cut
            for side in ["Left", "Right"]:
                try:
                    # CORRECTED: Plates meet exactly at the cut line
                    plate_x = x_pos - half_thickness/2 if side == "Left" else x_pos + half_thickness/2
                    FreeCAD.Console.PrintMessage(f"  [Plate {i+1}{side[0]}] Creating {side} X-cut plate at X={plate_x:.2f}...\n")
                    FreeCADGui.updateGui()
                    
                    plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                    plate_z_size = (foil_bbox.ZMax - foil_bbox.ZMin) + 2 * bounding_margin
                    
                    # Create perforated or solid plate
                    perf_shape, perf_info = create_perforation_pattern(
                        plate_z_size, plate_y_size, half_thickness,
                        pattern_type, hex_radius, hex_wall_thickness,
                        hole_diameter, hole_spacing
                    )
                    
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"X_CutPlate_{i+1}_{side}")
                    plate.Shape = perf_shape
                    
                    # Rotate 90 degrees around Y axis for vertical orientation
                    rotation = FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90)
                    plate.Placement.Rotation = rotation
                    
                    if 'total_hexagons' in perf_info:
                        FreeCAD.Console.PrintMessage(f"    Hex pattern: {perf_info['total_hexagons']} hexagons\n")
                    elif 'total_holes' in perf_info:
                        FreeCAD.Console.PrintMessage(f"    Circular pattern: {perf_info['total_holes']} holes\n")
                    
                    plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                    plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 - plate_z_size / 2
                    
                    current_placement = plate.Placement
                    current_placement.Base = FreeCAD.Vector(plate_x, plate_y_center, plate_z_center + plate_z_size)
                    plate.Placement = current_placement
                    
                    try:
                        shaped = plate.Shape.common(working_shape)
                        if shaped.Volume > 0:
                            plate.Shape = shaped
                            FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
                            
                            # Cut out stock if provided
                            if stock_cutout and stock_cutout.Shape:
                                FreeCAD.Console.PrintMessage(f"    Cutting out stock from X-cut plate...\n")
                                plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                                FreeCAD.Console.PrintMessage(f"    Stock cutout complete\n")
                        else:
                            FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
                    except Exception as e:
                        FreeCAD.Console.PrintError(f"    Boolean operation failed: {str(e)}\n")
                        raise
                    
                    plate.Label = f"{boat_name}_X_CutPlate_{i+1}_{side}_at_X{x_pos:.1f}"
                    plates.append(plate)
                    
                    FreeCAD.Console.PrintMessage(f"  [Plate {i+1}{side[0]}] Completed\n")
                    
                    # Breathing room after each plate
                    FreeCADGui.updateGui()
                    FreeCAD.ActiveDocument.recompute()
                    time.sleep(0.2)
                    
                except Exception as e:
                    FreeCAD.Console.PrintError(f"FATAL: Failed creating X-cut plate {i+1} {side}: {str(e)}\n")
                    raise
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_x_cut_plates failed: {str(e)}\n")
        raise
    
    return plates

def export_plates_for_printing(plates, boat_name):
    """Export all plates as individual STL files to print_ready folder"""
    try:
        FreeCAD.Console.PrintMessage("\n=== Exporting Plates for 3D Printing ===\n")
        FreeCADGui.updateGui()
        
        # Construct export path
        boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
        output_folder = f"{boat_folder}/output/cut_foil"
        print_ready_folder = f"{output_folder}/print_ready"
        
        # Clear or create print_ready folder
        if os.path.exists(print_ready_folder):
            FreeCAD.Console.PrintMessage(f"Clearing existing print_ready folder...\n")
            shutil.rmtree(print_ready_folder)
        os.makedirs(print_ready_folder)
        
        FreeCAD.Console.PrintMessage(f"Export folder: {print_ready_folder}\n")
        
        # Export each plate as STL
        import Mesh
        exported_count = 0
        
        for plate in plates:
            try:
                filename = f"{print_ready_folder}/{plate.Label}.stl"
                Mesh.export([plate], filename)
                exported_count += 1
                FreeCAD.Console.PrintMessage(f"  ✅ Exported: {plate.Label}.stl\n")
            except Exception as e:
                FreeCAD.Console.PrintError(f"  ❌ Failed to export {plate.Label}: {str(e)}\n")
        
        FreeCAD.Console.PrintMessage(f"\n✅ Successfully exported {exported_count} STL files\n")
        FreeCAD.Console.PrintMessage(f"📁 Files ready in: {print_ready_folder}\n")
        FreeCAD.Console.PrintMessage("\nNext steps:\n")
        FreeCAD.Console.PrintMessage("1. Add your foil shell STL to the print_ready folder\n")
        FreeCAD.Console.PrintMessage("2. Import all files into Bambu Lab Studio\n")
        FreeCAD.Console.PrintMessage("3. Slice and print as single object\n")
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: export_plates_for_printing failed: {str(e)}\n")
        raise

def run_plate_creation(boat_name="MackenSea", 
                      plate_thickness=6.0,
                      support_plate_thickness=3.0,
                      plate_spacing=150.0,
                      bounding_margin=10.0,
                      hex_radius=5.0,
                      hex_wall_thickness=3.0,
                      pattern_type='circle',
                      hole_diameter=10.0,
                      hole_spacing=15.0):
    """Main business logic for plate creation
    
    Args:
        boat_name: Name of the boat (determines file paths)
        plate_thickness: Thickness of cutting plates in mm
        support_plate_thickness: Thickness of support plates in mm  
        plate_spacing: Target spacing between plates in mm
        bounding_margin: Margin around foil for plates in mm
        hex_radius: Radius of hexagonal perforations in mm
        hex_wall_thickness: Wall thickness between hexagons in mm
        pattern_type: 'hex', 'circle', or 'solid'
        hole_diameter: Diameter of circular holes in mm
        hole_spacing: Center-to-center spacing of holes in mm
    """
    cutting_plan, foil = import_foil(boat_name)
    
    if cutting_plan and foil:
        FreeCAD.Console.PrintMessage("Successfully imported cutting plan and foil!\n")
        FreeCAD.Console.PrintMessage(f"Foil object: {foil.Label}\n")
        configure_display(foil, cutting_plan)
        
        # Import stock cutout early so it can be used for plate cutting
        stock_cutout = import_stock_cutout(boat_name)
        
        all_plates = []
        
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("CREATING CUTTING AND SUPPORT PLATES\n")
        FreeCAD.Console.PrintMessage(f"Pattern type: {pattern_type.upper()}\n")
        FreeCAD.Console.PrintMessage(f"Cut plates: DUAL (half-thickness pairs)\n")
        FreeCAD.Console.PrintMessage(f"Support plates: SINGLE\n")
        if pattern_type == 'circle':
            FreeCAD.Console.PrintMessage(f"Hole diameter: {hole_diameter}mm, Spacing: {hole_spacing}mm\n")
        elif pattern_type == 'hex':
            FreeCAD.Console.PrintMessage(f"Hex radius: {hex_radius}mm, Wall thickness: {hex_wall_thickness}mm\n")
        if stock_cutout:
            FreeCAD.Console.PrintMessage(f"Stock cutout: ENABLED - plates will have stock clearance\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        z_cut_plates = []
        z_support_plates = []
        x_support_plates = []
        y_cut_plates = []
        x_cut_plates = []
        
        try:
            z_cut_plates = create_z_cut_plates(foil, cutting_plan, boat_name, plate_thickness, 
                                              bounding_margin, hex_radius, hex_wall_thickness,
                                              pattern_type, hole_diameter, hole_spacing, stock_cutout)
            all_plates.extend(z_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(z_cut_plates)} Z-cut plates (dual)\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Z-cut plates: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            z_support_plates = create_z_support_plates(foil, cutting_plan, boat_name, 
                                                      support_plate_thickness, plate_spacing,
                                                      bounding_margin, hex_radius, hex_wall_thickness,
                                                      pattern_type, hole_diameter, hole_spacing, stock_cutout)
            all_plates.extend(z_support_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(z_support_plates)} Z-support plates\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Z-support plates: {str(e)}\n")
        
        FreeCADGui.updateGui()
        
        # Create X-support plates at 50mm spacing
        try:
            x_support_spacing = 50.0  # Fixed 50mm spacing for X-supports
            x_support_plates = create_x_support_plates(foil, cutting_plan, boat_name,
                                                      support_plate_thickness, x_support_spacing,
                                                      bounding_margin, hex_radius, hex_wall_thickness,
                                                      pattern_type, hole_diameter, hole_spacing, stock_cutout)
            all_plates.extend(x_support_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(x_support_plates)} X-support plates\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create X-support plates: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            y_cut_plates = create_y_cut_plate(foil, cutting_plan, boat_name, plate_thickness,
                                             bounding_margin, hex_wall_thickness,
                                             pattern_type, hole_diameter, hole_spacing, stock_cutout)
            all_plates.extend(y_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(y_cut_plates)} Y-cut plates (dual)\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Y-cut plates: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            x_cut_plates = create_x_cut_plates(foil, cutting_plan, boat_name, plate_thickness,
                                              bounding_margin, hex_radius, hex_wall_thickness,
                                              pattern_type, hole_diameter, hole_spacing, stock_cutout)
            all_plates.extend(x_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(x_cut_plates)} X-cut plates (dual)\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create X-cut plates: {str(e)}\n")
        
        # Import foil shell if available
        shell = import_foil_shell(boat_name)
        
        FreeCADGui.updateGui()
        FreeCAD.ActiveDocument.recompute()
        
        # Export plates individually for 3D printing
        if all_plates:
            export_plates_for_printing(all_plates, boat_name)
        
        # Summary
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("PLATE CREATION COMPLETE:\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        if z_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(z_cut_plates)} Z-cut plates (dual half-thickness)\n")
        if z_support_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(z_support_plates)} Z-support plates\n")
        if x_support_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(x_support_plates)} X-support plates (50mm spacing)\n")
        if y_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(y_cut_plates)} Y-cut plates (dual half-thickness)\n")
        if x_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(x_cut_plates)} X-cut plates (dual half-thickness)\n")
        
        FreeCAD.Console.PrintMessage(f"  Total: {len(all_plates)} plates created\n")
        FreeCAD.Console.PrintMessage(f"  Pattern used: {pattern_type}\n")
        
        if shell:
            FreeCAD.Console.PrintMessage(f"  Foil shell imported and visible\n")
        
        if stock_cutout:
            FreeCAD.Console.PrintMessage(f"  Stock cutout: APPLIED to all plates\n")
        
        if cutting_plan:
            z_cuts = cutting_plan['cutting_plan']['z_cuts']
            x_cuts = cutting_plan['cutting_plan']['x_cuts']
            FreeCAD.Console.PrintMessage(f"  Target segments: {(len(z_cuts)+1)*2*(len(x_cuts)+1)}\n")
        
    else:
        FreeCAD.Console.PrintError("Import failed!\n")

# Main execution
if __name__ == "__main__":
    # UI setup only
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument()
    
    # Call business logic with parameters
    run_plate_creation(
        boat_name="MackenSea",
        plate_thickness=6.0,
        support_plate_thickness=3.0,
        plate_spacing=150.0,
        bounding_margin=10.0,
        hex_radius=5.0,
        hex_wall_thickness=3.0,
        pattern_type='solid',  # 'hex', 'circle', or 'solid'
        hole_diameter=10.0,
        hole_spacing=25.0
    )