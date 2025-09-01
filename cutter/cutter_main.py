# Rudder Profile Cutter - Creates final foil by cutting stock cavity
# Version 2.1.0 - Cleaned up with single shell creation method

import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.1.0"

# Shell parameters
SHELL_THICKNESS = 3.0      # mm target wall thickness
MIN_SHELL_THICKNESS = 2.5  # mm minimum acceptable thickness

# Paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
OUTPUT_BASE = f"{BOAT_FOLDER}/output"

# Files
FOIL_STEP = f"{OUTPUT_BASE}/foil/{BOAT_NAME}_Foil.step"
PROFILE_STEP = f"{OUTPUT_BASE}/outline/{BOAT_NAME}_Profile.step"
OUTPUT_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Cut_Foil.step"
OUTPUT_STL = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Cut_Foil.stl"
SHELL_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Shell_Foil.step"
SHELL_STL = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Shell_Foil.stl"

# Parameters
CUTTER_HEIGHT = 100.0  # mm
CUTTER_MARGIN = 50.0   # mm

def verify_shell_thickness(shell_shape, target_thickness, tolerance=0.5):
    """
    Verify shell thickness using volume/area ratio
    Returns: (actual_thickness, passes_check)
    """
    volume = shell_shape.Volume / 1000  # cm³
    area = shell_shape.Area / 100  # cm²
    
    # Estimated thickness from volume/area ratio
    estimated_thickness = (volume / area) * 10  # mm
    
    passes = abs(estimated_thickness - target_thickness) <= tolerance
    
    return estimated_thickness, passes

def create_shell(solid_shape, target_thickness):
    """
    Create shell using scaling method with iterative refinement
    Returns: (shell_shape, actual_thickness)
    """
    # Validate input
    if solid_shape.isNull() or not solid_shape.isValid():
        raise Exception("Invalid input shape for shell creation")
    
    # Check if geometry can support the thickness
    bbox = solid_shape.BoundBox
    min_dimension = min(bbox.XLength, bbox.YLength, bbox.ZLength)
    
    actual_thickness = target_thickness
    if min_dimension <= 2 * target_thickness:
        print(f"⚠️  Geometry constraint: min dimension is {min_dimension:.2f}mm")
        actual_thickness = max(MIN_SHELL_THICKNESS, min_dimension * 0.4)
        if actual_thickness < target_thickness:
            print(f"   Adjusted thickness from {target_thickness}mm to {actual_thickness:.2f}mm")
    
    # Iterative approach to get correct thickness
    max_iterations = 3
    thickness_multiplier = 1.0
    
    for iteration in range(max_iterations):
        # Calculate scale factor with multiplier
        center = solid_shape.CenterOfMass
        avg_dimension = (bbox.XLength + bbox.YLength + bbox.ZLength) / 3
        
        # Apply multiplier to compensate for non-uniform scaling effects
        adjusted_thickness = actual_thickness * thickness_multiplier
        scale_factor = max(0.1, 1 - (2 * adjusted_thickness / avg_dimension))
        
        print(f"   Iteration {iteration + 1}: scale factor = {scale_factor:.4f}, multiplier = {thickness_multiplier:.2f}")
        
        # Create transformation matrix for uniform scaling
        matrix = App.Matrix()
        matrix.scale(scale_factor, scale_factor, scale_factor)
        
        # Scale the shape: translate to origin, scale, translate back
        scaled_shape = solid_shape.copy()
        scaled_shape.translate(-center)
        scaled_shape = scaled_shape.transformGeometry(matrix)
        scaled_shape.translate(center)
        
        if scaled_shape.isNull() or not scaled_shape.isValid():
            raise Exception("Scaled shape is invalid")
        
        # Create shell by boolean cut
        shell_shape = solid_shape.cut(scaled_shape)
        
        if shell_shape.isNull() or not shell_shape.isValid():
            raise Exception("Shell creation failed - boolean cut resulted in invalid shape")
        
        # Verify thickness
        measured_thickness, passes = verify_shell_thickness(shell_shape, actual_thickness)
        print(f"   Measured thickness: {measured_thickness:.2f}mm (target: {actual_thickness:.2f}mm)")
        
        if passes:
            print(f"   ✅ Thickness within tolerance")
            return shell_shape, measured_thickness
        
        # Adjust multiplier for next iteration
        if measured_thickness < actual_thickness:
            # Too thin, need bigger gap
            thickness_multiplier *= (actual_thickness / measured_thickness)
        else:
            # Too thick, need smaller gap
            thickness_multiplier *= (actual_thickness / measured_thickness)
        
        # Limit multiplier to reasonable range
        thickness_multiplier = max(0.1, min(20.0, thickness_multiplier))
    
    # After max iterations, return best attempt
    print(f"   ⚠️  Could not achieve exact thickness after {max_iterations} iterations")
    return shell_shape, measured_thickness

def run():
    print(f"\n🔪 Rudder Cutter v{VERSION} for {BOAT_NAME}")
    print(f"   Target shell thickness: {SHELL_THICKNESS}mm")
    
    # Ensure output folder
    os.makedirs(os.path.dirname(OUTPUT_STEP), exist_ok=True)
    
    # New document
    doc = App.newDocument(f"Cutter_{BOAT_NAME}")
    Gui.activateWorkbench("PartWorkbench")
    
    # Import foil
    if not os.path.exists(FOIL_STEP):
        print("❌ Foil not found")
        return
    
    foil_shape = Part.read(FOIL_STEP)
    # Ensure solid
    if foil_shape.ShapeType != 'Solid':
        if foil_shape.Shells:
            foil_shape = Part.makeSolid(foil_shape.Shells[0])
    
    foil = doc.addObject("Part::Feature", "Foil")
    foil.Shape = foil_shape
    print(f"✅ Imported foil")
    
    # Import profile and extract shrunk wire
    if not os.path.exists(PROFILE_STEP):
        print("❌ Profile not found")
        return
    
    profile_compound = Part.read(PROFILE_STEP)
    subs = profile_compound.SubShapes if hasattr(profile_compound, 'SubShapes') else [profile_compound]
    
    if len(subs) < 2:
        print("❌ Profile missing shrunk wire")
        return
    
    # Second subshape is shrunk wire
    shrunk_wire = Part.Wire(subs[1].Edges)
    print(f"✅ Extracted shrunk wire: {len(shrunk_wire.Edges)} edges")
    
    # Create cutter (box with hole)
    bbox = shrunk_wire.BoundBox
    
    # Outer box
    outer = Part.makeBox(
        bbox.XLength + 2*CUTTER_MARGIN,
        2*CUTTER_HEIGHT,
        bbox.ZLength + 2*CUTTER_MARGIN,
        Vector(bbox.XMin - CUTTER_MARGIN, -CUTTER_HEIGHT, bbox.ZMin - CUTTER_MARGIN)
    )
    
    # Inner cavity (extrude shrunk wire)
    inner_face = Part.Face(shrunk_wire)
    inner = inner_face.extrude(Vector(0, 2*CUTTER_HEIGHT, 0))
    inner.translate(Vector(0, -CUTTER_HEIGHT, 0))
    
    # Create cutter
    cutter_shape = outer.cut(inner)
    cutter = doc.addObject("Part::Feature", "Cutter")
    cutter.Shape = cutter_shape
    cutter.ViewObject.Transparency = 50
    print("✅ Created cutter")
    
    # Align cutter to foil center
    offset = foil.Shape.BoundBox.Center - cutter.Shape.BoundBox.Center
    cutter_shape = cutter.Shape.copy()
    cutter_shape.translate(offset)
    
    # Cut foil
    cut_shape = foil.Shape.cut(cutter_shape)
    
    # Validate the cut shape
    if cut_shape.isNull():
        print("❌ Cut operation resulted in null shape")
        return
    
    if not cut_shape.isValid():
        print("⚠️  Cut shape is invalid, attempting to fix...")
        cut_shape = cut_shape.fix()
        if cut_shape.isNull() or not cut_shape.isValid():
            print("❌ Could not fix invalid cut shape")
            return
        print("✅ Fixed cut shape")
    
    cut_foil = doc.addObject("Part::Feature", "Cut_Foil")
    cut_foil.Shape = cut_shape
    cut_foil.ViewObject.ShapeColor = (0.0, 0.8, 0.0)
    print("✅ Cut complete")
    
    # Export solid version
    Part.export([cut_foil], OUTPUT_STEP)
    print(f"✅ Exported STEP: {OUTPUT_STEP}")
    
    try:
        cut_foil.Shape.exportStl(OUTPUT_STL)
        print(f"✅ Exported STL: {OUTPUT_STL}")
    except:
        print("⚠️  STL export failed")
    
    # Create shell version
    print("\n🔧 Creating shell version")
    
    # Convert Compound to Solid if necessary
    if cut_shape.ShapeType == 'Compound':
        solids = cut_shape.Solids
        if len(solids) == 0:
            print("❌ No solids found in compound")
            return
        elif len(solids) == 1:
            cut_shape = solids[0]
            print(f"   Extracted single solid from compound")
        else:
            print(f"   Fusing {len(solids)} solids...")
            cut_shape = solids[0]
            for i in range(1, len(solids)):
                cut_shape = cut_shape.fuse(solids[i])
            print(f"✅ Fused solids into one")
    
    # Print shape info
    print(f"   Shape type: {cut_shape.ShapeType}")
    print(f"   Volume: {cut_shape.Volume/1000:.1f} cm³")
    print(f"   Surface area: {cut_shape.Area/100:.1f} cm²")
    print(f"   Faces: {len(cut_shape.Faces)}, Edges: {len(cut_shape.Edges)}")
    
    # Create shell
    try:
        shell_shape, actual_thickness = create_shell(cut_shape, SHELL_THICKNESS)
        
        shell_foil = doc.addObject("Part::Feature", "Shell_Foil")
        shell_foil.Shape = shell_shape
        shell_foil.ViewObject.ShapeColor = (0.0, 0.5, 0.8)
        shell_foil.ViewObject.Transparency = 30
        
        print(f"✅ Shell created: {actual_thickness:.2f}mm thickness")
        
        # Verify shell thickness (volume-based check)
        solid_volume = cut_shape.Volume
        shell_volume = shell_shape.Volume
        volume_ratio = shell_volume / solid_volume
        print(f"   Volume ratio (shell/solid): {volume_ratio:.1%}")
        
        # Export shell
        Part.export([shell_foil], SHELL_STEP)
        print(f"✅ Exported Shell STEP: {SHELL_STEP}")
        
        try:
            shell_foil.Shape.exportStl(SHELL_STL)
            print(f"✅ Exported Shell STL: {SHELL_STL}")
        except:
            print("⚠️  Shell STL export failed")
            
    except Exception as e:
        print(f"❌ Shell creation failed: {e}")
        print("   Consider adjusting SHELL_THICKNESS parameter")
        return
    
    # Finalize
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    print(f"\n🚤 {BOAT_NAME} cutter complete!")
    print(f"   Solid: {OUTPUT_STEP}")
    print(f"   Shell: {SHELL_STEP} ({actual_thickness:.2f}mm walls)")

if __name__ == "__main__":
    run()