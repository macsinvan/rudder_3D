#!/usr/bin/env python3
"""
FreeCAD Macro: Lewmar Stripper Ring 45500408 - Complete Model
Step 1: Base cylinder 85mm diameter, 15mm height
Step 2: Add trapezoid extending from cylinder
Step 3: Add small nib at trapezoid end  
Step 4: Merge and shape with varying thickness (2mm to 7mm)
Step 5: Add "TOP" engraving
Step 6: Create final merged object
Step 7: Export STL for 3D printing
Author: Generated for 3D Printing
Recommended Materials: ASA, PETG, or Nylon for marine applications
"""

import FreeCAD as App
import Part
import math

def create_base_with_shaped_extension():
    """
    Create the base cylinder plus shaped trapezoid+nib - Steps 1-4 (separate objects)
    Base: 85mm diameter x 15mm height
    Shaped Extension: Merged trapezoid+nib with varying thickness (2mm to 7mm)
    """
    
    # Create new document
    doc = App.newDocument("Lewmar_Stripper_Ring_Step4")
    
    # Step 1: Base cylinder dimensions (CORRECTED - back to original)
    base_diameter = 86.0    # 86mm diameter
    base_radius = base_diameter / 2  # 42.5mm radius
    base_depth = 15.0       # 15mm deep (DO NOT CHANGE)
    
    print("Step 1: Creating base cylinder...")
    print(f"Diameter: {base_diameter}mm")
    print(f"Radius: {base_radius}mm") 
    print(f"Depth: {base_depth}mm")
    
    # Create solid cylinder
    base_cylinder = Part.makeCylinder(base_radius, base_depth)
    
    print(f"Solid cylinder created")
    
    # Create base cylinder object
    cylinder_obj = doc.addObject("Part::Feature", "Base_Cylinder")
    cylinder_obj.Shape = base_cylinder
    cylinder_obj.Label = "Base Cylinder"
    
    # Step 2: Trapezoid (CORRECTED dimensions, ORIGINAL orientation)
    trapezoid_width_bottom = base_diameter   # Bottom width matches cylinder diameter
    trapezoid_width_top = 30.0      # Top width 30mm
    trapezoid_length = base_radius + 25.0  # Length = radius + 25 = 67.5mm
    trapezoid_thickness = 7.0       # 7mm thick
    
    print("Step 2: Creating trapezoid...")
    print(f"Bottom width: {trapezoid_width_bottom}mm")
    print(f"Top width: {trapezoid_width_top}mm")
    print(f"Length: {trapezoid_length}mm")
    print(f"Thickness: {trapezoid_thickness}mm")
    
    # Create trapezoid extending from NEGATIVE Y side of cylinder
    # Start at Y = -radius, extend outward in negative Y direction
    start_y = -base_radius  # Start at Y = -42.5mm
    end_y = start_y + trapezoid_length  # Extend 67.5mm toward positive Y
    
    print(f"Trapezoid Y range: {start_y}mm to {end_y}mm")
    
    # Create trapezoid vertices - extending from -Y side of cylinder
    p1 = App.Vector(-trapezoid_width_bottom/2, start_y, 0)    # Bottom left at cylinder
    p2 = App.Vector(trapezoid_width_bottom/2, start_y, 0)     # Bottom right at cylinder
    p3 = App.Vector(trapezoid_width_top/2, end_y, 0)          # Top right at end
    p4 = App.Vector(-trapezoid_width_top/2, end_y, 0)         # Top left at end
    
    # Create the trapezoid face
    trapezoid_wire = Part.makePolygon([p1, p2, p3, p4, p1])
    trapezoid_face = Part.Face(trapezoid_wire)
    
    # Extrude the trapezoid to create the 3D shape (7mm thick in Z direction)
    trapezoid_solid = trapezoid_face.extrude(App.Vector(0, 0, trapezoid_thickness))
    
    # Position trapezoid with top edge 5.5mm down from cylinder top
    z_offset = base_depth - 5.5 - trapezoid_thickness  # Top edge at 9.5mm, bottom at 2.5mm
    trapezoid_solid.translate(App.Vector(0, 0, z_offset))
    
    # Fix trapezoid position as provided
    trapezoid_solid.translate(App.Vector(0, base_radius, 0))
    
    # Create separate trapezoid object (DO NOT MERGE)
    trapezoid_obj = doc.addObject("Part::Feature", "Trapezoid")
    trapezoid_obj.Shape = trapezoid_solid
    trapezoid_obj.Label = "Trapezoid"
    
    # Step 3: Small nib at trapezoid end
    nib_width = 14.0    # 14mm wide
    nib_depth = 5.0     # 5mm deep
    nib_thickness = trapezoid_thickness  # Same as trapezoid (7mm)
    
    print("Step 3: Creating nib at trapezoid end...")
    print(f"Nib width: {nib_width}mm")
    print(f"Nib depth: {nib_depth}mm")
    print(f"Nib thickness: {nib_thickness}mm")
    
    # Calculate nib position - at the far end of trapezoid
    nib_start_y = end_y  # Start where trapezoid ends
    nib_end_y = nib_start_y + nib_depth  # Extend 5mm further
    
    # Create nib vertices - centered on trapezoid end (30mm -> 14mm centered)
    n1 = App.Vector(-nib_width/2, nib_start_y, 0)    # Left at trapezoid end
    n2 = App.Vector(nib_width/2, nib_start_y, 0)     # Right at trapezoid end
    n3 = App.Vector(nib_width/2, nib_end_y, 0)       # Right at nib end
    n4 = App.Vector(-nib_width/2, nib_end_y, 0)      # Left at nib end
    
    # Create the nib face
    nib_wire = Part.makePolygon([n1, n2, n3, n4, n1])
    nib_face = Part.Face(nib_wire)
    
    # Extrude the nib to create the 3D shape (7mm thick in Z direction)
    nib_solid = nib_face.extrude(App.Vector(0, 0, nib_thickness))
    
    # Position nib same as trapezoid
    nib_solid.translate(App.Vector(0, 0, z_offset))
    nib_solid.translate(App.Vector(0, base_radius, 0))
    
    # Create separate nib object (DO NOT MERGE)
    nib_obj = doc.addObject("Part::Feature", "Nib")
    nib_obj.Shape = nib_solid
    nib_obj.Label = "Nib"
    
    # Step 4: Merge trapezoid and nib, then apply varying thickness cut
    print("Step 4: Merging trapezoid and nib...")
    merged_shape = trapezoid_solid.fuse(nib_solid)
    
    print("Step 4: Applying varying thickness cut...")
    # Create cutting solid for varying thickness (2mm at start to 7mm at end)
    # Current thickness is 7mm, need to cut 5mm at start, 0mm at end
    
    # Get the Y range of the merged shape
    cut_start_y = -base_radius  # Start of trapezoid
    cut_end_y = end_y + nib_depth  # End of nib
    cut_length = cut_end_y - cut_start_y
    
    # Create cutting profile that varies from 5mm cut to 0mm cut
    cut_points = []
    num_points = 20  # Number of points for smooth curve
    for i in range(num_points + 1):
        y_pos = cut_start_y + (i / num_points) * cut_length
        # Linear interpolation from 5mm cut to 0mm cut
        cut_height = 5.0 * (1 - i / num_points)
        cut_z = z_offset + cut_height  # Bottom of cut
        cut_points.append(App.Vector(0, y_pos, cut_z))
    
    # Add points to complete the cutting profile
    # Top edge (constant at original bottom)
    for i in range(num_points, -1, -1):
        y_pos = cut_start_y + (i / num_points) * cut_length
        cut_points.append(App.Vector(0, y_pos, z_offset))
    
    # Create cutting wire and face
    cut_wire = Part.makePolygon(cut_points + [cut_points[0]])
    cut_face = Part.Face(cut_wire)
    
    # Extrude cutting face to cover full width
    cut_solid = cut_face.extrude(App.Vector(trapezoid_width_bottom + 10, 0, 0))
    cut_solid.translate(App.Vector(-(trapezoid_width_bottom + 10)/2, 0, 0))
    
    # Apply same positioning as trapezoid/nib
    cut_solid.translate(App.Vector(0, base_radius, 0))
    
    # Cut the merged shape
    shaped_solid = merged_shape.cut(cut_solid)
    
    # Create final shaped object
    shaped_obj = doc.addObject("Part::Feature", "Shaped_Trapezoid_Nib")
    shaped_obj.Shape = shaped_solid
    shaped_obj.Label = "Shaped Trapezoid+Nib"
    
    # Create cutting tool object for visual inspection
    cut_tool_obj = doc.addObject("Part::Feature", "Cutting_Tool")
    cut_tool_obj.Shape = cut_solid
    cut_tool_obj.Label = "Cutting Tool"
    
    # Set different colors for the parts
    if App.GuiUp:
        # Base cylinder in blue
        cylinder_obj.ViewObject.ShapeColor = (0.3, 0.3, 0.8)
        cylinder_obj.ViewObject.Transparency = 0
        cylinder_obj.ViewObject.DisplayMode = "Shaded"
        
        # Hide original trapezoid and nib (now merged)
        trapezoid_obj.ViewObject.Visibility = False
        nib_obj.ViewObject.Visibility = False
        
        # Shaped combined object in orange
        shaped_obj.ViewObject.ShapeColor = (0.8, 0.6, 0.2)
        shaped_obj.ViewObject.Transparency = 0
        shaped_obj.ViewObject.DisplayMode = "Shaded"
        
        # Cutting tool in red for visibility
        cut_tool_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
        cut_tool_obj.ViewObject.Transparency = 30
        cut_tool_obj.ViewObject.DisplayMode = "Shaded"
    
    # Add properties for documentation
    cylinder_obj.addProperty("App::PropertyString", "Step", "Info", "Build step")
    cylinder_obj.addProperty("App::PropertyFloat", "Diameter", "Dimensions", "Diameter in mm")
    cylinder_obj.addProperty("App::PropertyFloat", "Depth", "Dimensions", "Depth in mm")
    
    trapezoid_obj.addProperty("App::PropertyString", "Step", "Info", "Build step")
    trapezoid_obj.addProperty("App::PropertyFloat", "BottomWidth", "Dimensions", "Bottom width in mm")
    trapezoid_obj.addProperty("App::PropertyFloat", "TopWidth", "Dimensions", "Top width in mm")
    trapezoid_obj.addProperty("App::PropertyFloat", "Length", "Dimensions", "Length in mm")
    trapezoid_obj.addProperty("App::PropertyFloat", "Thickness", "Dimensions", "Thickness in mm")
    
    nib_obj.addProperty("App::PropertyString", "Step", "Info", "Build step")
    nib_obj.addProperty("App::PropertyFloat", "Width", "Dimensions", "Width in mm")
    nib_obj.addProperty("App::PropertyFloat", "Depth", "Dimensions", "Depth in mm")
    nib_obj.addProperty("App::PropertyFloat", "Thickness", "Dimensions", "Thickness in mm")
    
    shaped_obj.addProperty("App::PropertyString", "Step", "Info", "Build step")
    shaped_obj.addProperty("App::PropertyString", "Description", "Info", "Component description")
    
    cylinder_obj.Step = "1 - Base Cylinder"
    cylinder_obj.Diameter = base_diameter
    cylinder_obj.Depth = base_depth
    
    trapezoid_obj.Step = "2 - Trapezoid (hidden)"
    trapezoid_obj.BottomWidth = trapezoid_width_bottom
    trapezoid_obj.TopWidth = trapezoid_width_top
    trapezoid_obj.Length = trapezoid_length
    trapezoid_obj.Thickness = trapezoid_thickness
    
    nib_obj.Step = "3 - Nib (hidden)"
    nib_obj.Width = nib_width
    nib_obj.Depth = nib_depth
    nib_obj.Thickness = nib_thickness
    
    shaped_obj.Step = "4 - Shaped Trapezoid+Nib"
    shaped_obj.Description = "Merged with varying thickness (2mm to 7mm)"
    
    # Recompute document
    doc.recompute()
    
    # Fit view
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.SendMsgToActiveView("ViewFit")
    
    print("Base cylinder and shaped trapezoid+nib created successfully!")
    print("Shaped component has varying thickness: 2mm to 7mm")
    
    # Step 5: Add "TOP" engraving
    print("Step 5: Adding TOP engraving...")
    
    # Text parameters
    text_content = "TOP"
    text_height = 4.0  # 4mm high letters
    text_depth = 0.5   # Engraving depth
    
    # Position 16mm down from end of nib
    text_y_pos = nib_end_y - 16.0  # 16mm back from nib end
    text_z_pos = z_offset + trapezoid_thickness - text_depth  # Position for engraving INTO surface
    
    print(f"Text position: Y={text_y_pos}mm, Z={text_z_pos}mm")
    
    # Create text geometry
    text_obj = doc.addObject("Part::Feature", "TOP_Text")
    
    # Create simple block letters for "TOP" (since FreeCAD text can be complex)
    # Create as extruded rectangles for each letter
    
    # Letter spacing and positioning
    letter_width = 2.5
    letter_spacing = 3.5
    total_width = 3 * letter_width + 2 * (letter_spacing - letter_width)  # Approximate
    
    # Create "T"
    t_horizontal = Part.makeBox(letter_width, 0.8, text_height)
    t_horizontal.translate(App.Vector(0, letter_width - 0.8, 0))  # Move horizontal bar to top
    t_vertical = Part.makeBox(0.8, letter_width, text_height)
    t_letter = t_horizontal.fuse(t_vertical.translate(App.Vector((letter_width-0.8)/2, 0, 0)))
    
    # Create "O" 
    o_outer = Part.makeBox(letter_width, letter_width, text_height)
    o_inner = Part.makeBox(letter_width-1.0, letter_width-1.0, text_height + 1)
    o_inner.translate(App.Vector(0.5, 0.5, -0.5))
    o_letter = o_outer.cut(o_inner)
    o_letter.translate(App.Vector(letter_spacing, 0, 0))
    
    # Create "P"
    p_vertical = Part.makeBox(0.8, letter_width, text_height)
    p_horizontal1 = Part.makeBox(letter_width-0.8, 0.8, text_height)
    p_horizontal1.translate(App.Vector(0.8, letter_width-0.8, 0))
    p_horizontal2 = Part.makeBox(letter_width-0.8, 0.8, text_height)
    p_horizontal2.translate(App.Vector(0.8, (letter_width-0.8)/2, 0))
    p_letter = p_vertical.fuse(p_horizontal1).fuse(p_horizontal2)
    p_letter.translate(App.Vector(2 * letter_spacing, 0, 0))
    
    # Combine all letters
    top_text = t_letter.fuse(o_letter).fuse(p_letter)
    
    # Position the text
    top_text.translate(App.Vector(-total_width/2, text_y_pos, text_z_pos))
    top_text.translate(App.Vector(0, base_radius, 0))  # Apply same translation as other objects
    
    # Assign geometry to text object
    text_obj.Shape = top_text
    text_obj.Label = "TOP Text"
    
    # Make text visible in green
    if App.GuiUp:
        text_obj.ViewObject.ShapeColor = (0.2, 0.8, 0.2)
        text_obj.ViewObject.Transparency = 0
        text_obj.ViewObject.DisplayMode = "Shaded"
    
    # Create engraving by cutting text from shaped object
    engraved_solid = shaped_solid.cut(top_text)
    
    # Update the shaped object with engraving
    shaped_obj.Shape = engraved_solid
    
    print("TOP engraving added successfully!")
    
    # Step 6: Create final merged object
    print("Step 6: Creating final merged object...")
    final_merged = cylinder_obj.Shape.fuse(shaped_obj.Shape)
    
    # Cut inner hole through entire merged shape to create ring
    print("Cutting inner hole to create ring...")
    inner_radius = base_radius - 3.7  # 42.5 - 3.7 = 38.8mm
    inner_cylinder = Part.makeCylinder(inner_radius, base_depth + 2)  # Slightly taller to ensure clean cut
    inner_cylinder.translate(App.Vector(0, 0, -1))  # Center the cut
    
    final_merged = final_merged.cut(inner_cylinder)
    print(f"Ring inner radius: {inner_radius}mm")
    
    # Add light chamfer on all edges
    print("Adding light chamfer on all edges...")
    try:
        chamfer_radius = 0.2  # Very light 0.2mm chamfer
        edges_to_chamfer = []
        for edge in final_merged.Edges:
            if edge.Length > 1.0:  # Only chamfer edges longer than 1mm
                edges_to_chamfer.append(edge)
        
        if edges_to_chamfer:
            final_merged = final_merged.makeFillet(chamfer_radius, edges_to_chamfer)
            print(f"Applied {chamfer_radius}mm chamfer to {len(edges_to_chamfer)} edges")
    except:
        print("Chamfering failed, using original shape")
    
    # Create final object
    final_obj = doc.addObject("Part::Feature", "Lewmar_Stripper_Ring_Final")
    final_obj.Shape = final_merged
    final_obj.Label = "Lewmar Stripper Ring 45500408 - Final"
    
    # Set final object color
    if App.GuiUp:
        final_obj.ViewObject.ShapeColor = (0.2, 0.2, 0.2)  # Dark gray like original
        final_obj.ViewObject.Transparency = 0
        final_obj.ViewObject.DisplayMode = "Shaded"
        
        # Hide individual components
        cylinder_obj.ViewObject.Visibility = False
        shaped_obj.ViewObject.Visibility = False
    
    # Step 7: Export STL
    print("Step 7: Exporting STL...")
    
    import os
    import Mesh
    from datetime import datetime
    
    # Get downloads folder with timestamped filename
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stl_filename = os.path.join(downloads_path, f"Lewmar_Stripper_Ring_45500408_{timestamp}.stl")
    
    # Create mesh from final shape
    mesh = Mesh.Mesh()
    mesh.addFacets(final_obj.Shape.tessellate(0.1))  # 0.1mm tolerance for good quality
    
    # Export STL
    mesh.write(stl_filename)
    
    print(f"STL exported to: {stl_filename}")
    print(f"File size: {len(mesh.Facets)} triangles")
    
    # Print material recommendations
    print("\n" + "="*50)
    print("3D PRINTING RECOMMENDATIONS:")
    print("="*50)
    print("RECOMMENDED MATERIAL: PLA CF (Carbon Fiber)")
    print("- BEST CHOICE for marine applications")
    print("- Excellent strength-to-weight ratio")
    print("- Carbon fiber reinforcement provides stiffness")
    print("- Good chemical resistance when properly printed")
    print("- Cost-effective compared to specialty marine filaments")
    print("\nPRINT SETTINGS FOR PLA CF:")
    print("- Layer Height: 0.15-0.2mm")
    print("- Infill: 80-100% for marine strength requirements")
    print("- Nozzle Temp: 210-230°C")
    print("- Bed Temp: 60-70°C")
    print("- Print Speed: 30-50mm/s")
    print("- Supports: Yes (for trapezoid overhangs)")
    print("- Orientation: Ring flat on bed")
    print("\nPOST-PROCESSING:")
    print("- Sand contact surfaces smooth (400-800 grit)")
    print("- Consider marine-grade protective coating")
    print("- Test fit before final installation")
    print("\nMARINE APPLICATION NOTES:")
    print("- PLA CF offers optimal balance of strength and printability")
    print("- Superior to standard PLA for marine hardware")
    print("- Monitor for wear in high-stress applications")
    print("="*50)
    
    print("Final Lewmar Stripper Ring model completed!")
    print("Ready for 3D printing!")
    
    return cylinder_obj, shaped_obj, cut_tool_obj, final_obj

# Run the macro
if __name__ == "__main__":
    # Create the base with shaped extension - Steps 1-7 (Complete)
    cylinder_object, shaped_object, cutting_tool, final_object = create_base_with_shaped_extension()