#!/usr/bin/env python3
"""
FreeCAD Macro: Lewmar Stripper Ring 45500408 - Step 4: Shaped Extension
Step 1: Base cylinder 85mm diameter, 15mm height
Step 2: Add trapezoid extending from cylinder
Step 3: Add small nib at trapezoid end  
Step 4: Merge and shape with varying thickness (2mm to 7mm)
Author: Generated for 3D Printing
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
    base_diameter = 85.0    # 85mm diameter
    base_radius = base_diameter / 2  # 42.5mm radius
    base_depth = 15.0       # 15mm deep (DO NOT CHANGE)
    
    print("Step 1: Creating base cylinder...")
    print(f"Diameter: {base_diameter}mm")
    print(f"Radius: {base_radius}mm") 
    print(f"Depth: {base_depth}mm")
    
    # Create solid cylinder
    base_cylinder = Part.makeCylinder(base_radius, base_depth)
    
    # Create base cylinder object
    cylinder_obj = doc.addObject("Part::Feature", "Base_Cylinder")
    cylinder_obj.Shape = base_cylinder
    cylinder_obj.Label = "Base Cylinder"
    
    # Step 2: Trapezoid (CORRECTED dimensions, ORIGINAL orientation)
    trapezoid_width_bottom = 85.0   # Bottom width matches cylinder diameter
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
    print("Ready for next step - what should we add next?")
    
    return cylinder_obj, shaped_obj, cut_tool_obj

# Run the macro
if __name__ == "__main__":
    # Create the base with shaped extension - Steps 1-4
    cylinder_object, shaped_object, cutting_tool = create_base_with_shaped_extension()