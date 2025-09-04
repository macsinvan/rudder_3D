import FreeCAD
import FreeCADGui
import Import
import Part
import json
import os
import time

# Compatible with FreeCAD 1.1
# Foil Mold Importer and Visualizer for Boat Manufacturing
# VERSION: 2.1.0 - CLEAN REVERT - Solid plates only

print("=== FREECAD MOLD IMPORTER VERSION 2.1.0 - CLEAN REVERT ===")
FreeCAD.Console.PrintMessage("=== FREECAD MOLD IMPORTER VERSION 2.1.0 - CLEAN REVERT ===\n")

# Parameters
boat_name = "MackenSea"
plate_thickness = 6.0  # mm
bounding_margin = 10.0  # mm
hole_diameter = 4.0  # mm
hole_spacing = 6.0  # mm (center to center)

# Construct file paths
boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
output_folder = f"{boat_folder}/output"
cut_foil_folder = f"{output_folder}/cut_foil"

cutting_plan_file = f"{cut_foil_folder}/{boat_name}_Cut_Foil_cutting_plan.json"
mold_step_file = f"{cut_foil_folder}/{boat_name}_Mold.step"

def import_foil_mold():
    """Import the cutting plan JSON and mold STEP file"""
    
    # Check if files exist
    if not os.path.exists(cutting_plan_file):
        FreeCAD.Console.PrintError(f"Cutting plan file not found: {cutting_plan_file}\n")
        return None, None
        
    if not os.path.exists(mold_step_file):
        FreeCAD.Console.PrintError(f"Mold STEP file not found: {mold_step_file}\n")
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
    
    # Import mold STEP file
    try:
        Import.insert(mold_step_file, FreeCAD.ActiveDocument.Name)
        FreeCAD.Console.PrintMessage(f"Imported mold STEP file: {mold_step_file}\n")
        
        # Get the imported object (should be the last object added)
        mold_object = FreeCAD.ActiveDocument.Objects[-1]
        mold_object.Label = f"{boat_name}_Mold"
        
        FreeCAD.ActiveDocument.recompute()
        
        # Allow time for object to fully initialize
        time.sleep(0.5)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error importing mold STEP file: {str(e)}\n")
        return cutting_plan, None
    
    return cutting_plan, mold_object

def configure_display(mold_object, cutting_plan):
    """Configure FreeCAD display for optimal viewing of the mold and cutting planes"""
    
    try:
        # Ensure we have a GUI
        if not hasattr(FreeCADGui, 'ActiveDocument') or not FreeCADGui.ActiveDocument:
            FreeCAD.Console.PrintWarning("No GUI available - skipping display configuration\n")
            return
            
        # Set transparency - FreeCAD 1.1 compatible
        try:
            if hasattr(mold_object, 'ViewObject') and mold_object.ViewObject:
                mold_object.ViewObject.Transparency = 70
                FreeCAD.ActiveDocument.recompute()
                FreeCADGui.updateGui()
                FreeCAD.Console.PrintMessage("Set mold transparency to 70%\n")
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

def create_plates(mold_object, cutting_plan):
    """Create plates at each cutting plane position with proper dimensions"""
    
    try:
        # Get mold bounding box for reference
        mold_bbox = mold_object.Shape.BoundBox
        FreeCAD.Console.PrintMessage(f"Mold bounding box: X({mold_bbox.XMin:.2f} to {mold_bbox.XMax:.2f}), "
                                   f"Y({mold_bbox.YMin:.2f} to {mold_bbox.YMax:.2f}), "
                                   f"Z({mold_bbox.ZMin:.2f} to {mold_bbox.ZMax:.2f})\n")
        
        plates = []
        
        # Create Z-cut plates (horizontal plates - XY plane)
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        FreeCAD.Console.PrintMessage(f"\nCreating {len(z_cuts)} Z-cut plates (horizontal)...\n")
        
        for i, z_pos in enumerate(z_cuts):
            try:
                # For Z-cuts, create XY plane plates
                # Use full mold X and Y extents plus margin
                plate_x_size = (mold_bbox.XMax - mold_bbox.XMin) + 2 * bounding_margin
                plate_y_size = (mold_bbox.YMax - mold_bbox.YMin) + 2 * bounding_margin
                
                # Create plate as FreeCAD box
                plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"Z_Plate_{i+1}")
                plate.Length = plate_x_size
                plate.Width = plate_y_size  
                plate.Height = plate_thickness
                
                # Position plate - center it on mold XY, position at z_cut coordinate
                plate_x_center = (mold_bbox.XMin + mold_bbox.XMax) / 2 - plate_x_size / 2
                plate_y_center = (mold_bbox.YMin + mold_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = z_pos - plate_thickness / 2
                
                plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                plate.Label = f"{boat_name}_Z_Plate_{i+1}_at_Z{z_pos:.1f}"
                
                plates.append(plate)
                
                FreeCAD.Console.PrintMessage(f"  Z-Plate {i+1}: {plate_x_size:.1f} × {plate_y_size:.1f} × {plate_thickness:.1f} mm at Z={z_pos:.2f}\n")
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error creating Z-plate {i+1}: {str(e)}\n")
        
        # Create X-cut plates (vertical plates - YZ plane)
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        FreeCAD.Console.PrintMessage(f"\nCreating {len(x_cuts)} X-cut plates (vertical)...\n")
        
        for i, x_pos in enumerate(x_cuts):
            try:
                # For X-cuts, create YZ plane plates  
                # Use full mold Y and Z extents plus margin
                plate_y_size = (mold_bbox.YMax - mold_bbox.YMin) + 2 * bounding_margin
                plate_z_size = (mold_bbox.ZMax - mold_bbox.ZMin) + 2 * bounding_margin
                
                # Create plate as FreeCAD box
                plate = FreeCAD.ActiveDocument.addObject("Part::Box", f"X_Plate_{i+1}")
                plate.Length = plate_thickness
                plate.Width = plate_y_size
                plate.Height = plate_z_size
                
                # Position plate - center it on mold YZ, position at x_cut coordinate  
                plate_x_center = x_pos - plate_thickness / 2
                plate_y_center = (mold_bbox.YMin + mold_bbox.YMax) / 2 - plate_y_size / 2
                plate_z_center = (mold_bbox.ZMin + mold_bbox.ZMax) / 2 - plate_z_size / 2
                
                plate.Placement.Base = FreeCAD.Vector(plate_x_center, plate_y_center, plate_z_center)
                plate.Label = f"{boat_name}_X_Plate_{i+1}_at_X{x_pos:.1f}"
                
                plates.append(plate)
                
                FreeCAD.Console.PrintMessage(f"  X-Plate {i+1}: {plate_thickness:.1f} × {plate_y_size:.1f} × {plate_z_size:.1f} mm at X={x_pos:.2f}\n")
                
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error creating X-plate {i+1}: {str(e)}\n")
        
        # Recompute document to show all plates
        FreeCAD.ActiveDocument.recompute()
        
        FreeCAD.Console.PrintMessage(f"\nStep 2 Complete: Created {len(plates)} plates total\n")
        FreeCAD.Console.PrintMessage(f"  - {len(z_cuts)} Z-cut plates (horizontal, will need tabs)\n")  
        FreeCAD.Console.PrintMessage(f"  - {len(x_cuts)} X-cut plates (vertical, clean cuts only)\n")
        
        return plates
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error creating plates: {str(e)}\n")
        return []

# Execute the import
if __name__ == "__main__":
    # Ensure we have an active document
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument()
    
    cutting_plan, mold = import_foil_mold()
    
    if cutting_plan and mold:
        FreeCAD.Console.PrintMessage("Successfully imported cutting plan and mold!\n")
        FreeCAD.Console.PrintMessage(f"Mold object: {mold.Label}\n")
        configure_display(mold, cutting_plan)
        
        # Step 2: Create plates at cutting positions
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("STEP 2: CREATING PLATES\n") 
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        plates = create_plates(mold, cutting_plan)
        
        FreeCAD.Console.PrintMessage("\nCLEAN REVERT COMPLETE\n")
        FreeCAD.Console.PrintMessage("Step 1 ✅ Import Mold - Working\n")
        FreeCAD.Console.PrintMessage("Step 2 ✅ Define Plate Sizes - Working\n")
        FreeCAD.Console.PrintMessage("Ready for next steps when you are.\n")
        
    else:
        FreeCAD.Console.PrintError("Import failed!\n")