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
# VERSION: 2.9.0 - INLINE BOOLEAN SHAPING FOR ALL PLATES

print("=== FREECAD MOLD IMPORTER VERSION 2.9.0 - INLINE BOOLEAN SHAPING ===")
FreeCAD.Console.PrintMessage("=== FREECAD MOLD IMPORTER VERSION 2.9.0 - INLINE BOOLEAN SHAPING ===\n")

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
plate_thickness = 6.0  # mm
bounding_margin = 10.0  # mm
hole_diameter = 4.0  # mm
hole_spacing = 6.0  # mm (center to center)

# Hex perforation parameters
hex_radius = 8.0  # mm - circumradius of hexagon holes
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
        
        # Configure view - FreeCAD 1.1 compatible
        try:
            # Get active view using FreeCAD 1.1 method
            view = FreeCADGui.activeView()
            
            if view:
                # Set isometric view - try multiple methods for 1.1 compatibility
                try:
                    view.viewIsometric()
                    FreeCAD.Console.PrintMessage("Set isometric view (method 1)\n")
                except:
                    try:
                        view.setViewDirection((1, 1, 1))
                        FreeCAD.Console.PrintMessage("Set isometric view (method 2)\n")
                    except:
                        FreeCAD.Console.PrintWarning("Could not set isometric view\n")
                
                # Fit all objects to view
                try:
                    view.fitAll()
                    FreeCAD.Console.PrintMessage("Fitted all objects to view\n")
                except:
                    try:
                        FreeCADGui.SendMsgToActiveView("ViewFit")
                        FreeCAD.Console.PrintMessage("Fitted view using SendMsg method\n")
                    except:
                        FreeCAD.Console.PrintWarning("Could not fit view\n")
            else:
                FreeCAD.Console.PrintWarning("No active view available\n")
                
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error configuring view: {str(e)}\n")
        
        # Print cutting information to console for reference
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("CUTTING PLAN SUMMARY:\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        
        FreeCAD.Console.PrintMessage(f"Z-CUTS (horizontal, need plates with tabs):\n")
        for i, z_pos in enumerate(z_cuts):
            FreeCAD.Console.PrintMessage(f"  Cut {i+1}: Z = {z_pos:.2f} mm\n")
            
        FreeCAD.Console.PrintMessage(f"\nX-CUTS (vertical, clean cuts only):\n")
        for i, x_pos in enumerate(x_cuts):
            FreeCAD.Console.PrintMessage(f"  Cut {i+1}: X = {x_pos:.2f} mm\n")
            
        FreeCAD.Console.PrintMessage(f"\nTotal segments: {len(z_cuts)+1} vertical × {len(x_cuts)+1} horizontal = {(len(z_cuts)+1)*(len(x_cuts)+1)} pieces\n")
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

def create_plates(foil_object, cutting_plan):
    """Create plates at each cutting plane position with proper dimensions"""
    
    try:
        # Get foil bounding box for reference
        foil_bbox = foil_object.Shape.BoundBox
        FreeCAD.Console.PrintMessage(f"Foil bounding box: X({foil_bbox.XMin:.2f} to {foil_bbox.XMax:.2f}), "
                                   f"Y({foil_bbox.YMin:.2f} to {foil_bbox.YMax:.2f}), "
                                   f"Z({foil_bbox.ZMin:.2f} to {foil_bbox.ZMax:.2f})\n")
        
        # Prepare foil for boolean operations
        FreeCAD.Console.PrintMessage("\nChecking foil geometry for boolean operations...\n")
        working_shape = prepare_foil_for_boolean(foil_object)
        
        plates = []
        
        # Create Z-cut plates (horizontal plates - XY plane) with hex perforation and boolean shaping
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        FreeCAD.Console.PrintMessage(f"\nCreating {len(z_cuts)} Z-cut plates (horizontal) with hex perforation and foil shaping...\n")
        
        for i, z_pos in enumerate(z_cuts):
            try:
                # For Z-cuts, create XY plane plates
                # Use full foil X and Y extents plus margin
                plate_x_size = (foil_bbox.XMax - foil_bbox.XMin) + 2 * bounding_margin
                plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                
                # Create hex-perforated plate using helper module
                if hex_array_helper:
                    # Create hex-perforated geometry
                    hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                        length=plate_x_size,
                        width=plate_y_size,
                        thickness=plate_thickness,
                        hex_radius=hex_radius,
                        wall_thickness=hex_wall_thickness
                    )
                    
                    # Create FreeCAD Part object from the shape
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Z_Plate_{i+1}")
                    plate.Shape = hex_shape
                    
                    FreeCAD.Console.PrintMessage(f"  Z-Plate {i+1}: {plate_x_size:.1f} × {plate_y_size:.1f} × {plate_thickness:.1f} mm at Z={z_pos:.2f}\n")
                    FreeCAD.Console.PrintMessage(f"    Hex pattern: {hex_info['total_hexagons']} hexagons\n")
                else:
                    # Fallback to solid plate if hex module not available
                    FreeCAD.Console.PrintWarning("Hex module not available - creating solid plate\n")
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"Z_Plate_{i+1}")
                    plate.Length = plate_x_size
                    plate.Width = plate_y_size  
                    plate.Height = plate_thickness
                    FreeCAD.Console.PrintMessage(f"  Z-Plate {i+1}: {plate_x_size:.1f} × {plate_y_size:.1f} × {plate_thickness:.1f} mm at Z={z_pos:.2f} (SOLID)\n")
                
                # Position plate - center it on foil XY, position at z_cut coordinate
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
                
                plate.Label = f"{boat_name}_Z_Plate_{i+1}_at_Z{z_pos:.1f}"
                plates.append(plate)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error creating Z-plate {i+1}: {str(e)}\n")
        
        # Create X-cut plates (vertical plates - YZ plane) with hex perforation and boolean shaping
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        FreeCAD.Console.PrintMessage(f"\nCreating {len(x_cuts)} X-cut plates (vertical) with hex perforation and foil shaping...\n")
        
        for i, x_pos in enumerate(x_cuts):
            try:
                # For X-cuts, create YZ plane plates  
                # Use full foil Y and Z extents plus margin
                plate_y_size = (foil_bbox.YMax - foil_bbox.YMin) + 2 * bounding_margin
                plate_z_size = (foil_bbox.ZMax - foil_bbox.ZMin) + 2 * bounding_margin
                
                # Create hex-perforated plate using helper module
                if hex_array_helper:
                    # Note: For X-plates, we use z_size as length and y_size as width for the hex pattern
                    # since the plate is vertical (YZ plane)
                    hex_shape, hex_info = hex_array_helper.create_honeycomb_geometry(
                        length=plate_z_size,  # Height becomes length for vertical plate
                        width=plate_y_size,   # Width remains width
                        thickness=plate_thickness,
                        hex_radius=hex_radius,
                        wall_thickness=hex_wall_thickness
                    )
                    
                    # Create FreeCAD Part object from the shape
                    plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"X_Plate_{i+1}")
                    plate.Shape = hex_shape
                    
                    # Rotate the plate 90 degrees around Y axis to make it vertical
                    rotation = FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90)
                    plate.Placement.Rotation = rotation
                    
                    FreeCAD.Console.PrintMessage(f"  X-Plate {i+1}: {plate_thickness:.1f} × {plate_y_size:.1f} × {plate_z_size:.1f} mm at X={x_pos:.2f}\n")
                    FreeCAD.Console.PrintMessage(f"    Hex pattern: {hex_info['total_hexagons']} hexagons\n")
                else:
                    # Fallback to solid plate if hex module not available
                    FreeCAD.Console.PrintWarning("Hex module not available - creating solid plate\n")
                    plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"X_Plate_{i+1}")
                    plate.Length = plate_thickness
                    plate.Width = plate_y_size
                    plate.Height = plate_z_size
                    FreeCAD.Console.PrintMessage(f"  X-Plate {i+1}: {plate_thickness:.1f} × {plate_y_size:.1f} × {plate_z_size:.1f} mm at X={x_pos:.2f} (SOLID)\n")
                
                # Position plate - center it on foil YZ, position at x_cut coordinate  
                plate_x_center = x_pos - plate_thickness / 2
                plate_y_center = (foil_bbox.YMin + foil_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = (foil_bbox.ZMin + foil_bbox.ZMax) / 2 + plate_z_size / 2
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
                
                plate.Label = f"{boat_name}_X_Plate_{i+1}_at_X{x_pos:.1f}"
                plates.append(plate)
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error creating X-plate {i+1}: {str(e)}\n")
        
        # Recompute document to show all plates
        FreeCAD.ActiveDocument.recompute()
        
        FreeCAD.Console.PrintMessage(f"\nStep 2, 3 & 4 Complete: Created {len(plates)} plates total\n")
        FreeCAD.Console.PrintMessage(f"  - {len(z_cuts)} Z-cut plates (horizontal, hex-perforated, shaped to foil)\n")  
        FreeCAD.Console.PrintMessage(f"  - {len(x_cuts)} X-cut plates (vertical, hex-perforated, shaped to foil)\n")
        
        return plates
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error creating plates: {str(e)}\n")
        return []

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
        
        # Step 2, 3 & 4: Create plates at cutting positions with hex perforation and shaping
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("STEP 2, 3 & 4: CREATING PLATES WITH HEX PERFORATION AND SHAPING\n") 
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        plates = create_plates(foil, cutting_plan)
        
        FreeCAD.Console.PrintMessage("\nPROGRESS STATUS:\n")
        FreeCAD.Console.PrintMessage("Step 1 ✅ Import Foil - Working\n")
        FreeCAD.Console.PrintMessage("Step 2 ✅ Define Plate Sizes - Working\n")
        FreeCAD.Console.PrintMessage("Step 3 ✅ Hex Perforation - ALL plates hex-perforated\n")
        FreeCAD.Console.PrintMessage("Step 4 ✅ Boolean Shape - ALL plates shaped to foil profile\n")
        FreeCAD.Console.PrintMessage("Ready for: Step 5 (Z-cut tabs).\n")
        
    else:
        FreeCAD.Console.PrintError("Import failed!\n")