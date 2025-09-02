# Rudder Profile Cutter - Creates final foil by cutting stock cavity + mold creation
# Version 2.2.0 - Added mold creation functionality

import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.2.0"

# Shell parameters
SHELL_THICKNESS = 3.0      # mm target wall thickness
MIN_SHELL_THICKNESS = 2.5  # mm minimum acceptable thickness

# Mold parameters
MOLD_CLEARANCE = 5.0       # mm clearance around foil in all directions
MOLD_MIN_THICKNESS = 10.0  # mm minimum mold wall thickness

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
MOLD_STEP = f"{OUTPUT_BASE}/mold/{BOAT_NAME}_Mold.step"
MOLD_STL = f"{OUTPUT_BASE}/mold/{BOAT_NAME}_Mold.stl"

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

def create_mold(cut_foil_shape):
    """
    Create a mold (negative) of the cut foil
    Returns: mold_shape
    """
    print("\n🏗️  Creating mold")
    
    # Validate input
    if cut_foil_shape.isNull() or not cut_foil_shape.isValid():
        raise Exception("Invalid cut foil shape for mold creation")
    
    # Get bounding box of cut foil
    bbox = cut_foil_shape.BoundBox
    print(f"   Foil dimensions: {bbox.XLength:.1f} x {bbox.YLength:.1f} x {bbox.ZLength:.1f} mm")
    
    # Calculate mold box dimensions (foil + clearance + wall thickness)
    mold_x = bbox.XLength + 2 * (MOLD_CLEARANCE + MOLD_MIN_THICKNESS)
    mold_y = bbox.YLength + 2 * (MOLD_CLEARANCE + MOLD_MIN_THICKNESS)
    mold_z = bbox.ZLength + 2 * (MOLD_CLEARANCE + MOLD_MIN_THICKNESS)
    
    print(f"   Mold box dimensions: {mold_x:.1f} x {mold_y:.1f} x {mold_z:.1f} mm")
    print(f"   Clearance: {MOLD_CLEARANCE}mm, Wall thickness: {MOLD_MIN_THICKNESS}mm")
    
    # Create mold box centered on foil
    mold_center = bbox.Center
    mold_box = Part.makeBox(
        mold_x, mold_y, mold_z,
        Vector(
            mold_center.x - mold_x/2,
            mold_center.y - mold_y/2,
            mold_center.z - mold_z/2
        )
    )
    
    # Create clearance-expanded foil for cavity
    # Scale up the foil slightly to add clearance
    clearance_center = cut_foil_shape.CenterOfMass
    avg_dimension = (bbox.XLength + bbox.YLength + bbox.ZLength) / 3
    clearance_scale = 1 + (MOLD_CLEARANCE / avg_dimension)
    
    print(f"   Clearance scale factor: {clearance_scale:.4f}")
    
    # Create transformation matrix for clearance scaling
    matrix = App.Matrix()
    matrix.scale(clearance_scale, clearance_scale, clearance_scale)
    
    # Scale the foil: translate to origin, scale, translate back
    expanded_foil = cut_foil_shape.copy()
    expanded_foil.translate(-clearance_center)
    expanded_foil = expanded_foil.transformGeometry(matrix)
    expanded_foil.translate(clearance_center)
    
    if expanded_foil.isNull() or not expanded_foil.isValid():
        raise Exception("Expanded foil shape is invalid")
    
    print(f"   ✅ Created expanded foil for cavity")
    
    # Create mold by boolean cut (box minus expanded foil)
    mold_shape = mold_box.cut(expanded_foil)
    
    if mold_shape.isNull() or not mold_shape.isValid():
        raise Exception("Mold creation failed - boolean cut resulted in invalid shape")
    
    # Verify mold properties
    mold_volume = mold_shape.Volume / 1000  # cm³
    cavity_volume = (mold_box.Volume - mold_shape.Volume) / 1000  # cm³
    print(f"   Mold volume: {mold_volume:.1f} cm³")
    print(f"   Cavity volume: {cavity_volume:.1f} cm³")
    
    return mold_shape

def run():
    print(f"\n🔪 Rudder Cutter v{VERSION} for {BOAT_NAME}")
    print(f"   Target shell thickness: {SHELL_THICKNESS}mm")
    print(f"   Mold clearance: {MOLD_CLEARANCE}mm")
    
    # Ensure output folders
    os.makedirs(os.path.dirname(OUTPUT_STEP), exist_ok=True)
    os.makedirs(os.path.dirname(MOLD_STEP), exist_ok=True)
    
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
    
    # Create mold
    print("\n🏗️  Creating mold")
    
    try:
        mold_shape = create_mold(cut_shape)
        
        mold = doc.addObject("Part::Feature", "Mold")
        mold.Shape = mold_shape
        mold.ViewObject.ShapeColor = (0.8, 0.4, 0.0)  # Orange color for mold
        mold.ViewObject.Transparency = 70  # Highly transparent for visual confirmation
        
        print(f"✅ Mold created")
        
        # Export mold
        Part.export([mold], MOLD_STEP)
        print(f"✅ Exported Mold STEP: {MOLD_STEP}")
        
        try:
            mold.Shape.exportStl(MOLD_STL)
            print(f"✅ Exported Mold STL: {MOLD_STL}")
        except:
            print("⚠️  Mold STL export failed")
        
        # Verify mold can accommodate original foil
        mold_bbox = mold_shape.BoundBox
        foil_bbox = cut_shape.BoundBox
        
        clearance_x = (mold_bbox.XLength - foil_bbox.XLength) / 2 - MOLD_MIN_THICKNESS
        clearance_y = (mold_bbox.YLength - foil_bbox.YLength) / 2 - MOLD_MIN_THICKNESS  
        clearance_z = (mold_bbox.ZLength - foil_bbox.ZLength) / 2 - MOLD_MIN_THICKNESS
        
        print(f"   Actual clearances: X={clearance_x:.1f}mm, Y={clearance_y:.1f}mm, Z={clearance_z:.1f}mm")
        
    except Exception as e:
        print(f"❌ Mold creation failed: {e}")
        print("   Consider adjusting MOLD_CLEARANCE or MOLD_MIN_THICKNESS parameters")
        return
    
    # Finalize
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewIsometric()
    
    print(f"\n🚤 {BOAT_NAME} cutter complete!")
    print(f"   Solid: {OUTPUT_STEP}")
    print(f"   Shell: {SHELL_STEP} ({actual_thickness:.2f}mm walls)")
    print(f"   Mold: {MOLD_STEP} ({MOLD_CLEARANCE}mm clearance)")

def create_mold(cut_foil_shape):
    """
    Create a mold (negative) of the cut foil
    Returns: mold_shape
    """
    # Validate input
    if cut_foil_shape.isNull() or not cut_foil_shape.isValid():
        raise Exception("Invalid cut foil shape for mold creation")
    
    # Get bounding box of cut foil
    bbox = cut_foil_shape.BoundBox
    print(f"   Foil bbox: {bbox.XLength:.1f} x {bbox.YLength:.1f} x {bbox.ZLength:.1f} mm")
    
    # Calculate mold box dimensions
    # Total size = foil + 2*(clearance + wall_thickness)
    total_clearance = MOLD_CLEARANCE + MOLD_MIN_THICKNESS
    
    mold_x = bbox.XLength + 2 * total_clearance
    mold_y = bbox.YLength + 2 * total_clearance
    mold_z = bbox.ZLength + 2 * total_clearance
    
    print(f"   Mold outer dimensions: {mold_x:.1f} x {mold_y:.1f} x {mold_z:.1f} mm")
    
    # Create mold box centered on foil
    foil_center = bbox.Center
    mold_box = Part.makeBox(
        mold_x, mold_y, mold_z,
        Vector(
            foil_center.x - mold_x/2,
            foil_center.y - mold_y/2,
            foil_center.z - mold_z/2
        )
    )
    
    # Create expanded foil for cavity (add clearance)
    center = cut_foil_shape.CenterOfMass
    avg_dimension = (bbox.XLength + bbox.YLength + bbox.ZLength) / 3
    scale_factor = 1 + (MOLD_CLEARANCE / avg_dimension)
    
    print(f"   Foil expansion scale: {scale_factor:.4f}")
    
    # Create transformation matrix
    matrix = App.Matrix()
    matrix.scale(scale_factor, scale_factor, scale_factor)
    
    # Scale the foil: translate to origin, scale, translate back
    expanded_foil = cut_foil_shape.copy()
    expanded_foil.translate(-center)
    expanded_foil = expanded_foil.transformGeometry(matrix)
    expanded_foil.translate(center)
    
    if expanded_foil.isNull() or not expanded_foil.isValid():
        raise Exception("Expanded foil is invalid")
    
    # Create mold by boolean subtraction
    mold_shape = mold_box.cut(expanded_foil)
    
    if mold_shape.isNull() or not mold_shape.isValid():
        raise Exception("Mold boolean operation failed")
    
    # Calculate actual clearances
    expanded_bbox = expanded_foil.BoundBox
    mold_bbox = mold_box.BoundBox
    
    actual_clearance_x = (mold_bbox.XLength - expanded_bbox.XLength) / 2 - MOLD_MIN_THICKNESS
    actual_clearance_y = (mold_bbox.YLength - expanded_bbox.YLength) / 2 - MOLD_MIN_THICKNESS
    actual_clearance_z = (mold_bbox.ZLength - expanded_bbox.ZLength) / 2 - MOLD_MIN_THICKNESS
    
    print(f"   Actual clearances: X={actual_clearance_x:.1f}mm, Y={actual_clearance_y:.1f}mm, Z={actual_clearance_z:.1f}mm")
    
    return mold_shape

if __name__ == "__main__":
    run()