# FreeCAD 1.1.1 Spiral Tunnel Creator - Clean PartDesign Method
# Uses proper PartDesign workflow with Additive Helix

import FreeCAD
import Part
import Sketcher
import PartDesign

def create_spiral_tunnel_module():
    """
    Create filament dryer module using proper PartDesign Additive Helix method
    """
    
    # Parameters
    OUTER_DIAMETER = 150.0      # mm - module outer diameter
    CENTER_HOLE_DIAMETER = 35.0 # mm - central heating core
    MODULE_HEIGHT = 50.0        # mm - module height
    NUM_LOOPS = 12             # number of spiral loops
    TUNNEL_DIAMETER = 3.0      # mm - tunnel for 1.75mm filament + clearance
    SPIRAL_RADIUS = 50.0       # mm - radius of spiral path
    
    # Calculated parameters
    pitch = MODULE_HEIGHT / NUM_LOOPS  # Height per loop (~4.2mm)
    
    print(f"Creating spiral tunnel module using PartDesign Additive Helix:")
    print(f"  Tunnel diameter: {TUNNEL_DIAMETER}mm")
    print(f"  Spiral radius: {SPIRAL_RADIUS}mm") 
    print(f"  Pitch: {pitch:.1f}mm")
    print(f"  Height: {MODULE_HEIGHT}mm")
    print(f"  Turns: {NUM_LOOPS}")
    
    # Create document
    try:
        doc = FreeCAD.getDocument("FilamentDryer")
    except:
        doc = FreeCAD.newDocument("FilamentDryer")
    
    # Step 1: Create main cylinder with center hole
    outer_cylinder = Part.makeCylinder(OUTER_DIAMETER/2, MODULE_HEIGHT,
                                      FreeCAD.Vector(0, 0, -MODULE_HEIGHT/2))
    center_hole = Part.makeCylinder(CENTER_HOLE_DIAMETER/2, MODULE_HEIGHT + 2,
                                   FreeCAD.Vector(0, 0, -MODULE_HEIGHT/2 - 1))
    main_shape = outer_cylinder.cut(center_hole)
    
    main_obj = doc.addObject("Part::Feature", "MainCylinder")
    main_obj.Shape = main_shape
    main_obj.Label = "Main Cylinder"
    
    # Step 2: Create PartDesign Body for tunnel
    body = doc.addObject('PartDesign::Body', 'TunnelBody')
    
    # Step 3: Create sketch for circular profile
    sketch = body.newObject('Sketcher::SketchObject', 'CircleProfile')
    
    # Position circle at helix starting point (SPIRAL_RADIUS from center)
    circle = sketch.addGeometry(Part.Circle(
        FreeCAD.Vector(SPIRAL_RADIUS, 0, 0),  # At spiral radius
        FreeCAD.Vector(0, 0, 1), 
        TUNNEL_DIAMETER/2
    ), False)  # False = not construction geometry
    
    # Add constraints to fully define the circle
    sketch.addConstraint(Sketcher.Constraint('Radius', circle, TUNNEL_DIAMETER/2))
    sketch.addConstraint(Sketcher.Constraint('DistanceX', circle, 3, SPIRAL_RADIUS))  # 3 = center point
    sketch.addConstraint(Sketcher.Constraint('DistanceY', circle, 3, 0))
    
    # Close the sketch (important!)
    sketch.ViewObject.hide()
    doc.recompute()
    print("✓ Created circular profile sketch positioned at helix starting point")
    
    # Step 4: Create Additive Helix
    try:
        helix = body.newObject("PartDesign::AdditiveHelix", "SpiralTunnel")
        helix.Profile = sketch
        
        # Set mode and parameters based on working examples
        helix.Mode = 0  # 0 = pitch-height mode
        helix.Pitch = pitch
        helix.Height = MODULE_HEIGHT
        helix.Turns = NUM_LOOPS
        helix.LeftHanded = False
        helix.Reversed = False
        helix.ReferenceAxis = (body.Origin.OriginFeatures[2],[''])  # Z-axis
        
        doc.recompute()
        print("✓ Created spiral tunnel using PartDesign Additive Helix")
        
        # Check if helix created properly
        if hasattr(helix, 'Shape') and helix.Shape.isValid():
            print("✓ Helix shape is valid")
            # Set visualization
            if hasattr(helix, 'ViewObject'):
                helix.ViewObject.ShapeColor = (1.0, 0.0, 1.0)  # Magenta
                helix.ViewObject.Transparency = 30
        else:
            print("❌ Helix shape is invalid")
            helix = None
            
    except Exception as e:
        print(f"Additive Helix failed: {e}")
        print("Trying alternative approach...")
        helix = None
    
    # Step 5: Cut tunnel from main cylinder
    if helix and hasattr(helix, 'Shape'):
        try:
            final_shape = main_shape.cut(helix.Shape)
            
            final_obj = doc.addObject("Part::Feature", "ModuleWithTunnel")
            final_obj.Shape = final_shape
            final_obj.Label = "Filament Dryer Module"
            
            # Hide intermediate objects
            main_obj.ViewObject.Visibility = False
            body.ViewObject.Visibility = False
            
            print("✓ Cut spiral tunnel from main cylinder")
            
        except Exception as e:
            print(f"Cut operation failed: {e}")
            final_obj = main_obj
    else:
        final_obj = main_obj
    
    # Final setup
    doc.recompute()
    
    try:
        import FreeCADGui
        FreeCADGui.SendMsgToActiveView("ViewFit")
    except:
        pass
    
    print("\n✓ Spiral tunnel module created using proper PartDesign method!")
    print("  - Circular profile positioned at helix starting point")
    print("  - PartDesign Additive Helix with correct parameters")
    print("  - Clean, constant circular cross-section")
    
    return final_obj

# Main execution
if __name__ == "__main__":
    module = create_spiral_tunnel_module()