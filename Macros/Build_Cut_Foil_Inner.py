import FreeCAD
import FreeCADGui
import Import
import Part
import json
import os
import time
import sys

# Foil Mold Importer for Boat Manufacturing - FreeCAD 1.1 Compatible
# VERSION: 3.1.2 - REFACTORED

print("=== FREECAD MOLD IMPORTER VERSION 3.1.2 - REFACTORED ===")
FreeCAD.Console.PrintMessage("=== FREECAD MOLD IMPORTER VERSION 3.1.2 - REFACTORED ===\n")

# System configuration (not user parameters)
helpers_path = os.path.expanduser("~/Rudder_Code/helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)

try:
    import hex_array_helper
    FreeCAD.Console.PrintMessage("Successfully imported hex_array_helper module\n")
except ImportError as e:
    FreeCAD.Console.PrintError(f"Could not import hex_array_helper: {str(e)}\n")
    hex_array_helper = None

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

def create_z_cut_plates(foil_object, cutting_plan, boat_name, plate_thickness, bounding_margin, hex_radius, hex_wall_thickness):
    """Create Z-cut plates (horizontal - XY plane)"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Z-Cut Plates ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        FreeCAD.Console.PrintMessage(f"Foil bounding box: X({foil_bbox.XMin:.2f} to {foil_bbox.XMax:.2f}), "
                                   f"Y({foil_bbox.YMin:.2f} to {foil_bbox.YMax:.2f}), "
                                   f"Z({foil_bbox.ZMin:.2f} to {foil_bbox.ZMax:.2f})\n")
        
        working_shape = prepare_foil_for_boolean(foil_object)
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        
        FreeCAD.Console.PrintMessage(f"Creating {len(z_cuts)} Z-cut plates ({plate_thickness}mm thick)...\n")
        FreeCADGui.updateGui()
        
        for i, z_pos in enumerate(z_cuts):
            try:
                FreeCAD.Console.PrintMessage(f"  [Plate {i+1}/{len(z_cuts)}] Starting Z-cut plate at Z={z_pos:.2f}...\n")
                FreeCADGui.updateGui()
                
                plate_x_size = (foil_bbox.XMax - foil_bbox.XMin) + 2 * bounding_margin
                plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                
                if hex_array_helper:
                    FreeCAD.Console.PrintMessage(f"    Creating hex perforation pattern...\n")
                    FreeCADGui.updateGui()
                    
                    hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                        length=plate_x_size,
                        width=plate_y_size,
                        thickness=plate_thickness,
                        hex_radius=hex_radius,
                        wall_thickness=hex_wall_thickness
                    )
                    
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Z_CutPlate_{i+1}")
                    plate.Shape = hex_shape
                    
                    FreeCAD.Console.PrintMessage(f"    Hex pattern: {hex_info['total_hexagons']} hexagons\n")
                else:
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"Z_CutPlate_{i+1}")
                    plate.Length = plate_x_size
                    plate.Width = plate_y_size  
                    plate.Height = plate_thickness
                    FreeCAD.Console.PrintMessage(f"    Created solid plate\n")
                
                plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = z_pos - plate_thickness / 2
                
                plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                
                FreeCAD.Console.PrintMessage(f"    Performing boolean intersection...\n")
                FreeCADGui.updateGui()
                
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
                        FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
                    else:
                        FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
                except Exception as e:
                    FreeCAD.Console.PrintError(f"    Boolean operation failed: {str(e)}\n")
                    raise
                
                plate.Label = f"{boat_name}_Z_CutPlate_{i+1}_at_Z{z_pos:.1f}"
                plates.append(plate)
                
                FreeCAD.Console.PrintMessage(f"  [Plate {i+1}/{len(z_cuts)}] Completed\n")
                
                # Breathing room after each plate
                FreeCADGui.updateGui()
                FreeCAD.ActiveDocument.recompute()
                time.sleep(0.2)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"FATAL: Failed creating Z-cut plate {i+1}: {str(e)}\n")
                raise
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_z_cut_plates failed: {str(e)}\n")
        raise
    
    return plates

def create_z_support_plates(foil_object, cutting_plan, boat_name, support_plate_thickness, plate_spacing, bounding_margin, hex_radius, hex_wall_thickness):
    """Create Z support plates (3mm thick)"""
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
                
                if hex_array_helper:
                    hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                        length=plate_x_size,
                        width=plate_y_size,
                        thickness=support_plate_thickness,
                        hex_radius=hex_radius,
                        wall_thickness=hex_wall_thickness
                    )
                    
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Z_SupportPlate_{i+1}")
                    plate.Shape = hex_shape
                    FreeCAD.Console.PrintMessage(f"    Created hex support plate\n")
                else:
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"Z_SupportPlate_{i+1}")
                    plate.Length = plate_x_size
                    plate.Width = plate_y_size  
                    plate.Height = support_plate_thickness
                    FreeCAD.Console.PrintMessage(f"    Created solid support plate\n")
                
                plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = z_pos - support_plate_thickness / 2
                
                plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
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

def create_x_support_plates(foil_object, cutting_plan, boat_name, support_plate_thickness, x_support_spacing, bounding_margin, hex_radius, hex_wall_thickness):
    """Create X support plates (3mm thick) at 50mm spacing"""
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
                
                if hex_array_helper:
                    hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                        length=plate_z_size,
                        width=plate_y_size,
                        thickness=support_plate_thickness,
                        hex_radius=hex_radius,
                        wall_thickness=hex_wall_thickness
                    )
                    
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"X_SupportPlate_{i+1}")
                    plate.Shape = hex_shape
                    
                    rotation = FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90)
                    plate.Placement.Rotation = rotation
                    
                    FreeCAD.Console.PrintMessage(f"    Created hex X-support plate\n")
                else:
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"X_SupportPlate_{i+1}")
                    plate.Length = support_plate_thickness
                    plate.Width = plate_y_size
                    plate.Height = plate_z_size
                    FreeCAD.Console.PrintMessage(f"    Created solid X-support plate\n")
                
                plate_x_center = x_pos - support_plate_thickness / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 - plate_z_size / 2
                
                if hex_array_helper:
                    current_placement = plate.Placement
                    current_placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center + plate_z_size)
                    plate.Placement = current_placement
                else:
                    plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
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

def create_y_cut_plate(foil_object, cutting_plan, boat_name, plate_thickness, bounding_margin, hex_wall_thickness):
    """Create Y-cut plate (centerline - XZ plane) at Y=0"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Y-Cut Plate ===\n")
        FreeCAD.Console.PrintMessage("Creating Y-cut plate at Y=0...\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        plate_x_size = (foil_bbox.XMax - foil_bbox.XMin) + 2 * bounding_margin
        plate_z_size = (foil_bbox.ZMax - foil_bbox.ZMin) + 2 * bounding_margin
        
        if hex_array_helper:
            hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                length=plate_x_size,
                width=plate_z_size,
                thickness=plate_thickness,
                hex_radius=8.0,  # Larger hex since this prints flat
                wall_thickness=hex_wall_thickness
            )
            
            plate = FreeCAD.ActiveDocument.addObject("Part::Feature", "Y_CutPlate_Center")
            plate.Shape = hex_shape
            
            rotation = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 90)
            plate.Placement.Rotation = rotation
            
            FreeCAD.Console.PrintMessage(f"  Y-Cut Plate: {plate_x_size:.1f} × {plate_thickness:.1f} × {plate_z_size:.1f} mm\n")
            FreeCAD.Console.PrintMessage(f"    Hex pattern: {hex_info['total_hexagons']} hexagons (8mm radius)\n")
        else:
            plate = FreeCAD.ActiveDocument.addObject("Part::Box", "Y_CutPlate_Center")
            plate.Length = plate_x_size
            plate.Width = plate_thickness
            plate.Height = plate_z_size
            FreeCAD.Console.PrintMessage(f"  Y-Cut Plate: Solid plate at Y=0\n")
        
        plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
        plate_y_center = 0 - plate_thickness / 2
        plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 - plate_z_size / 2
        
        current_placement = plate.Placement
        current_placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
        plate.Placement = current_placement
        
        try:
            shaped = plate.Shape.common(working_shape)
            if shaped.Volume > 0:
                plate.Shape = shaped
                FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
            else:
                FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"    Boolean operation failed: {str(e)}\n")
            raise
        
        plate.Label = f"{boat_name}_Y_CutPlate_Center_at_Y0"
        plates.append(plate)
        
        FreeCAD.Console.PrintMessage(f"  Y-Cut Plate Completed\n")
        
        # Breathing room after plate
        FreeCADGui.updateGui()
        FreeCAD.ActiveDocument.recompute()
        time.sleep(0.2)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_y_cut_plate failed: {str(e)}\n")
        raise
    
    return plates

def create_x_cut_plates(foil_object, cutting_plan, boat_name, plate_thickness, bounding_margin, hex_radius, hex_wall_thickness):
    """Create X-cut plates (vertical - YZ plane)"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating X-Cut Plates ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        
        FreeCAD.Console.PrintMessage(f"Creating {len(x_cuts)} X-cut plates ({plate_thickness}mm thick)...\n")
        FreeCADGui.updateGui()
        
        for i, x_pos in enumerate(x_cuts):
            try:
                FreeCAD.Console.PrintMessage(f"  [Plate {i+1}/{len(x_cuts)}] Starting X-cut plate at X={x_pos:.2f}...\n")
                FreeCADGui.updateGui()
                
                plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                plate_z_size = (foil_bbox.ZMax - foil_bbox.ZMin) + 2 * bounding_margin
                
                if hex_array_helper:
                    hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                        length=plate_z_size,
                        width=plate_y_size,
                        thickness=plate_thickness,
                        hex_radius=hex_radius,
                        wall_thickness=hex_wall_thickness
                    )
                    
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"X_CutPlate_{i+1}")
                    plate.Shape = hex_shape
                    
                    rotation = FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90)
                    plate.Placement.Rotation = rotation
                    
                    FreeCAD.Console.PrintMessage(f"    Hex pattern: {hex_info['total_hexagons']} hexagons\n")
                else:
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"X_CutPlate_{i+1}")
                    plate.Length = plate_thickness
                    plate.Width = plate_y_size
                    plate.Height = plate_z_size
                    FreeCAD.Console.PrintMessage(f"    Created solid plate\n")
                
                plate_x_center = x_pos - plate_thickness / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 - plate_z_size / 2
                
                if hex_array_helper:
                    current_placement = plate.Placement
                    current_placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center + plate_z_size)
                    plate.Placement = current_placement
                else:
                    plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
                        FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
                    else:
                        FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
                except Exception as e:
                    FreeCAD.Console.PrintError(f"    Boolean operation failed: {str(e)}\n")
                    raise
                
                plate.Label = f"{boat_name}_X_CutPlate_{i+1}_at_X{x_pos:.1f}"
                plates.append(plate)
                
                FreeCAD.Console.PrintMessage(f"  [Plate {i+1}/{len(x_cuts)}] Completed\n")
                
                # Breathing room after each plate
                FreeCADGui.updateGui()
                FreeCAD.ActiveDocument.recompute()
                time.sleep(0.2)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"FATAL: Failed creating X-cut plate {i+1}: {str(e)}\n")
                raise
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_x_cut_plates failed: {str(e)}\n")
        raise
    
    return plates

def merge_all_plates(boat_name):
    """Merge all plates into a single unified structure"""
    try:
        FreeCAD.Console.PrintMessage("\n=== Merging All Plates ===\n")
        FreeCADGui.updateGui()
        
        # Find all plate objects
        plates_to_merge = []
        for obj in FreeCAD.ActiveDocument.Objects:
            if any(x in obj.Label for x in ['_CutPlate_', '_SupportPlate_', '_Support_']):
                plates_to_merge.append(obj)
                FreeCAD.Console.PrintMessage(f"  Found plate: {obj.Label}\n")
        
        if not plates_to_merge:
            FreeCAD.Console.PrintError("No plates found to merge!\n")
            return None
        
        FreeCAD.Console.PrintMessage(f"\nMerging {len(plates_to_merge)} plates...\n")
        FreeCADGui.updateGui()
        
        # Start with first plate shape
        merged_shape = plates_to_merge[0].Shape
        
        # Fuse with remaining plates
        for i, plate in enumerate(plates_to_merge[1:], 1):
            FreeCAD.Console.PrintMessage(f"  Merging plate {i+1}/{len(plates_to_merge)}...\n")
            FreeCADGui.updateGui()
            
            try:
                merged_shape = merged_shape.fuse(plate.Shape)
            except Exception as e:
                FreeCAD.Console.PrintError(f"    Error merging {plate.Label}: {str(e)}\n")
            
            # Breathing room every 5 plates
            if i % 5 == 0:
                FreeCAD.ActiveDocument.recompute()
                time.sleep(0.2)
        
        # Create merged object
        merged_plates = FreeCAD.ActiveDocument.addObject("Part::Feature", "MergedPlates")
        merged_plates.Shape = merged_shape
        merged_plates.Label = f"{boat_name}_MergedPlates_Assembly"
        
        FreeCAD.Console.PrintMessage(f"\n✅ Successfully merged {len(plates_to_merge)} plates\n")
        FreeCAD.Console.PrintMessage(f"  Merged volume: {merged_shape.Volume:.2f} mm³\n")
        
        # Hide individual plates after merging
        for plate in plates_to_merge:
            if hasattr(plate, 'ViewObject') and plate.ViewObject:
                plate.ViewObject.Visibility = False
        
        FreeCAD.ActiveDocument.recompute()
        return merged_plates
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: merge_all_plates failed: {str(e)}\n")
        raise

def export_merged_plates(merged_plates, boat_name):
    """Export merged plates as STL and STEP files"""
    try:
        FreeCAD.Console.PrintMessage("\n=== Exporting Merged Plates ===\n")
        FreeCADGui.updateGui()
        
        # Construct export paths
        boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
        output_folder = f"{boat_folder}/output"
        cut_foil_folder = f"{output_folder}/cut_foil"
        
        # Create filenames
        stl_file = f"{cut_foil_folder}/merged_inner_plates.stl"
        step_file = f"{cut_foil_folder}/merged_inner_plates.step"
        
        # Export as STL
        FreeCAD.Console.PrintMessage(f"  Exporting STL to: {stl_file}\n")
        FreeCADGui.updateGui()
        
        try:
            import Mesh
            Mesh.export([merged_plates], stl_file)
            FreeCAD.Console.PrintMessage(f"    ✅ STL export successful\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"    ❌ STL export failed: {str(e)}\n")
        
        # Export as STEP
        FreeCAD.Console.PrintMessage(f"  Exporting STEP to: {step_file}\n")
        FreeCADGui.updateGui()
        
        try:
            Import.export([merged_plates], step_file)
            FreeCAD.Console.PrintMessage(f"    ✅ STEP export successful\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"    ❌ STEP export failed: {str(e)}\n")
        
        FreeCAD.Console.PrintMessage(f"\nExports complete:\n")
        FreeCAD.Console.PrintMessage(f"  - STL: merged_inner_plates.stl\n")
        FreeCAD.Console.PrintMessage(f"  - STEP: merged_inner_plates.step\n")
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: export_merged_plates failed: {str(e)}\n")
        raise

def run_plate_creation(boat_name="MackenSea", 
                      plate_thickness=6.0,
                      support_plate_thickness=3.0,
                      plate_spacing=150.0,
                      bounding_margin=10.0,
                      hex_radius=5.0,
                      hex_wall_thickness=3.0):
    """Main business logic for plate creation
    
    Args:
        boat_name: Name of the boat (determines file paths)
        plate_thickness: Thickness of cutting plates in mm
        support_plate_thickness: Thickness of support plates in mm  
        plate_spacing: Target spacing between plates in mm
        bounding_margin: Margin around foil for plates in mm
        hex_radius: Radius of hexagonal perforations in mm
        hex_wall_thickness: Wall thickness between hexagons in mm
    """
    cutting_plan, foil = import_foil(boat_name)
    
    if cutting_plan and foil:
        FreeCAD.Console.PrintMessage("Successfully imported cutting plan and foil!\n")
        FreeCAD.Console.PrintMessage(f"Foil object: {foil.Label}\n")
        configure_display(foil, cutting_plan)
        
        all_plates = []
        
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("CREATING CUTTING AND SUPPORT PLATES\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        z_cut_plates = []
        z_support_plates = []
        x_support_plates = []
        y_cut_plates = []
        x_cut_plates = []
        
        try:
            z_cut_plates = create_z_cut_plates(foil, cutting_plan, boat_name, plate_thickness, 
                                              bounding_margin, hex_radius, hex_wall_thickness)
            all_plates.extend(z_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(z_cut_plates)} Z-cut plates\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Z-cut plates: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            z_support_plates = create_z_support_plates(foil, cutting_plan, boat_name, 
                                                      support_plate_thickness, plate_spacing,
                                                      bounding_margin, hex_radius, hex_wall_thickness)
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
                                                      bounding_margin, hex_radius, hex_wall_thickness)
            all_plates.extend(x_support_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(x_support_plates)} X-support plates\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create X-support plates: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            y_cut_plates = create_y_cut_plate(foil, cutting_plan, boat_name, plate_thickness,
                                             bounding_margin, hex_wall_thickness)
            all_plates.extend(y_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(y_cut_plates)} Y-cut plate\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Y-cut plate: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            x_cut_plates = create_x_cut_plates(foil, cutting_plan, boat_name, plate_thickness,
                                              bounding_margin, hex_radius, hex_wall_thickness)
            all_plates.extend(x_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(x_cut_plates)} X-cut plates\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create X-cut plates: {str(e)}\n")
        
        # Merge all plates into single assembly
        if all_plates:
            try:
                merged = merge_all_plates(boat_name)
                if merged:
                    FreeCAD.Console.PrintMessage(f"✅ Created merged plate assembly\n")
                    
                    # Export merged plates
                    export_merged_plates(merged, boat_name)
                    
            except Exception as e:
                FreeCAD.Console.PrintError(f"❌ Failed to merge plates: {str(e)}\n")
        
        FreeCAD.ActiveDocument.recompute()
        
        # Summary
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("PLATE CREATION COMPLETE:\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        if z_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(z_cut_plates)} Z-cut plates\n")
        if z_support_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(z_support_plates)} Z-support plates\n")
        if x_support_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(x_support_plates)} X-support plates (50mm spacing)\n")
        if y_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(y_cut_plates)} Y-cut plate\n")
        if x_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(x_cut_plates)} X-cut plates\n")
        
        FreeCAD.Console.PrintMessage(f"  Total: {len(all_plates)} plates created\n")
        
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
        hex_wall_thickness=3.0
    )