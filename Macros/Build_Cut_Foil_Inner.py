import FreeCAD
import FreeCADGui
import Import
import Part
import json
import os
import time
import sys

# Compatible with FreeCAD 1.1
# Foil Mold Importer and Visualizer for Boat Manufacturing
# VERSION: 3.1.2 - REFACTORED WITH SEPARATED PLATE CREATION

print("=== FREECAD MOLD IMPORTER VERSION 3.1.2 - REFACTORED ===")
FreeCAD.Console.PrintMessage("=== FREECAD MOLD IMPORTER VERSION 3.1.2 - REFACTORED ===\n")

# Add helper module to path and import
boat_name = "MackenSea"
helpers_path = os.path.expanduser("~/Rudder_Code/helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)

try:
    import hex_array_helper
    FreeCAD.Console.PrintMessage("Successfully imported hex_array_helper module\n")
except ImportError as e:
    FreeCAD.Console.PrintError(f"Could not import hex_array_helper: {str(e)}\n")
    hex_array_helper = None

# Parameters
plate_thickness = 6.0  # mm - for cutting plates
support_plate_thickness = 3.0  # mm - for support plates (0.5 * cutting plate thickness)
plate_spacing = 150.0  # mm - target spacing between all plates
bounding_margin = 10.0  # mm
hole_diameter = 4.0  # mm
hole_spacing = 6.0  # mm (center to center)

# Hex perforation parameters
hex_radius = 5.0  # mm - reduced from 8mm for better bridging (except Y-plate)
hex_wall_thickness = 3.0  # mm - minimum wall between hexagons

# Construct file paths
boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
output_folder = f"{boat_folder}/output"
cut_foil_folder = f"{output_folder}/cut_foil"

cutting_plan_file = f"{cut_foil_folder}/{boat_name}_Cut_Foil_cutting_plan.json"
foil_step_file = f"{cut_foil_folder}/{boat_name}_Cut_Foil.step"

def import_foil():
    """Import the cutting plan JSON and foil STEP file"""
    
    # Check if files exist
    if not os.path.exists(cutting_plan_file):
        FreeCAD.Console.PrintError(f"Cutting plan file not found: {cutting_plan_file}\n")
        return None, None
        
    if not os.path.exists(foil_step_file):
        FreeCAD.Console.PrintError(f"Foil STEP file not found: {foil_step_file}\n")
        return None, None
    
    # Load cutting plan JSON
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
    
    # Import foil STEP file
    try:
        Import.insert(foil_step_file, FreeCAD.ActiveDocument.Name)
        FreeCAD.Console.PrintMessage(f"Imported foil STEP file: {foil_step_file}\n")
        
        # Get the imported object (should be the last object added)
        foil_object = FreeCAD.ActiveDocument.Objects[-1]
        foil_object.Label = f"{boat_name}_Foil"
        
        FreeCAD.ActiveDocument.recompute()
        
        # Allow time for object to fully initialize
        time.sleep(0.5)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error importing foil STEP file: {str(e)}\n")
        return cutting_plan, None
    
    return cutting_plan, foil_object

def configure_display(foil_object, cutting_plan):
    """Configure FreeCAD display for optimal viewing of the foil and cutting planes"""
    
    try:
        # Ensure we have a GUI
        if not hasattr(FreeCADGui, 'ActiveDocument') or not FreeCADGui.ActiveDocument:
            FreeCAD.Console.PrintWarning("No GUI available - skipping display configuration\n")
            return
            
        # Set transparency - FreeCAD 1.1 compatible
        try:
            if hasattr(foil_object, 'ViewObject') and foil_object.ViewObject:
                foil_object.ViewObject.Transparency = 70
                FreeCAD.ActiveDocument.recompute()
                FreeCADGui.updateGui()
                FreeCAD.Console.PrintMessage("Set foil transparency to 70%\n")
            else:
                FreeCAD.Console.PrintWarning("ViewObject not available for transparency setting\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error setting transparency: {str(e)}\n")
        
        # Configure view
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
            else:
                FreeCAD.Console.PrintWarning("No active view available\n")
                
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error configuring view: {str(e)}\n")
        
        # Print cutting information to console
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("CUTTING PLAN SUMMARY:\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        
        FreeCAD.Console.PrintMessage(f"Z-CUTS (horizontal, need plates with tabs):\n")
        for i, z_pos in enumerate(z_cuts):
            FreeCAD.Console.PrintMessage(f"  Cut {i+1}: Z = {z_pos:.2f} mm\n")
            
        FreeCAD.Console.PrintMessage(f"\nY-CUT (centerline):\n")
        FreeCAD.Console.PrintMessage(f"  Cut 1: Y = 0.00 mm (centerline)\n")
        
        FreeCAD.Console.PrintMessage(f"\nX-CUTS (vertical, clean cuts only):\n")
        for i, x_pos in enumerate(x_cuts):
            FreeCAD.Console.PrintMessage(f"  Cut {i+1}: X = {x_pos:.2f} mm\n")
            
        FreeCAD.Console.PrintMessage(f"\nTotal segments: {len(z_cuts)+1} × 2 × {len(x_cuts)+1} = {(len(z_cuts)+1)*2*(len(x_cuts)+1)} pieces\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        FreeCAD.Console.PrintMessage("Display configuration complete\n")
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error configuring display: {str(e)}\n")

def prepare_foil_for_boolean(foil_object):
    """Ensure foil is a solid for boolean operations"""
    
    # Check if foil has solids
    num_solids = len(foil_object.Shape.Solids)
    
    if num_solids == 0:
        FreeCAD.Console.PrintMessage("Foil has no solids - attempting to create solid...\n")
        try:
            # Check if we have shells
            num_shells = len(foil_object.Shape.Shells)
            
            if num_shells > 0:
                # Try to make solid from first shell
                solid_shape = Part.makeSolid(foil_object.Shape.Shells[0])
                if len(solid_shape.Solids) > 0:
                    FreeCAD.Console.PrintMessage("Successfully created solid from foil shell!\n")
                    return solid_shape
                else:
                    FreeCAD.Console.PrintMessage("makeSolid failed to create proper solid\n")
            else:
                FreeCAD.Console.PrintMessage("No shells found to convert to solid\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error making solid: {str(e)}\n")
    
    return foil_object.Shape

def calculate_support_plate_positions(z_cuts, foil_bbox):
    print("Calculate positions for support plates if needed\n")
    
    support_positions = []
    
    # Get Z extent of foil
    z_min = foil_bbox.ZMin
    z_max = foil_bbox.ZMax
    
    # Sort z_cuts for processing
    z_cuts_sorted = sorted(z_cuts)
    
    # Add z_min and z_max to create complete segments
    all_boundaries = [z_min] + z_cuts_sorted + [z_max]
    
    # For each segment between boundaries, add support plates
    for i in range(len(all_boundaries) - 1):
        segment_start = all_boundaries[i]
        segment_end = all_boundaries[i + 1]
        segment_length = segment_end - segment_start
        
        # Calculate number of support plates needed in this segment
        num_supports = int(segment_length / plate_spacing)
        
        # If we need supports and there's room
        if num_supports > 1:  # >1 because we don't count the boundaries
            # Distribute supports evenly within segment
            actual_spacing = segment_length / (num_supports + 1)
            
            for j in range(1, num_supports + 1):
                support_z = segment_start + (j * actual_spacing)
                
                # Don't place supports too close to cutting planes (within 10mm)
                too_close = False
                for cut_z in z_cuts_sorted:
                    if abs(support_z - cut_z) < 10:
                        too_close = True
                        break
                
                if not too_close:
                    print("Extra Z support will be added: ", support_z)
                    support_positions.append(support_z)
    
    return sorted(support_positions)

def create_z_cut_plates(foil_object, cutting_plan):
    """Create Z-cut plates (horizontal plates - XY plane) with hex perforation and boolean shaping"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Z-Cut Plates ===\n")
        
        foil_bbox = foil_object.Shape.BoundBox
        FreeCAD.Console.PrintMessage(f"Foil bounding box: X({foil_bbox.XMin:.2f} to {foil_bbox.XMax:.2f}), "
                                   f"Y({foil_bbox.YMin:.2f} to {foil_bbox.YMax:.2f}), "
                                   f"Z({foil_bbox.ZMin:.2f} to {foil_bbox.ZMax:.2f})\n")
        
        working_shape = prepare_foil_for_boolean(foil_object)
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        
        FreeCAD.Console.PrintMessage(f"Creating {len(z_cuts)} Z-cut plates (6mm thick) for cutting...\n")
        
        for i, z_pos in enumerate(z_cuts):
            try:
                plate_x_size = (foil_bbox.XMax - foil_bbox.XMin) + 2 * bounding_margin
                plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                
                # Create hex-perforated plate using helper module
                if hex_array_helper:
                    hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                        length=plate_x_size,
                        width=plate_y_size,
                        thickness=plate_thickness,
                        hex_radius=hex_radius,
                        wall_thickness=hex_wall_thickness
                    )
                    
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Z_CutPlate_{i+1}")
                    plate.Shape = hex_shape
                    
                    FreeCAD.Console.PrintMessage(f"  Z-Cut Plate {i+1}: {plate_x_size:.1f} × {plate_y_size:.1f} × {plate_thickness:.1f} mm at Z={z_pos:.2f}\n")
                    FreeCAD.Console.PrintMessage(f"    Hex pattern: {hex_info['total_hexagons']} hexagons (5mm radius)\n")
                else:
                    FreeCAD.Console.PrintWarning("Hex module not available - creating solid plate\n")
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"Z_CutPlate_{i+1}")
                    plate.Length = plate_x_size
                    plate.Width = plate_y_size  
                    plate.Height = plate_thickness
                    FreeCAD.Console.PrintMessage(f"  Z-Cut Plate {i+1}: {plate_x_size:.1f} × {plate_y_size:.1f} × {plate_thickness:.1f} mm at Z={z_pos:.2f} (SOLID)\n")
                
                # Position plate
                plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = z_pos - plate_thickness / 2
                
                plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                
                # Boolean operation to shape Z-plate to foil cross-section
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
                        FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
                    else:
                        FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
                except Exception as e:
                    FreeCAD.Console.PrintError(f"    Error shaping plate: {str(e)}\n")
                
                plate.Label = f"{boat_name}_Z_CutPlate_{i+1}_at_Z{z_pos:.1f}"
                plates.append(plate)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error creating Z-cut plate {i+1}: {str(e)}\n")
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error in create_z_cut_plates: {str(e)}\n")
    
    return plates

def create_z_support_plates(foil_object, cutting_plan):
    """Create Z support plates (3mm thick) for printing support"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Z-Support Plates ===\n")
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        # Calculate support plate positions
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        support_z_positions = calculate_support_plate_positions(z_cuts, foil_bbox)
        FreeCAD.Console.PrintMessage(f"Calculated {len(support_z_positions)} support plate positions at ~50mm spacing\n")
        FreeCAD.Console.PrintMessage(f"Creating {len(support_z_positions)} Z-support plates (3mm thick) for printing support...\n")
        
        for i, z_pos in enumerate(support_z_positions):
            try:
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
                    
                    FreeCAD.Console.PrintMessage(f"  Z-Support {i+1}: 3mm thick at Z={z_pos:.2f}\n")
                else:
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"Z_SupportPlate_{i+1}")
                    plate.Length = plate_x_size
                    plate.Width = plate_y_size  
                    plate.Height = support_plate_thickness
                    FreeCAD.Console.PrintMessage(f"  Z-Support {i+1}: 3mm thick at Z={z_pos:.2f} (SOLID)\n")
                
                # Position and shape
                plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = z_pos - support_plate_thickness / 2
                
                plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                
                # Boolean operation
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
                except Exception as e:
                    FreeCAD.Console.PrintError(f"    Error shaping support plate: {str(e)}\n")
                
                plate.Label = f"{boat_name}_Z_Support_{i+1}_at_Z{z_pos:.1f}"
                
                # Set transparency for support plates to distinguish them
                if hasattr(plate, 'ViewObject') and plate.ViewObject:
                    plate.ViewObject.Transparency = 85
                
                plates.append(plate)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error creating Z-support plate {i+1}: {str(e)}\n")
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error in create_z_support_plates: {str(e)}\n")
    
    return plates

def create_y_cut_plate(foil_object, cutting_plan):
    """Create Y-cut plate (centerline plate - XZ plane) at Y=0"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Y-Cut Plate ===\n")
        FreeCAD.Console.PrintMessage("Creating Y-cut plate (centerline) at Y=0...\n")
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        # For Y-cut at centerline, create XZ plane plate
        plate_x_size = (foil_bbox.XMax - foil_bbox.XMin) + 2 * bounding_margin
        plate_z_size = (foil_bbox.ZMax - foil_bbox.ZMin) + 2 * bounding_margin
        
        # Create hex-perforated plate using helper module
        if hex_array_helper:
            # For Y-plate, use larger hex since it prints flat
            hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                length=plate_x_size,
                width=plate_z_size,
                thickness=plate_thickness,
                hex_radius=8.0,  # Larger hex (8mm) since this prints flat
                wall_thickness=hex_wall_thickness
            )
            
            plate = FreeCAD.ActiveDocument.addObject("Part::Feature", "Y_CutPlate_Center")
            plate.Shape = hex_shape
            
            # Rotate the plate 90 degrees around X axis to make it vertical on XZ plane
            rotation = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 90)
            plate.Placement.Rotation = rotation
            
            FreeCAD.Console.PrintMessage(f"  Y-Cut Plate (Center): {plate_x_size:.1f} × {plate_thickness:.1f} × {plate_z_size:.1f} mm at Y=0\n")
            FreeCAD.Console.PrintMessage(f"    Hex pattern: {hex_info['total_hexagons']} hexagons (8mm radius - prints flat)\n")
        else:
            FreeCAD.Console.PrintWarning("Hex module not available - creating solid Y-plate\n")
            plate = FreeCAD.ActiveDocument.addObject("Part::Box", "Y_CutPlate_Center")
            plate.Length = plate_x_size
            plate.Width = plate_thickness
            plate.Height = plate_z_size
            FreeCAD.Console.PrintMessage(f"  Y-Cut Plate (Center): {plate_x_size:.1f} × {plate_thickness:.1f} × {plate_z_size:.1f} mm at Y=0 (SOLID)\n")
        
        # Position plate - center it on foil XZ, position at Y=0
        plate_x_center = (foil_bbox.XMin + foil_bbox.XMax) / 2 - plate_x_size / 2
        plate_y_center = 0 - plate_thickness / 2  # Centered at Y=0
        plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 - plate_z_size / 2  # Fixed centering
        
        # Apply position after rotation
        current_placement = plate.Placement
        current_placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
        plate.Placement = current_placement
        
        # Boolean operation to shape Y-plate to foil profile
        try:
            shaped = plate.Shape.common(working_shape)
            if shaped.Volume > 0:
                plate.Shape = shaped
                FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
            else:
                FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"    Error shaping plate: {str(e)}\n")
        
        plate.Label = f"{boat_name}_Y_CutPlate_Center_at_Y0"
        plates.append(plate)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error in create_y_cut_plate: {str(e)}\n")
    
    return plates

def create_x_cut_plates(foil_object, cutting_plan):
    """Create X-cut plates (vertical plates - YZ plane) with hex perforation and boolean shaping"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating X-Cut Plates ===\n")
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        
        FreeCAD.Console.PrintMessage(f"Creating {len(x_cuts)} X-cut plates (6mm thick) for cutting...\n")
        
        for i, x_pos in enumerate(x_cuts):
            try:
                # For X-cuts, create YZ plane plates
                plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                plate_z_size = (foil_bbox.ZMax - foil_bbox.ZMin) + 2 * bounding_margin
                
                # Create hex-perforated plate using helper module
                if hex_array_helper:
                    # For X-plates, we use z_size as length and y_size as width for the hex pattern
                    hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                        length=plate_z_size,  # Height becomes length for vertical plate
                        width=plate_y_size,   # Width remains width
                        thickness=plate_thickness,
                        hex_radius=hex_radius,
                        wall_thickness=hex_wall_thickness
                    )
                    
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"X_CutPlate_{i+1}")
                    plate.Shape = hex_shape
                    
                    # Rotate the plate 90 degrees around Y axis to make it vertical
                    rotation = FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90)
                    plate.Placement.Rotation = rotation
                    
                    FreeCAD.Console.PrintMessage(f"  X-Cut Plate {i+1}: {plate_thickness:.1f} × {plate_y_size:.1f} × {plate_z_size:.1f} mm at X={x_pos:.2f}\n")
                    FreeCAD.Console.PrintMessage(f"    Hex pattern: {hex_info['total_hexagons']} hexagons (5mm radius)\n")
                else:
                    FreeCAD.Console.PrintWarning("Hex module not available - creating solid plate\n")
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"X_CutPlate_{i+1}")
                    plate.Length = plate_thickness
                    plate.Width = plate_y_size
                    plate.Height = plate_z_size
                    FreeCAD.Console.PrintMessage(f"  X-Cut Plate {i+1}: {plate_thickness:.1f} × {plate_y_size:.1f} × {plate_z_size:.1f} mm at X={x_pos:.2f} (SOLID)\n")
                
                # Position plate
                plate_x_center = x_pos - plate_thickness / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 - plate_z_size / 2
                
                # Apply position after rotation if hex was used
                if hex_array_helper:
                    current_placement = plate.Placement
                    current_placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center + plate_z_size)
                    plate.Placement = current_placement
                else:
                    plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                
                # Boolean operation to shape X-plate to foil profile
                try:
                    shaped = plate.Shape.common(working_shape)
                    if shaped.Volume > 0:
                        plate.Shape = shaped
                        FreeCAD.Console.PrintMessage(f"    Shaped to foil - Volume: {shaped.Volume:.2f} mm³\n")
                    else:
                        FreeCAD.Console.PrintWarning(f"    Warning: No intersection with foil\n")
                except Exception as e:
                    FreeCAD.Console.PrintError(f"    Error shaping plate: {str(e)}\n")
                
                plate.Label = f"{boat_name}_X_CutPlate_{i+1}_at_X{x_pos:.1f}"
                plates.append(plate)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error creating X-cut plate {i+1}: {str(e)}\n")
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error in create_x_cut_plates: {str(e)}\n")
    
    return plates

##########################################################################################
# Execute the import
if __name__ == "__main__":
    # Ensure we have an active document
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument()
    
    cutting_plan, foil = import_foil()
    
    if cutting_plan and foil:
        FreeCAD.Console.PrintMessage("Successfully imported cutting plan and foil!\n")
        FreeCAD.Console.PrintMessage(f"Foil object: {foil.Label}\n")
        configure_display(foil, cutting_plan)
        
        # Create cutting and support plates with separated function calls
        all_plates = []
        
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("CREATING CUTTING AND SUPPORT PLATES\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        # Initialize all plate lists to empty
        z_cut_plates = []
        z_support_plates = []
        y_cut_plates = []
        x_cut_plates = []
        
        # Create Z-cut plates
        try:
            z_cut_plates = create_z_cut_plates(foil, cutting_plan)
            all_plates.extend(z_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(z_cut_plates)} Z-cut plates\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Z-cut plates: {str(e)}\n")
        
        # Create Z-support plates - COMMENT THIS OUT IF YOU WANT TO SKIP
        try:
            z_support_plates = create_z_support_plates(foil, cutting_plan)
            all_plates.extend(z_support_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(z_support_plates)} Z-support plates\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Z-support plates: {str(e)}\n")
        
        # Create Y-cut plate - COMMENT THIS OUT IF YOU WANT TO SKIP
        try:
            y_cut_plates = create_y_cut_plate(foil, cutting_plan)
            all_plates.extend(y_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(y_cut_plates)} Y-cut plate\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Y-cut plate: {str(e)}\n")
        
        # Create X-cut plates - COMMENT THIS OUT IF YOU WANT TO SKIP
        try:
            x_cut_plates = create_x_cut_plates(foil, cutting_plan)
            all_plates.extend(x_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(x_cut_plates)} X-cut plates\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create X-cut plates: {str(e)}\n")
        
        # Final recompute
        FreeCAD.ActiveDocument.recompute()
        
        # Summary - only shows what was actually created
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("PLATE CREATION COMPLETE:\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        if z_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(z_cut_plates)} Z-cut plates (6mm thick for cutting)\n")
        if z_support_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(z_support_plates)} Z-support plates (3mm thick for printing support)\n")
        if y_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(y_cut_plates)} Y-cut plate (centerline at Y=0, 8mm hex)\n")
        if x_cut_plates:
            FreeCAD.Console.PrintMessage(f"  - {len(x_cut_plates)} X-cut plates (6mm thick for cutting)\n")
        
        FreeCAD.Console.PrintMessage(f"  Total: {len(all_plates)} plates created\n")
        
        if cutting_plan:
            z_cuts = cutting_plan['cutting_plan']['z_cuts']
            x_cuts = cutting_plan['cutting_plan']['x_cuts']
            FreeCAD.Console.PrintMessage(f"  Target segments: {(len(z_cuts)+1)*2*(len(x_cuts)+1)} for complete cutting\n")
        
        FreeCAD.Console.PrintMessage("\nPROGRESS STATUS:\n")
        FreeCAD.Console.PrintMessage("Step 1 ✅ Import Foil - Working\n")
        FreeCAD.Console.PrintMessage("Step 2 ✅ Define Plate Sizes - Working\n")
        
        if z_cut_plates or x_cut_plates or y_cut_plates:
            FreeCAD.Console.PrintMessage("Step 3 ✅ Hex Perforation - Working for created plates\n")
            FreeCAD.Console.PrintMessage("Step 4 ✅ Boolean Shape - Working for created plates\n")
        
        if z_support_plates:
            FreeCAD.Console.PrintMessage("Step 5 ✅ Support Plates - Created successfully\n")
        else:
            FreeCAD.Console.PrintMessage("Step 5 ⏸️ Support Plates - Not yet created\n")
            
        if y_cut_plates:
            FreeCAD.Console.PrintMessage("Step 6 ✅ Y-Cut Centerline - Created successfully\n")
        else:
            FreeCAD.Console.PrintMessage("Step 6 ⏸️ Y-Cut Centerline - Not yet created\n")
            
        FreeCAD.Console.PrintMessage("Step 7 ✅ Refactored - Separated plate creation functions\n")
        
        # Show what still needs to be done
        not_created = []
        if not z_support_plates:
            not_created.append("Z-support plates")
        if not y_cut_plates:
            not_created.append("Y-cut plate")
        if not x_cut_plates:
            not_created.append("X-cut plates")
        
        if not_created:
            FreeCAD.Console.PrintMessage(f"\nStill to create: {', '.join(not_created)}\n")
        else:
            FreeCAD.Console.PrintMessage("\nAll plate types created successfully!\n")
        
    else:
        FreeCAD.Console.PrintError("Import failed!\n")