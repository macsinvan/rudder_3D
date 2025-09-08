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
# VERSION: 3.9.0 - MESH REPAIR FOR MANIFOLD EDGES

print("=== FREECAD MOLD IMPORTER VERSION 3.9.0 - MESH REPAIR FOR MANIFOLD EDGES ===")
FreeCAD.Console.PrintMessage("=== FREECAD MOLD IMPORTER VERSION 3.9.0 - MESH REPAIR FOR MANIFOLD EDGES ===\n")

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

def repair_mesh(mesh_data):
    """Repair mesh to fix non-manifold edges"""
    try:
        import Mesh
        
        FreeCAD.Console.PrintMessage(f"      Repairing mesh...\n")
        
        # Remove duplicated points
        mesh_data.removeDuplicatedPoints()
        
        # Remove duplicated facets
        mesh_data.removeDuplicatedFacets()
        
        # Remove degenerated facets (zero area)
        mesh_data.removeNonManifolds()
        
        # Fix self-intersections
        mesh_data.fixSelfIntersections()
        
        # Harmonize normals
        mesh_data.harmonizeNormals()
        
        # Fill holes if any
        mesh_data.fillupHoles()
        
        FreeCAD.Console.PrintMessage(f"      ✅ Mesh repaired\n")
        return mesh_data
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"      ⚠️ Mesh repair failed: {str(e)}\n")
        return mesh_data

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

def segment_shell(shell_object, cutting_plan, boat_name, stock_cutout=None):
    """Segment the shell mesh using the cutting planes and cut out stock"""
    try:
        FreeCAD.Console.PrintMessage("\n=== Segmenting Shell ===\n")
        
        if not shell_object or not hasattr(shell_object, 'Mesh'):
            FreeCAD.Console.PrintWarning("No shell mesh to segment\n")
            return []
        
        import Mesh
        
        # Get cutting positions from the plan
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        y_cut = 0.0  # Centerline cut
        
        # Get shell bounding box
        shell_bbox = shell_object.Mesh.BoundBox
        
        # Sort cuts
        z_cuts_sorted = sorted(z_cuts)
        x_cuts_sorted = sorted(x_cuts)
        
        # Add boundaries to create segments
        z_boundaries = [shell_bbox.ZMin - 10] + z_cuts_sorted + [shell_bbox.ZMax + 10]
        x_boundaries = [shell_bbox.XMin - 10] + x_cuts_sorted + [shell_bbox.XMax + 10]
        y_boundaries = [shell_bbox.YMin - 10, y_cut, shell_bbox.YMax + 10]
        
        FreeCAD.Console.PrintMessage(f"Cutting shell into {(len(z_cuts)+1) * 2 * (len(x_cuts)+1)} segments\n")
        if stock_cutout:
            FreeCAD.Console.PrintMessage(f"Will cut stock hole in shell segments\n")
        
        segments = []
        segment_count = 0
        
        # Convert mesh to shape for cutting with better tolerance
        shell_shape = Part.Shape()
        shell_shape.makeShapeFromMesh(shell_object.Mesh.Topology, 0.01)  # Finer tolerance
        shell_shape = shell_shape.removeSplitter()
        
        # Create segments by cutting with planes
        for z_idx in range(len(z_boundaries) - 1):
            z_min = z_boundaries[z_idx]
            z_max = z_boundaries[z_idx + 1]
            
            for y_idx in range(len(y_boundaries) - 1):
                y_min = y_boundaries[y_idx]
                y_max = y_boundaries[y_idx + 1]
                
                for x_idx in range(len(x_boundaries) - 1):
                    x_min = x_boundaries[x_idx]
                    x_max = x_boundaries[x_idx + 1]
                    
                    segment_count += 1
                    FreeCAD.Console.PrintMessage(f"  Creating segment Z{z_idx+1}_Y{y_idx+1}_X{x_idx+1}...\n")
                    
                    try:
                        # Create cutting box slightly larger than segment
                        cut_box = Part.makeBox(
                            x_max - x_min,
                            y_max - y_min,
                            z_max - z_min,
                            FreeCAD.Vector(x_min, y_min, z_min)
                        )
                        
                        # Intersect shell with box to get segment
                        segment_shape = shell_shape.common(cut_box)
                        
                        if segment_shape.Volume > 0:
                            # Cut out stock if provided
                            if stock_cutout and stock_cutout.Shape:
                                FreeCAD.Console.PrintMessage(f"    Cutting stock hole in shell segment...\n")
                                segment_shape = segment_shape.cut(stock_cutout.Shape)
                            
                            # Create mesh from segment shape with better tessellation
                            segment_mesh = FreeCAD.ActiveDocument.addObject("Mesh::Feature", 
                                f"Shell_Segment_Z{z_idx+1}_Y{y_idx+1}_X{x_idx+1}")
                            
                            # Convert shape to mesh with finer tessellation
                            mesh_data = Mesh.Mesh()
                            mesh_data.addFacets(segment_shape.tessellate(0.5))  # Finer tessellation
                            
                            # REPAIR THE MESH
                            mesh_data = repair_mesh(mesh_data)
                            
                            segment_mesh.Mesh = mesh_data
                            
                            segment_mesh.Label = f"{boat_name}_Shell_Z{z_idx+1}_Y{y_idx+1}_X{x_idx+1}"
                            
                            # Set transparency for visibility
                            if hasattr(segment_mesh, 'ViewObject') and segment_mesh.ViewObject:
                                segment_mesh.ViewObject.Transparency = 60
                            
                            segments.append(segment_mesh)
                            FreeCAD.Console.PrintMessage(f"    ✅ Segment created and repaired\n")
                        else:
                            FreeCAD.Console.PrintMessage(f"    ⚠️ Empty segment (no intersection)\n")
                            
                    except Exception as e:
                        FreeCAD.Console.PrintError(f"    ❌ Failed to create segment: {str(e)}\n")
        
        FreeCAD.Console.PrintMessage(f"✅ Created {len(segments)} shell segments (all repaired)\n")
        
        # Hide original shell
        if hasattr(shell_object, 'ViewObject') and shell_object.ViewObject:
            shell_object.ViewObject.Visibility = False
        
        return segments
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Failed to segment shell: {str(e)}\n")
        return []

def organize_and_export_segments(shell_segments, plates, boat_name):
    """Organize and export shell segments and plates into segment folders"""
    try:
        FreeCAD.Console.PrintMessage("\n=== Organizing and Exporting Segments ===\n")
        
        # Construct export path
        boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
        output_folder = f"{boat_folder}/output/cut_foil"
        print_ready_folder = f"{output_folder}/print_ready"
        
        # Clear or create print_ready folder
        if os.path.exists(print_ready_folder):
            FreeCAD.Console.PrintMessage(f"Clearing existing print_ready folder...\n")
            shutil.rmtree(print_ready_folder)
        os.makedirs(print_ready_folder)
        
        import Mesh
        
        # Parse segment indices from shell segments
        segment_folders = {}
        for shell_segment in shell_segments:
            # Extract Z, Y, X indices from label like "MackenSea_Shell_Z1_Y1_X1"
            label_parts = shell_segment.Label.split('_')
            z_idx = label_parts[-3]  # Z1
            y_idx = label_parts[-2]  # Y1
            x_idx = label_parts[-1]  # X1
            
            segment_key = f"{z_idx}_{y_idx}_{x_idx}"
            
            if segment_key not in segment_folders:
                segment_folders[segment_key] = {
                    'shell': shell_segment,
                    'plates': []
                }
            else:
                segment_folders[segment_key]['shell'] = shell_segment
        
        # Match plates to segments based on their labels
        for plate in plates:
            label = plate.Label
            
            # Try to match plate to segment
            for segment_key in segment_folders.keys():
                z_idx, y_idx, x_idx = segment_key.split('_')
                
                # Check if plate belongs to this segment
                # Plates have labels like "MackenSea_Z_CutPlate_Z1_Lower_Y1_X1"
                if (f"_{z_idx}_" in label or f"Z{z_idx[1:]}_" in label) and \
                   (f"_{y_idx}_" in label or f"Y{y_idx[1:]}_" in label or f"Y_{y_idx[1:]}" in label) and \
                   (f"_{x_idx}" in label or f"X{x_idx[1:]}_" in label or f"X{x_idx[1:]}" in label):
                    segment_folders[segment_key]['plates'].append(plate)
                    break
        
        # Export each segment to its own folder
        exported_segments = 0
        for segment_key, segment_data in segment_folders.items():
            segment_folder = os.path.join(print_ready_folder, f"Segment_{segment_key}")
            os.makedirs(segment_folder)
            
            FreeCAD.Console.PrintMessage(f"\n  Segment {segment_key}:\n")
            
            # Export shell segment
            if segment_data['shell']:
                filename = os.path.join(segment_folder, f"{segment_data['shell'].Label}.stl")
                Mesh.export([segment_data['shell']], filename)
                FreeCAD.Console.PrintMessage(f"    ✅ Shell: {segment_data['shell'].Label}.stl\n")
            
            # Export associated plates with mesh repair
            for plate in segment_data['plates']:
                try:
                    # Convert plate shape to mesh
                    plate_mesh = Mesh.Mesh()
                    plate_mesh.addFacets(plate.Shape.tessellate(0.5))
                    
                    # Repair the plate mesh
                    plate_mesh = repair_mesh(plate_mesh)
                    
                    # Create temporary mesh object for export
                    temp_mesh_obj = FreeCAD.ActiveDocument.addObject("Mesh::Feature", "TempMesh")
                    temp_mesh_obj.Mesh = plate_mesh
                    
                    filename = os.path.join(segment_folder, f"{plate.Label}.stl")
                    Mesh.export([temp_mesh_obj], filename)
                    
                    # Remove temporary object
                    FreeCAD.ActiveDocument.removeObject(temp_mesh_obj.Name)
                    
                    FreeCAD.Console.PrintMessage(f"    ✅ Plate: {plate.Label}.stl (repaired)\n")
                except Exception as e:
                    FreeCAD.Console.PrintError(f"    ❌ Failed to export plate {plate.Label}: {str(e)}\n")
            
            FreeCAD.Console.PrintMessage(f"    Total files in segment: {1 + len(segment_data['plates'])}\n")
            exported_segments += 1
        
        FreeCAD.Console.PrintMessage(f"\n✅ Exported {exported_segments} segment folders (all meshes repaired)\n")
        FreeCAD.Console.PrintMessage(f"📁 Segments ready in: {print_ready_folder}\n")
        FreeCAD.Console.PrintMessage("\nAll meshes have been repaired to fix non-manifold edges.\n")
        FreeCAD.Console.PrintMessage("Each segment folder contains all parts needed for that section.\n")
        FreeCAD.Console.PrintMessage("Load one folder at a time into Bambu Studio for printing.\n")
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Failed to organize and export segments: {str(e)}\n")

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
    """Create Z-cut plates (horizontal - XY plane) - PRE-SEGMENTED"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Z-Cut Plates (Pre-Segmented) ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        y_cut = 0.0
        
        # Half the plate thickness for dual plates
        half_thickness = plate_thickness / 2
        
        # Create segment boundaries
        x_boundaries = [foil_bbox.XMin - bounding_margin] + sorted(x_cuts) + [foil_bbox.XMax + bounding_margin]
        y_boundaries = [foil_bbox.YMin - bounding_margin, y_cut, foil_bbox.YMax + bounding_margin]
        
        total_plates = len(z_cuts) * 2 * (len(x_boundaries)-1) * (len(y_boundaries)-1)
        FreeCAD.Console.PrintMessage(f"Creating {total_plates} Z-cut plate segments ({half_thickness}mm thick each)...\n")
        FreeCADGui.updateGui()
        
        for i, z_pos in enumerate(z_cuts):
            # Create two plates - one above and one below the cut line
            for side in ["Lower", "Upper"]:
                plate_z = z_pos - half_thickness/2 if side == "Lower" else z_pos + half_thickness/2
                
                # Create plates for each XY segment
                for x_idx in range(len(x_boundaries)-1):
                    x_min = x_boundaries[x_idx]
                    x_max = x_boundaries[x_idx+1]
                    
                    for y_idx in range(len(y_boundaries)-1):
                        y_min = y_boundaries[y_idx]
                        y_max = y_boundaries[y_idx+1]
                        
                        try:
                            plate_label = f"Z{i+1}_{side}_Y{y_idx+1}_X{x_idx+1}"
                            FreeCAD.Console.PrintMessage(f"  Creating Z-cut plate segment {plate_label}...\n")
                            FreeCADGui.updateGui()
                            
                            plate_x_size = x_max - x_min
                            plate_y_size = y_max - y_min
                            
                            # Create perforated or solid plate
                            perf_shape, perf_info = create_perforation_pattern(
                                plate_x_size, plate_y_size, half_thickness,
                                pattern_type, hex_radius, hex_wall_thickness,
                                hole_diameter, hole_spacing
                            )
                            
                            plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Z_CutPlate_{plate_label}")
                            plate.Shape = perf_shape
                            
                            # Position the plate segment
                            plate.Placement.Base = FreeCAD.Vector(x_min, y_min, plate_z)
                            
                            # Shape to foil
                            shaped = plate.Shape.common(working_shape)
                            if shaped.Volume > 0:
                                plate.Shape = shaped
                                
                                # Cut out stock if provided
                                if stock_cutout and stock_cutout.Shape:
                                    plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                                
                                plate.Label = f"{boat_name}_Z_CutPlate_{plate_label}"
                                plates.append(plate)
                                FreeCAD.Console.PrintMessage(f"    ✅ Created segment\n")
                            else:
                                # Remove empty plate
                                FreeCAD.ActiveDocument.removeObject(plate.Name)
                                FreeCAD.Console.PrintMessage(f"    ⚠️ Empty segment (no intersection)\n")
                                
                        except Exception as e:
                            FreeCAD.Console.PrintError(f"    Failed creating segment: {str(e)}\n")
                        
                        time.sleep(0.1)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_z_cut_plates failed: {str(e)}\n")
        raise
    
    return plates

def create_z_support_plates(foil_object, cutting_plan, boat_name, support_plate_thickness, plate_spacing, 
                           bounding_margin, hex_radius, hex_wall_thickness, pattern_type='hex',
                           hole_diameter=10.0, hole_spacing=15.0, stock_cutout=None):
    """Create Z support plates (3mm thick) - PRE-SEGMENTED"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Z-Support Plates (Pre-Segmented) ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        y_cut = 0.0
        
        support_z_positions = calculate_support_plate_positions(z_cuts, foil_bbox, plate_spacing)
        
        # Create segment boundaries
        x_boundaries = [foil_bbox.XMin - bounding_margin] + sorted(x_cuts) + [foil_bbox.XMax + bounding_margin]
        y_boundaries = [foil_bbox.YMin - bounding_margin, y_cut, foil_bbox.YMax + bounding_margin]
        z_boundaries = [foil_bbox.ZMin] + sorted(z_cuts) + [foil_bbox.ZMax]
        
        FreeCAD.Console.PrintMessage(f"Creating Z-support plate segments ({support_plate_thickness}mm thick)...\n")
        FreeCADGui.updateGui()
        
        for i, z_pos in enumerate(support_z_positions):
            # Determine which Z segment this support belongs to
            z_segment_idx = 0
            for idx, z_boundary in enumerate(z_boundaries[:-1]):
                if z_pos >= z_boundary and z_pos < z_boundaries[idx+1]:
                    z_segment_idx = idx + 1
                    break
            
            # Create plates for each XY segment
            for x_idx in range(len(x_boundaries)-1):
                x_min = x_boundaries[x_idx]
                x_max = x_boundaries[x_idx+1]
                
                for y_idx in range(len(y_boundaries)-1):
                    y_min = y_boundaries[y_idx]
                    y_max = y_boundaries[y_idx+1]
                    
                    try:
                        plate_label = f"Z{z_segment_idx}_Support{i+1}_Y{y_idx+1}_X{x_idx+1}"
                        FreeCAD.Console.PrintMessage(f"  Creating Z-support segment {plate_label}...\n")
                        
                        plate_x_size = x_max - x_min
                        plate_y_size = y_max - y_min
                        
                        # Create perforated or solid plate
                        perf_shape, perf_info = create_perforation_pattern(
                            plate_x_size, plate_y_size, support_plate_thickness,
                            pattern_type, hex_radius, hex_wall_thickness,
                            hole_diameter, hole_spacing
                        )
                        
                        plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Z_Support_{plate_label}")
                        plate.Shape = perf_shape
                        
                        # Position the plate segment
                        plate_z_center = z_pos - support_plate_thickness / 2
                        plate.Placement.Base = FreeCAD.Vector(x_min, y_min, plate_z_center)
                        
                        # Shape to foil
                        shaped = plate.Shape.common(working_shape)
                        if shaped.Volume > 0:
                            plate.Shape = shaped
                            
                            # Cut out stock if provided
                            if stock_cutout and stock_cutout.Shape:
                                plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                            
                            plate.Label = f"{boat_name}_Z_Support_{plate_label}"
                            
                            if hasattr(plate, 'ViewObject') and plate.ViewObject:
                                plate.ViewObject.Transparency = 85
                            
                            plates.append(plate)
                            FreeCAD.Console.PrintMessage(f"    ✅ Created segment\n")
                        else:
                            # Remove empty plate
                            FreeCAD.ActiveDocument.removeObject(plate.Name)
                            FreeCAD.Console.PrintMessage(f"    ⚠️ Empty segment\n")
                            
                    except Exception as e:
                        FreeCAD.Console.PrintError(f"    Failed: {str(e)}\n")
                    
                    time.sleep(0.1)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_z_support_plates failed: {str(e)}\n")
        raise
    
    return plates

def create_x_support_plates(foil_object, cutting_plan, boat_name, support_plate_thickness, x_support_spacing, 
                           bounding_margin, hex_radius, hex_wall_thickness, pattern_type='hex',
                           hole_diameter=10.0, hole_spacing=15.0, stock_cutout=None):
    """Create X support plates (3mm thick) at 50mm spacing - PRE-SEGMENTED"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating X-Support Plates (Pre-Segmented) ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        y_cut = 0.0
        
        support_x_positions = calculate_x_support_positions(x_cuts, foil_bbox, x_support_spacing)
        
        # Create segment boundaries
        z_boundaries = [foil_bbox.ZMin - bounding_margin] + sorted(z_cuts) + [foil_bbox.ZMax + bounding_margin]
        y_boundaries = [foil_bbox.YMin - bounding_margin, y_cut, foil_bbox.YMax + bounding_margin]
        x_boundaries = [foil_bbox.XMin] + sorted(x_cuts) + [foil_bbox.XMax]
        
        FreeCAD.Console.PrintMessage(f"Creating X-support plate segments ({support_plate_thickness}mm thick)...\n")
        FreeCADGui.updateGui()
        
        for i, x_pos in enumerate(support_x_positions):
            # Determine which X segment this support belongs to
            x_segment_idx = 0
            for idx, x_boundary in enumerate(x_boundaries[:-1]):
                if x_pos >= x_boundary and x_pos < x_boundaries[idx+1]:
                    x_segment_idx = idx + 1
                    break
            
            # Create plates for each YZ segment
            for z_idx in range(len(z_boundaries)-1):
                z_min = z_boundaries[z_idx]
                z_max = z_boundaries[z_idx+1]
                
                for y_idx in range(len(y_boundaries)-1):
                    y_min = y_boundaries[y_idx]
                    y_max = y_boundaries[y_idx+1]
                    
                    try:
                        plate_label = f"Z{z_idx+1}_Y{y_idx+1}_X{x_segment_idx}_Support{i+1}"
                        FreeCAD.Console.PrintMessage(f"  Creating X-support segment {plate_label}...\n")
                        
                        plate_y_size = y_max - y_min
                        plate_z_size = z_max - z_min
                        
                        # Create perforated or solid plate
                        perf_shape, perf_info = create_perforation_pattern(
                            plate_z_size, plate_y_size, support_plate_thickness,
                            pattern_type, hex_radius, hex_wall_thickness,
                            hole_diameter, hole_spacing
                        )
                        
                        plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"X_Support_{plate_label}")
                        plate.Shape = perf_shape
                        
                        # Rotate 90 degrees around Y axis for vertical orientation
                        rotation = FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90)
                        plate.Placement.Rotation = rotation
                        
                        # Position the plate segment
                        plate_x_center = x_pos - support_plate_thickness / 2
                        current_placement = plate.Placement
                        current_placement.Base = FreeCAD.Vector(plate_x_center, y_min, z_min + plate_z_size)
                        plate.Placement = current_placement
                        
                        # Shape to foil
                        shaped = plate.Shape.common(working_shape)
                        if shaped.Volume > 0:
                            plate.Shape = shaped
                            
                            # Cut out stock if provided
                            if stock_cutout and stock_cutout.Shape:
                                plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                            
                            plate.Label = f"{boat_name}_X_Support_{plate_label}"
                            
                            if hasattr(plate, 'ViewObject') and plate.ViewObject:
                                plate.ViewObject.Transparency = 85
                            
                            plates.append(plate)
                            FreeCAD.Console.PrintMessage(f"    ✅ Created segment\n")
                        else:
                            # Remove empty plate
                            FreeCAD.ActiveDocument.removeObject(plate.Name)
                            FreeCAD.Console.PrintMessage(f"    ⚠️ Empty segment\n")
                            
                    except Exception as e:
                        FreeCAD.Console.PrintError(f"    Failed: {str(e)}\n")
                    
                    time.sleep(0.1)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_x_support_plates failed: {str(e)}\n")
        raise
    
    return plates

def create_y_cut_plate(foil_object, cutting_plan, boat_name, plate_thickness, bounding_margin, 
                      hex_wall_thickness, pattern_type='hex',
                      hole_diameter=16.0, hole_spacing=20.0, stock_cutout=None):
    """Create Y-cut plates (centerline - XZ plane) at Y=0 - PRE-SEGMENTED"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating Y-Cut Plates (Pre-Segmented) ===\n")
        FreeCAD.Console.PrintMessage("Creating Y-cut plate segments at Y=0...\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        
        # Half the plate thickness for dual plates
        half_thickness = plate_thickness / 2
        
        # Create segment boundaries
        x_boundaries = [foil_bbox.XMin - bounding_margin] + sorted(x_cuts) + [foil_bbox.XMax + bounding_margin]
        z_boundaries = [foil_bbox.ZMin - bounding_margin] + sorted(z_cuts) + [foil_bbox.ZMax + bounding_margin]
        
        # Create two plates - one on each side of Y=0
        for side in ["Left", "Right"]:
            plate_y = -half_thickness/2 if side == "Left" else half_thickness/2
            y_idx = 1 if side == "Left" else 2  # Y index for naming
            
            # Create plates for each XZ segment
            for x_idx in range(len(x_boundaries)-1):
                x_min = x_boundaries[x_idx]
                x_max = x_boundaries[x_idx+1]
                
                for z_idx in range(len(z_boundaries)-1):
                    z_min = z_boundaries[z_idx]
                    z_max = z_boundaries[z_idx+1]
                    
                    try:
                        plate_label = f"Z{z_idx+1}_Y{y_idx}_{side}_X{x_idx+1}"
                        FreeCAD.Console.PrintMessage(f"  Creating Y-cut segment {plate_label}...\n")
                        
                        plate_x_size = x_max - x_min
                        plate_z_size = z_max - z_min
                        
                        # Y-cut plates can use larger perforations
                        if pattern_type == 'hex' and hex_array_helper:
                            perf_shape, perf_info = hex_array_helper.create_honeycomb_geometry(
                                length=plate_x_size,
                                width=plate_z_size,
                                thickness=half_thickness,
                                hex_radius=8.0,
                                wall_thickness=hex_wall_thickness
                            )
                        elif pattern_type == 'circle':
                            perf_shape, perf_info = create_perforation_pattern(
                                plate_x_size, plate_z_size, half_thickness,
                                pattern_type, 8.0, hex_wall_thickness,
                                hole_diameter, hole_spacing
                            )
                        else:
                            perf_shape = Part.makeBox(plate_x_size, plate_z_size, half_thickness)
                            perf_info = {'pattern': 'solid'}
                        
                        plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Y_CutPlate_{plate_label}")
                        plate.Shape = perf_shape
                        
                        # Rotate 90 degrees around X axis for vertical orientation
                        rotation = FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 90)
                        plate.Placement.Rotation = rotation
                        
                        # Position the plate segment
                        current_placement = plate.Placement
                        current_placement.Base = FreeCAD.Vector(x_min, plate_y, z_min)
                        plate.Placement = current_placement
                        
                        # Shape to foil
                        shaped = plate.Shape.common(working_shape)
                        if shaped.Volume > 0:
                            plate.Shape = shaped
                            
                            # Cut out stock if provided
                            if stock_cutout and stock_cutout.Shape:
                                plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                            
                            plate.Label = f"{boat_name}_Y_CutPlate_{plate_label}"
                            plates.append(plate)
                            FreeCAD.Console.PrintMessage(f"    ✅ Created segment\n")
                        else:
                            # Remove empty plate
                            FreeCAD.ActiveDocument.removeObject(plate.Name)
                            FreeCAD.Console.PrintMessage(f"    ⚠️ Empty segment\n")
                            
                    except Exception as e:
                        FreeCAD.Console.PrintError(f"    Failed: {str(e)}\n")
                    
                    time.sleep(0.1)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_y_cut_plate failed: {str(e)}\n")
        raise
    
    return plates

def create_x_cut_plates(foil_object, cutting_plan, boat_name, plate_thickness, bounding_margin, 
                       hex_radius, hex_wall_thickness, pattern_type='hex',
                       hole_diameter=10.0, hole_spacing=15.0, stock_cutout=None):
    """Create X-cut plates (vertical - YZ plane) - PRE-SEGMENTED"""
    plates = []
    
    try:
        FreeCAD.Console.PrintMessage("\n=== Creating X-Cut Plates (Pre-Segmented) ===\n")
        FreeCADGui.updateGui()
        
        foil_bbox = foil_object.Shape.BoundBox
        working_shape = prepare_foil_for_boolean(foil_object)
        
        z_cuts = cutting_plan['cutting_plan']['z_cuts']
        x_cuts = cutting_plan['cutting_plan']['x_cuts']
        y_cut = 0.0
        
        # Half the plate thickness for dual plates
        half_thickness = plate_thickness / 2
        
        # Create segment boundaries
        y_boundaries = [foil_bbox.YMin - bounding_margin, y_cut, foil_bbox.YMax + bounding_margin]
        z_boundaries = [foil_bbox.ZMin - bounding_margin] + sorted(z_cuts) + [foil_bbox.ZMax + bounding_margin]
        
        FreeCAD.Console.PrintMessage(f"Creating X-cut plate segments ({half_thickness}mm thick each)...\n")
        FreeCADGui.updateGui()
        
        for i, x_pos in enumerate(x_cuts):
            # Create two plates - one on each side of the cut
            for side in ["Left", "Right"]:
                plate_x = x_pos - half_thickness/2 if side == "Left" else x_pos + half_thickness/2
                x_idx = i+1 if side == "Left" else i+2  # X index for naming
                
                # Create plates for each YZ segment
                for y_idx in range(len(y_boundaries)-1):
                    y_min = y_boundaries[y_idx]
                    y_max = y_boundaries[y_idx+1]
                    
                    for z_idx in range(len(z_boundaries)-1):
                        z_min = z_boundaries[z_idx]
                        z_max = z_boundaries[z_idx+1]
                        
                        try:
                            plate_label = f"Z{z_idx+1}_Y{y_idx+1}_X{x_idx}_{side}"
                            FreeCAD.Console.PrintMessage(f"  Creating X-cut segment {plate_label}...\n")
                            
                            plate_y_size = y_max - y_min
                            plate_z_size = z_max - z_min
                            
                            # Create perforated or solid plate
                            perf_shape, perf_info = create_perforation_pattern(
                                plate_z_size, plate_y_size, half_thickness,
                                pattern_type, hex_radius, hex_wall_thickness,
                                hole_diameter, hole_spacing
                            )
                            
                            plate = FreeCAD.ActiveDocument.addObject("Part::Feature", f"X_CutPlate_{plate_label}")
                            plate.Shape = perf_shape
                            
                            # Rotate 90 degrees around Y axis for vertical orientation
                            rotation = FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90)
                            plate.Placement.Rotation = rotation
                            
                            # Position the plate segment
                            current_placement = plate.Placement
                            current_placement.Base = FreeCAD.Vector(plate_x, y_min, z_min + plate_z_size)
                            plate.Placement = current_placement
                            
                            # Shape to foil
                            shaped = plate.Shape.common(working_shape)
                            if shaped.Volume > 0:
                                plate.Shape = shaped
                                
                                # Cut out stock if provided
                                if stock_cutout and stock_cutout.Shape:
                                    plate.Shape = plate.Shape.cut(stock_cutout.Shape)
                                
                                plate.Label = f"{boat_name}_X_CutPlate_{plate_label}"
                                plates.append(plate)
                                FreeCAD.Console.PrintMessage(f"    ✅ Created segment\n")
                            else:
                                # Remove empty plate
                                FreeCAD.ActiveDocument.removeObject(plate.Name)
                                FreeCAD.Console.PrintMessage(f"    ⚠️ Empty segment\n")
                                
                        except Exception as e:
                            FreeCAD.Console.PrintError(f"    Failed: {str(e)}\n")
                        
                        time.sleep(0.1)
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"FATAL: create_x_cut_plates failed: {str(e)}\n")
        raise
    
    return plates

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
        
        # Import stock cutout early so it can be used for plate cutting and shell
        stock_cutout = import_stock_cutout(boat_name)
        
        all_plates = []
        shell_segments = []
        
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("CREATING PRE-SEGMENTED PLATES WITH MESH REPAIR\n")
        FreeCAD.Console.PrintMessage(f"Pattern type: {pattern_type.upper()}\n")
        FreeCAD.Console.PrintMessage(f"Plates will be created already segmented for each mold section\n")
        FreeCAD.Console.PrintMessage(f"All meshes will be repaired to fix non-manifold edges\n")
        if pattern_type == 'circle':
            FreeCAD.Console.PrintMessage(f"Hole diameter: {hole_diameter}mm, Spacing: {hole_spacing}mm\n")
        elif pattern_type == 'hex':
            FreeCAD.Console.PrintMessage(f"Hex radius: {hex_radius}mm, Wall thickness: {hex_wall_thickness}mm\n")
        if stock_cutout:
            FreeCAD.Console.PrintMessage(f"Stock cutout: ENABLED - plates and shell will have stock clearance\n")
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
            FreeCAD.Console.PrintMessage(f"✅ Created {len(z_cut_plates)} Z-cut plate segments\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Z-cut plates: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            z_support_plates = create_z_support_plates(foil, cutting_plan, boat_name, 
                                                      support_plate_thickness, plate_spacing,
                                                      bounding_margin, hex_radius, hex_wall_thickness,
                                                      pattern_type, hole_diameter, hole_spacing, stock_cutout)
            all_plates.extend(z_support_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(z_support_plates)} Z-support plate segments\n")
            
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
            FreeCAD.Console.PrintMessage(f"✅ Created {len(x_support_plates)} X-support plate segments\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create X-support plates: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            y_cut_plates = create_y_cut_plate(foil, cutting_plan, boat_name, plate_thickness,
                                             bounding_margin, hex_wall_thickness,
                                             pattern_type, hole_diameter, hole_spacing, stock_cutout)
            all_plates.extend(y_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(y_cut_plates)} Y-cut plate segments\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create Y-cut plates: {str(e)}\n")
        
        FreeCADGui.updateGui()

        try:
            x_cut_plates = create_x_cut_plates(foil, cutting_plan, boat_name, plate_thickness,
                                              bounding_margin, hex_radius, hex_wall_thickness,
                                              pattern_type, hole_diameter, hole_spacing, stock_cutout)
            all_plates.extend(x_cut_plates)
            FreeCAD.Console.PrintMessage(f"✅ Created {len(x_cut_plates)} X-cut plate segments\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"❌ Failed to create X-cut plates: {str(e)}\n")
        
        # Import foil shell if available and segment it (with stock cutout)
        shell = import_foil_shell(boat_name)
        if shell:
            shell_segments = segment_shell(shell, cutting_plan, boat_name, stock_cutout)
            FreeCAD.Console.PrintMessage(f"✅ Segmented shell into {len(shell_segments)} pieces (all repaired)\n")
        
        FreeCADGui.updateGui()
        FreeCAD.ActiveDocument.recompute()
        
        # Organize and export into segment folders
        if shell_segments and all_plates:
            organize_and_export_segments(shell_segments, all_plates, boat_name)
        
        # Summary
        FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
        FreeCAD.Console.PrintMessage("PLATE CREATION COMPLETE:\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        
        FreeCAD.Console.PrintMessage(f"  Total plate segments: {len(all_plates)}\n")
        
        if shell_segments:
            FreeCAD.Console.PrintMessage(f"  Shell segments: {len(shell_segments)}\n")
        
        FreeCAD.Console.PrintMessage(f"  Total pieces: {len(all_plates) + len(shell_segments)}\n")
        FreeCAD.Console.PrintMessage(f"  Pattern used: {pattern_type}\n")
        FreeCAD.Console.PrintMessage(f"  All meshes repaired for manifold edges\n")
        
        if stock_cutout:
            FreeCAD.Console.PrintMessage(f"  Stock cutout: APPLIED to all plates and shell\n")
        
        if cutting_plan:
            z_cuts = cutting_plan['cutting_plan']['z_cuts']
            x_cuts = cutting_plan['cutting_plan']['x_cuts']
            FreeCAD.Console.PrintMessage(f"  Target mold segments: {(len(z_cuts)+1)*2*(len(x_cuts)+1)}\n")
        
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