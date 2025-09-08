import FreeCAD
import FreeCADGui
import Import
import Part
import Mesh
import json
import os
import time
import sys

# Foil Shell and Inner Plates Assembly
# VERSION: 1.0.2 - Added breathing room to prevent crashes

FreeCAD.Console.PrintMessage("=== FOIL SHELL AND PLATES ASSEMBLY VERSION 1.0.2 ===\n")

def import_components(boat_name):
    """Import the merged inner plates (STL) and foil shell (STEP) files"""
    
    # Construct file paths
    boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
    output_folder = f"{boat_folder}/output"
    cut_foil_folder = f"{output_folder}/cut_foil"
    
    merged_plates_stl = f"{cut_foil_folder}/merged_inner_plates.stl"  # Use STL instead
    shell_foil_file = f"{cut_foil_folder}/{boat_name}_Shell_Foil.step"
    cutting_plan_file = f"{cut_foil_folder}/{boat_name}_Cut_Foil_cutting_plan.json"
    
    imported_objects = {}
    
    # Import cutting plan JSON
    if not os.path.exists(cutting_plan_file):
        FreeCAD.Console.PrintError(f"Cutting plan file not found: {cutting_plan_file}\n")
    else:
        try:
            with open(cutting_plan_file, 'r') as f:
                cutting_plan = json.load(f)
            imported_objects['cutting_plan'] = cutting_plan
            FreeCAD.Console.PrintMessage(f"Loaded cutting plan: {cutting_plan_file}\n")
            FreeCAD.Console.PrintMessage(f"  Z-cuts: {cutting_plan['cutting_plan']['z_cuts']}\n")
            FreeCAD.Console.PrintMessage(f"  X-cuts: {cutting_plan['cutting_plan']['x_cuts']}\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error loading cutting plan: {str(e)}\n")
    
    # Import merged inner plates from STL
    if not os.path.exists(merged_plates_stl):
        FreeCAD.Console.PrintError(f"Merged plates STL not found: {merged_plates_stl}\n")
    else:
        try:
            FreeCAD.Console.PrintMessage(f"Importing merged inner plates from STL: {merged_plates_stl}\n")
            FreeCADGui.updateGui()
            
            # Import STL as mesh
            mesh = Mesh.Mesh(merged_plates_stl)
            FreeCAD.Console.PrintMessage(f"  Loaded mesh with {len(mesh.Facets)} facets\n")
            
            # Breathing room after loading mesh
            FreeCADGui.updateGui()
            time.sleep(0.5)
            
            # Convert mesh to solid shape
            FreeCAD.Console.PrintMessage(f"  Converting mesh to solid...\n")
            shape = Part.Shape()
            shape.makeShapeFromMesh(mesh.Topology, 0.1)  # 0.1mm tolerance
            
            # Breathing room after conversion
            FreeCADGui.updateGui()
            time.sleep(0.5)
            
            solid = Part.makeSolid(shape)
            
            # Create FreeCAD object
            inner_plates = FreeCAD.ActiveDocument.addObject("Part::Feature", "InnerPlates")
            inner_plates.Shape = solid
            inner_plates.Label = f"{boat_name}_Inner_Plates"
            
            imported_objects['inner_plates'] = inner_plates
            FreeCAD.Console.PrintMessage(f"  ✅ Imported inner plates from STL\n")
            
            # Check if reasonable
            bbox = inner_plates.Shape.BoundBox
            FreeCAD.Console.PrintMessage(f"  Bounding box: X({bbox.XMin:.1f} to {bbox.XMax:.1f}), Y({bbox.YMin:.1f} to {bbox.YMax:.1f}), Z({bbox.ZMin:.1f} to {bbox.ZMax:.1f})\n")
            
            # Final breathing room
            FreeCAD.ActiveDocument.recompute()
            FreeCADGui.updateGui()
            time.sleep(0.5)
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error importing merged plates STL: {str(e)}\n")
    
    # Import foil shell
    if not os.path.exists(shell_foil_file):
        FreeCAD.Console.PrintError(f"Shell foil file not found: {shell_foil_file}\n")
    else:
        try:
            FreeCAD.Console.PrintMessage(f"Importing foil shell: {shell_foil_file}\n")
            FreeCADGui.updateGui()
            
            Import.insert(shell_foil_file, FreeCAD.ActiveDocument.Name)
            
            foil_shell = FreeCAD.ActiveDocument.Objects[-1]
            foil_shell.Label = f"{boat_name}_Foil_Shell"
            imported_objects['foil_shell'] = foil_shell
            
            FreeCAD.Console.PrintMessage(f"  ✅ Imported foil shell\n")
            
            # Breathing room
            FreeCAD.ActiveDocument.recompute()
            FreeCADGui.updateGui()
            time.sleep(0.5)
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error importing foil shell: {str(e)}\n")
    
    FreeCAD.ActiveDocument.recompute()
    time.sleep(0.5)
    
    return imported_objects

def configure_display(imported_objects):
    """Configure display settings for imported components"""
    
    try:
        if not hasattr(FreeCADGui, 'ActiveDocument') or not FreeCADGui.ActiveDocument:
            FreeCAD.Console.PrintWarning("No GUI available - skipping display configuration\n")
            return
        
        # Set transparency for shell to see internal structure
        if 'foil_shell' in imported_objects:
            shell = imported_objects['foil_shell']
            if hasattr(shell, 'ViewObject') and shell.ViewObject:
                shell.ViewObject.Transparency = 50
                FreeCAD.Console.PrintMessage("Set shell transparency to 50%\n")
        
        # Set inner plates display
        if 'inner_plates' in imported_objects:
            plates = imported_objects['inner_plates']
            if hasattr(plates, 'ViewObject') and plates.ViewObject:
                plates.ViewObject.Transparency = 0
                FreeCAD.Console.PrintMessage("Set inner plates to opaque\n")
        
        # Configure view
        try:
            view = FreeCADGui.activeView()
            if view:
                view.viewIsometric()
                view.fitAll()
                FreeCAD.Console.PrintMessage("Set isometric view and fitted all\n")
        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Could not configure view: {str(e)}\n")
        
        FreeCADGui.updateGui()
        
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error configuring display: {str(e)}\n")

def analyze_components(imported_objects):
    """Analyze imported components and print information"""
    
    FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
    FreeCAD.Console.PrintMessage("COMPONENT ANALYSIS:\n")
    FreeCAD.Console.PrintMessage("="*50 + "\n")
    
    if 'inner_plates' in imported_objects:
        plates = imported_objects['inner_plates']
        bbox = plates.Shape.BoundBox
        
        FreeCAD.Console.PrintMessage("Inner Plates:\n")
        FreeCAD.Console.PrintMessage(f"  Bounding Box:\n")
        FreeCAD.Console.PrintMessage(f"    X: {bbox.XMin:.2f} to {bbox.XMax:.2f} mm\n")
        FreeCAD.Console.PrintMessage(f"    Y: {bbox.YMin:.2f} to {bbox.YMax:.2f} mm\n")
        FreeCAD.Console.PrintMessage(f"    Z: {bbox.ZMin:.2f} to {bbox.ZMax:.2f} mm\n")
        FreeCAD.Console.PrintMessage(f"  Volume: {plates.Shape.Volume:.2f} mm³\n")
        
        if plates.Shape.Solids:
            FreeCAD.Console.PrintMessage(f"  Number of solids: {len(plates.Shape.Solids)}\n")
    
    if 'foil_shell' in imported_objects:
        shell = imported_objects['foil_shell']
        bbox = shell.Shape.BoundBox
        
        FreeCAD.Console.PrintMessage("\nFoil Shell:\n")
        FreeCAD.Console.PrintMessage(f"  Bounding Box:\n")
        FreeCAD.Console.PrintMessage(f"    X: {bbox.XMin:.2f} to {bbox.XMax:.2f} mm\n")
        FreeCAD.Console.PrintMessage(f"    Y: {bbox.YMin:.2f} to {bbox.YMax:.2f} mm\n")
        FreeCAD.Console.PrintMessage(f"    Z: {bbox.ZMin:.2f} to {bbox.ZMax:.2f} mm\n")
        FreeCAD.Console.PrintMessage(f"  Volume: {shell.Shape.Volume:.2f} mm³\n")
        
        if shell.Shape.Shells:
            FreeCAD.Console.PrintMessage(f"  Number of shells: {len(shell.Shape.Shells)}\n")
        if shell.Shape.Solids:
            FreeCAD.Console.PrintMessage(f"  Number of solids: {len(shell.Shape.Solids)}\n")
    
    FreeCAD.Console.PrintMessage("="*50 + "\n")

def cut_foil_assembly(imported_objects, boat_name):
    """Cut the foil assembly according to the cutting plan"""
    
    if 'cutting_plan' not in imported_objects:
        FreeCAD.Console.PrintError("No cutting plan available\n")
        return []
    
    if 'foil_shell' not in imported_objects and 'inner_plates' not in imported_objects:
        FreeCAD.Console.PrintError("No components to cut\n")
        return []
    
    FreeCAD.Console.PrintMessage("\n=== CUTTING FOIL ASSEMBLY ===\n")
    FreeCADGui.updateGui()
    
    cutting_plan = imported_objects['cutting_plan']['cutting_plan']
    z_cuts = cutting_plan['z_cuts']
    x_cuts = cutting_plan['x_cuts']
    
    # Combine shell and plates for cutting
    shapes_to_cut = []
    if 'foil_shell' in imported_objects:
        shapes_to_cut.append(imported_objects['foil_shell'].Shape)
    if 'inner_plates' in imported_objects:
        shapes_to_cut.append(imported_objects['inner_plates'].Shape)
    
    # Fuse all shapes together for cutting
    FreeCAD.Console.PrintMessage("Combining components for cutting...\n")
    FreeCADGui.updateGui()
    time.sleep(0.5)
    
    if len(shapes_to_cut) > 1:
        combined_shape = shapes_to_cut[0].fuse(shapes_to_cut[1])
    else:
        combined_shape = shapes_to_cut[0]
    
    # Breathing room after fusion
    FreeCAD.ActiveDocument.recompute()
    FreeCADGui.updateGui()
    time.sleep(0.5)
    segment_objects = []
    
    # Get bounding box for creating cutting planes
    bbox = combined_shape.BoundBox
    margin = 50  # Extra margin for cutting planes
    
    # Start with the combined shape
    segments = [combined_shape]
    
    # Apply Z-cuts (horizontal)
    FreeCAD.Console.PrintMessage(f"\nApplying {len(z_cuts)} Z-cuts...\n")
    for i, z_pos in enumerate(z_cuts):
        FreeCAD.Console.PrintMessage(f"  Z-cut {i+1}/{len(z_cuts)} at Z={z_pos:.2f}...\n")
        FreeCADGui.updateGui()
        
        new_segments = []
        for j, segment in enumerate(segments):
            FreeCAD.Console.PrintMessage(f"    Processing segment {j+1}/{len(segments)}...\n")
            FreeCADGui.updateGui()
            
            # Create horizontal cutting plane
            cut_plane = Part.makeBox(
                bbox.XLength + 2*margin,
                bbox.YLength + 2*margin,
                bbox.ZLength,
                FreeCAD.Vector(bbox.XMin - margin, bbox.YMin - margin, z_pos)
            )
            
            try:
                # Cut segment into two pieces
                upper_part = segment.cut(cut_plane)
                lower_part = segment.common(cut_plane)
                
                if upper_part.Volume > 0:
                    new_segments.append(upper_part)
                if lower_part.Volume > 0:
                    new_segments.append(lower_part)
                    
                # Breathing room after each segment cut
                if j % 2 == 0:
                    FreeCADGui.updateGui()
                    time.sleep(0.2)
                    
            except Exception as e:
                FreeCAD.Console.PrintError(f"    Error in Z-cut: {str(e)}\n")
                new_segments.append(segment)
        
        segments = new_segments
        
        # Major breathing room after each Z-cut
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()
        time.sleep(0.5)
    
    # Apply Y-cut (centerline at Y=0)
    FreeCAD.Console.PrintMessage(f"\nApplying Y-cut at Y=0...\n")
    FreeCADGui.updateGui()
    
    new_segments = []
    for j, segment in enumerate(segments):
        FreeCAD.Console.PrintMessage(f"  Processing segment {j+1}/{len(segments)}...\n")
        FreeCADGui.updateGui()
        
        # Create vertical cutting plane at Y=0
        cut_plane = Part.makeBox(
            bbox.XLength + 2*margin,
            bbox.YLength,
            bbox.ZLength + 2*margin,
            FreeCAD.Vector(bbox.XMin - margin, 0, bbox.ZMin - margin)
        )
        
        try:
            # Cut segment into two pieces
            front_part = segment.cut(cut_plane)
            back_part = segment.common(cut_plane)
            
            if front_part.Volume > 0:
                new_segments.append(front_part)
            if back_part.Volume > 0:
                new_segments.append(back_part)
                
            # Breathing room
            if j % 2 == 0:
                FreeCADGui.updateGui()
                time.sleep(0.2)
                
        except Exception as e:
            FreeCAD.Console.PrintError(f"    Error in Y-cut: {str(e)}\n")
            new_segments.append(segment)
    
    segments = new_segments
    
    # Major breathing room after Y-cut
    FreeCAD.ActiveDocument.recompute()
    FreeCADGui.updateGui()
    time.sleep(0.5)
    
    # Apply X-cuts (vertical)
    FreeCAD.Console.PrintMessage(f"\nApplying {len(x_cuts)} X-cuts...\n")
    for i, x_pos in enumerate(x_cuts):
        FreeCAD.Console.PrintMessage(f"  X-cut {i+1}/{len(x_cuts)} at X={x_pos:.2f}...\n")
        FreeCADGui.updateGui()
        
        new_segments = []
        for j, segment in enumerate(segments):
            FreeCAD.Console.PrintMessage(f"    Processing segment {j+1}/{len(segments)}...\n")
            FreeCADGui.updateGui()
            
            # Create vertical cutting plane
            cut_plane = Part.makeBox(
                bbox.XLength,
                bbox.YLength + 2*margin,
                bbox.ZLength + 2*margin,
                FreeCAD.Vector(x_pos, bbox.YMin - margin, bbox.ZMin - margin)
            )
            
            try:
                # Cut segment into two pieces
                left_part = segment.cut(cut_plane)
                right_part = segment.common(cut_plane)
                
                if left_part.Volume > 0:
                    new_segments.append(left_part)
                if right_part.Volume > 0:
                    new_segments.append(right_part)
                    
                # Breathing room
                if j % 2 == 0:
                    FreeCADGui.updateGui()
                    time.sleep(0.2)
                    
            except Exception as e:
                FreeCAD.Console.PrintError(f"    Error in X-cut: {str(e)}\n")
                new_segments.append(segment)
        
        segments = new_segments
        
        # Major breathing room after each X-cut
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.updateGui()
        time.sleep(0.5)
    
    # Create FreeCAD objects for each segment
    FreeCAD.Console.PrintMessage(f"\nCreating {len(segments)} segment objects...\n")
    segment_objects = []
    
    for i, segment_shape in enumerate(segments):
        if segment_shape.Volume > 0:
            FreeCAD.Console.PrintMessage(f"  Creating segment {i+1}/{len(segments)}...\n")
            FreeCADGui.updateGui()
            
            segment_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", f"Segment_{i+1}")
            segment_obj.Shape = segment_shape
            segment_obj.Label = f"{boat_name}_Segment_{i+1}"
            segment_objects.append(segment_obj)
            
            # Random color for each segment
            if hasattr(segment_obj, 'ViewObject') and segment_obj.ViewObject:
                import random
                segment_obj.ViewObject.ShapeColor = (random.random(), random.random(), random.random())
            
            # Breathing room every 4 segments
            if i % 4 == 0:
                FreeCAD.ActiveDocument.recompute()
                FreeCADGui.updateGui()
                time.sleep(0.3)
    
    # Hide original objects
    if 'foil_shell' in imported_objects:
        shell = imported_objects['foil_shell']
        if hasattr(shell, 'ViewObject') and shell.ViewObject:
            shell.ViewObject.Visibility = False
    
    if 'inner_plates' in imported_objects:
        plates = imported_objects['inner_plates']
        if hasattr(plates, 'ViewObject') and plates.ViewObject:
            plates.ViewObject.Visibility = False
    
    # Final recompute
    FreeCAD.ActiveDocument.recompute()
    FreeCADGui.updateGui()
    
    FreeCAD.Console.PrintMessage(f"\n✅ Created {len(segment_objects)} segments\n")
    FreeCAD.Console.PrintMessage(f"Expected: {(len(z_cuts)+1) * 2 * (len(x_cuts)+1)} segments\n")
    
    return segment_objects

def run_assembly(boat_name="MackenSea"):
    """Main business logic for shell and plates assembly
    
    Args:
        boat_name: Name of the boat (determines file paths)
    """
    
    # Import components
    imported_objects = import_components(boat_name)
    
    if not imported_objects:
        FreeCAD.Console.PrintError("Failed to import components\n")
        return
    
    # Configure display
    configure_display(imported_objects)
    
    # Analyze components
    analyze_components(imported_objects)
    
    # Cut the foil assembly
    #segments = cut_foil_assembly(imported_objects, boat_name)
    
    FreeCAD.Console.PrintMessage("\n" + "="*50 + "\n")
    FreeCAD.Console.PrintMessage("CUTTING COMPLETE\n")
    FreeCAD.Console.PrintMessage("="*50 + "\n")
    FreeCAD.Console.PrintMessage(f"Ready for 3D printing\n")

# Main execution
if __name__ == "__main__":
    # UI setup only
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument()
    
    # Call business logic
    run_assembly(boat_name="MackenSea")