"""
fill_V_final.py - Final solution for V-groove filling
Creates a completely smooth cutout shape by rebuilding geometry from scratch
"""

import FreeCAD
import Part
from FreeCAD import Base
import math

def fill_v_grooves(stock_object):
    """
    Aggressively fill V-grooves by creating a completely new smooth shape
    based on the stock's overall dimensions and structure
    """
    
    print("=" * 60)
    print("AGGRESSIVE V-GROOVE FILLING")
    print("=" * 60)
    
    # Get the shape
    if hasattr(stock_object, 'Shape'):
        shape = stock_object.Shape
    else:
        shape = stock_object
    
    # Get bounding box for overall dimensions
    bbox = shape.BoundBox
    print(f"Stock dimensions: {bbox.XLength:.1f} x {bbox.YLength:.1f} x {bbox.ZLength:.1f} mm")
    print(f"Z range: {bbox.ZMin:.1f} to {bbox.ZMax:.1f}")
    
    # Analyze the compound to understand its structure
    print(f"\nAnalyzing {len(shape.Solids)} solids...")
    
    # Find cylindrical and tapered sections
    cylinders = []
    max_radius = 0
    min_radius = float('inf')
    
    for solid in shape.Solids:
        for face in solid.Faces:
            if hasattr(face.Surface, 'Radius'):
                radius = face.Surface.Radius
                cylinders.append({
                    'radius': radius,
                    'z_min': face.BoundBox.ZMin,
                    'z_max': face.BoundBox.ZMax,
                    'center': face.Surface.Center
                })
                max_radius = max(max_radius, radius)
                min_radius = min(min_radius, radius)
    
    print(f"Found {len(cylinders)} cylindrical surfaces")
    print(f"Radius range: {min_radius:.1f} to {max_radius:.1f} mm")
    
    # METHOD 1: Create smooth tapered cylinder
    print("\n1. Creating smooth tapered cylinder...")
    try:
        # Determine if stock is tapered
        if abs(max_radius - min_radius) > 1.0:  # Tapered stock
            print(f"   Creating tapered cylinder: R1={max_radius:.1f}, R2={min_radius:.1f}")
            
            # Create a cone (tapered cylinder)
            # Find which end has which radius
            top_radius = max_radius
            bottom_radius = min_radius
            
            # Check actual orientation
            for cyl in cylinders:
                if cyl['z_max'] > bbox.ZMin + bbox.ZLength * 0.9:  # Near top
                    top_radius = cyl['radius']
                elif cyl['z_min'] < bbox.ZMin + bbox.ZLength * 0.1:  # Near bottom
                    bottom_radius = cyl['radius']
            
            # Create tapered cylinder
            smooth_cylinder = Part.makeCone(
                bottom_radius,  # radius at bottom
                top_radius,     # radius at top
                bbox.ZLength,   # height
                Base.Vector(0, 0, bbox.ZMin),  # position
                Base.Vector(0, 0, 1)  # direction
            )
        else:
            print(f"   Creating straight cylinder: R={max_radius:.1f}")
            smooth_cylinder = Part.makeCylinder(
                max_radius,
                bbox.ZLength,
                Base.Vector(0, 0, bbox.ZMin),
                Base.Vector(0, 0, 1)
            )
        
        # METHOD 2: Add smooth plates (fins) without V-grooves
        print("\n2. Adding smooth plate features...")
        
        # Find rectangular/plate features
        plates = []
        for solid in shape.Solids:
            solid_bbox = solid.BoundBox
            
            # Check if this solid extends significantly from center
            center_dist = math.sqrt(solid_bbox.Center.x**2 + solid_bbox.Center.y**2)
            
            if center_dist > max_radius * 0.5:  # This is likely a plate/fin
                print(f"   Found plate at distance {center_dist:.1f} from center")
                
                # Create simplified box for this plate
                # Make it slightly thicker to ensure no gaps
                thickness = max(solid_bbox.XLength, solid_bbox.YLength) * 0.3
                
                # Determine plate orientation and create appropriate box
                if abs(solid_bbox.Center.x) > abs(solid_bbox.Center.y):
                    # Plate extends in X direction
                    plate_box = Part.makeBox(
                        solid_bbox.XLength,
                        thickness,
                        solid_bbox.ZLength,
                        Base.Vector(
                            solid_bbox.XMin,
                            -thickness/2,
                            solid_bbox.ZMin
                        )
                    )
                else:
                    # Plate extends in Y direction
                    plate_box = Part.makeBox(
                        thickness,
                        solid_bbox.YLength,
                        solid_bbox.ZLength,
                        Base.Vector(
                            -thickness/2,
                            solid_bbox.YMin,
                            solid_bbox.ZMin
                        )
                    )
                
                plates.append(plate_box)
        
        # Combine cylinder with plates
        final_shape = smooth_cylinder
        for i, plate in enumerate(plates):
            try:
                print(f"   Fusing plate {i+1}/{len(plates)}")
                final_shape = final_shape.fuse(plate)
            except Exception as e:
                print(f"   Warning: Could not fuse plate {i+1}: {e}")
        
        # Clean up the final shape
        print("\n3. Cleaning up geometry...")
        final_shape = final_shape.removeSplitter()
        
        # Create the filled object
        doc = FreeCAD.ActiveDocument
        if doc:
            # Remove old attempts if they exist
            for name in ["FilledStock_Smooth", "FilledStock_Method1", "FilledStock_Envelope"]:
                if doc.getObject(name):
                    doc.removeObject(name)
            
            filled_object = doc.addObject("Part::Feature", "FilledStock_Smooth")
            filled_object.Shape = final_shape
            
            # Set visual properties to make it clearly different
            if hasattr(filled_object, 'ViewObject'):
                filled_object.ViewObject.ShapeColor = (0.0, 1.0, 0.0)  # Green
                filled_object.ViewObject.Transparency = 30  # Semi-transparent
            
            doc.recompute()
            
            print("\n" + "=" * 60)
            print("SUCCESS! Created FilledStock_Smooth")
            print("The object is colored GREEN for easy identification")
            print(f"Original faces: {len(shape.Faces)}")
            print(f"Smooth faces: {len(final_shape.Faces)}")
            print(f"V-grooves removed: ~{len(shape.Faces) - len(final_shape.Faces)}")
            print("=" * 60)
            
            return filled_object
            
    except Exception as e:
        print(f"Error in smooth creation: {e}")
    
    # FALLBACK: Create simplest possible smooth envelope
    print("\nFALLBACK: Creating simplest envelope...")
    try:
        # Just create a cylinder that encompasses everything
        max_extent = max(abs(bbox.XMin), abs(bbox.XMax), abs(bbox.YMin), abs(bbox.YMax))
        
        envelope = Part.makeCylinder(
            max_extent,
            bbox.ZLength,
            Base.Vector(0, 0, bbox.ZMin),
            Base.Vector(0, 0, 1)
        )
        
        doc = FreeCAD.ActiveDocument
        if doc:
            fallback_object = doc.addObject("Part::Feature", "FilledStock_Fallback")
            fallback_object.Shape = envelope
            
            if hasattr(fallback_object, 'ViewObject'):
                fallback_object.ViewObject.ShapeColor = (1.0, 1.0, 0.0)  # Yellow
                fallback_object.ViewObject.Transparency = 50
            
            doc.recompute()
            print("Created yellow fallback envelope")
            return fallback_object
            
    except Exception as e:
        print(f"Fallback also failed: {e}")
    
    return stock_object

def verify_filling(original, filled):
    """
    Compare original and filled to verify V-grooves are gone
    """
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    orig_shape = original.Shape if hasattr(original, 'Shape') else original
    fill_shape = filled.Shape if hasattr(filled, 'Shape') else filled
    
    print(f"Original object:")
    print(f"  - Faces: {len(orig_shape.Faces)}")
    print(f"  - Edges: {len(orig_shape.Edges)}")
    print(f"  - Solids: {len(orig_shape.Solids)}")
    
    print(f"\nFilled object:")
    print(f"  - Faces: {len(fill_shape.Faces)}")
    print(f"  - Edges: {len(fill_shape.Edges)}")
    print(f"  - Solids: {len(fill_shape.Solids)}")
    
    # Check for small faces (V-grooves are typically small)
    orig_small = sum(1 for f in orig_shape.Faces if f.Area < 100)
    fill_small = sum(1 for f in fill_shape.Faces if f.Area < 100)
    
    print(f"\nSmall faces (<100 mm²):")
    print(f"  - Original: {orig_small}")
    print(f"  - Filled: {fill_small}")
    
    if fill_small < orig_small:
        print("✓ V-grooves successfully removed!")
    else:
        print("⚠ V-grooves may still be present")
    
    print("=" * 60)

# Export the STEP file for the filled shape
def export_filled_step(filled_object, boat_name="MackenSea"):
    """
    Export the filled/smooth stock as STEP for CAD operations
    """
    import os
    
    shape = filled_object.Shape if hasattr(filled_object, 'Shape') else filled_object
    
    # Determine output path
    rudder_code_path = "/Users/andrewmackenzie/Rudder_Code"
    output_dir = os.path.join(rudder_code_path, "boats", boat_name, "output", "stock")
    
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Export STEP
    step_path = os.path.join(output_dir, f"{boat_name}_Cutout.step")
    shape.exportStep(step_path)
    print(f"\n✅ Exported cutout STEP: {step_path}")
    
    # Also export STL for visualization
    stl_path = os.path.join(output_dir, f"{boat_name}_Cutout.stl")
    shape.exportStl(stl_path)
    print(f"✅ Exported cutout STL: {stl_path}")

# Main execution
if __name__ == "__main__":
    if FreeCAD.ActiveDocument:
        sel = FreeCADGui.Selection.getSelection()
        if sel:
            stock = sel[0]
            print(f"Processing: {stock.Name}")
            
            # Fill the grooves
            filled = fill_v_grooves(stock)
            
            # Verify the filling
            verify_filling(stock, filled)
            
            # Export the result
            export_filled_step(filled)
            
        else:
            print("Please select a stock object first")
    else:
        print("No active document")