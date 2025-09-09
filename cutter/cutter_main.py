# Rudder Profile Cutter - Creates final foil by cutting stock cavity + mold creation
# Version 2.3.1 - Fixed makeThickSolid API call syntax

import os
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

# Configuration
BOAT_NAME = "MackenSea"
VERSION = "2.3.1"

# Shell parameters
SHELL_THICKNESS = 3.0      # mm target wall thickness
SHELL_TOLERANCE = 0.1      # mm tolerance for shell creation
MIN_SHELL_THICKNESS = 1.0  # mm minimum allowed thickness

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
MOLD_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Mold.step"
CUTTER_STEP = f"{OUTPUT_BASE}/cut_foil/{BOAT_NAME}_Cutter.step"

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
    last_valid_shell = None
    last_thickness = None
    
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
        
        # Try transformGeometry first, fall back to transformShape for complex geometries
        try:
            scaled_shape = scaled_shape.transformGeometry(matrix)
        except:
            print("   Using transformShape for complex geometry")
            scaled_shape = scaled_shape.transformShape(matrix)
        
        scaled_shape.translate(center)
        
        # Check and fix invalid shapes
        if scaled_shape.isNull() or not scaled_shape.isValid():
            print("   Scaled shape invalid, attempting to fix...")
            try:
                # Try fixing the shape
                fixed = scaled_shape.fix(SHELL_TOLERANCE, SHELL_TOLERANCE, SHELL_TOLERANCE)
                # Handle that fix() might return boolean
                if isinstance(fixed, bool):
                    if not fixed:
                        # Adjust for next iteration - try thinner
                        thickness_multiplier *= 0.8
                        continue
                else:
                    scaled_shape = fixed
                    if scaled_shape.isNull() or not scaled_shape.isValid():
                        # Adjust for next iteration - try thinner
                        thickness_multiplier *= 0.8
                        continue
            except:
                # Adjust for next iteration - try thinner
                thickness_multiplier *= 0.8
                continue
        
        # Create shell by boolean cut
        try:
            shell_shape = solid_shape.cut(scaled_shape)
        except:
            # Try fuzzy boolean with tolerance
            print("   Using fuzzy boolean cut")
            try:
                shell_shape = solid_shape.cut(scaled_shape, SHELL_TOLERANCE)
            except:
                print("   Boolean cut failed")
                thickness_multiplier *= 0.8
                continue
        
        if shell_shape.isNull() or not shell_shape.isValid():
            print("   Shell invalid after boolean")
            thickness_multiplier *= 0.8
            continue
        
        # Verify thickness
        measured_thickness, passes = verify_shell_thickness(shell_shape, actual_thickness)
        print(f"   Measured thickness: {measured_thickness:.2f}mm (target: {actual_thickness:.2f}mm)")
        
        # Store this as a valid result
        last_valid_shell = shell_shape
        last_thickness = measured_thickness
        
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
    
    # If we have any valid shell, return it even if not perfect thickness
    if last_valid_shell is not None:
        print(f"   ⚠️  Using best result: {last_thickness:.2f}mm after {max_iterations} iterations")
        return last_valid_shell, last_thickness
    
    # No valid shell created at all
    raise Exception(f"Could not create valid shell after {max_iterations} iterations")

def create_split_shell(shell_shape, doc, split_at_y=0.0):
    """
    Split the shell along the x-z plane at specified y position
    Returns: (upper_half, lower_half) or (positive_half, negative_half)
    """
    print("\n📐 Creating split shell for visualization")
    
    # Get bounding box to determine plane size
    bbox = shell_shape.BoundBox
    print(f"   Shell bbox: X[{bbox.XMin:.1f}, {bbox.XMax:.1f}], "
          f"Y[{bbox.YMin:.1f}, {bbox.YMax:.1f}], Z[{bbox.ZMin:.1f}, {bbox.ZMax:.1f}]")
    print(f"   Splitting at Y = {split_at_y:.1f}")
    
    # Create cutting plane - make it larger than the shape
    plane_margin = 50.0  # Extra margin for plane
    plane_width = bbox.XLength + 2 * plane_margin
    plane_height = bbox.ZLength + 2 * plane_margin
    plane_thickness = 0.1  # Very thin box to act as plane
    
    # Create cutting box (thin in Y direction)
    cutting_box_positive = Part.makeBox(
        plane_width,
        bbox.YMax - split_at_y + plane_margin,  # From split plane to beyond max Y
        plane_height,
        Vector(
            bbox.XMin - plane_margin,
            split_at_y,
            bbox.ZMin - plane_margin
        )
    )
    
    cutting_box_negative = Part.makeBox(
        plane_width,
        split_at_y - bbox.YMin + plane_margin,  # From min Y to split plane
        plane_height,
        Vector(
            bbox.XMin - plane_margin,
            bbox.YMin - plane_margin,
            bbox.ZMin - plane_margin
        )
    )
    
    # Split the shell
    try:
        # Create positive half (Y > split_at_y)
        positive_half = shell_shape.common(cutting_box_positive)
        
        # Create negative half (Y < split_at_y)
        negative_half = shell_shape.common(cutting_box_negative)
        
        # Validate results
        if positive_half.isNull() or not positive_half.isValid():
            print("⚠️  Positive half invalid, attempting to fix...")
            positive_half = positive_half.fix(0.1, 0.1, 0.1)
            
        if negative_half.isNull() or not negative_half.isValid():
            print("⚠️  Negative half invalid, attempting to fix...")
            negative_half = negative_half.fix(0.1, 0.1, 0.1)
        
        # Calculate volumes for verification
        original_volume = shell_shape.Volume
        positive_volume = positive_half.Volume if not positive_half.isNull() else 0
        negative_volume = negative_half.Volume if not negative_half.isNull() else 0
        total_split_volume = positive_volume + negative_volume
        
        print(f"   Original volume: {original_volume/1000:.2f} cm³")
        print(f"   Positive half: {positive_volume/1000:.2f} cm³")
        print(f"   Negative half: {negative_volume/1000:.2f} cm³")
        print(f"   Volume difference: {abs(original_volume - total_split_volume)/1000:.3f} cm³")
        
        return positive_half, negative_half
        
    except Exception as e:
        print(f"❌ Split failed: {e}")
        return None, None

def add_split_shell_to_document(shell_shape, doc, export_path_base):
    """
    Add split shell parts to the document and export them
    """
    # Create split shells
    positive_half, negative_half = create_split_shell(shell_shape, doc)
    
    if positive_half is None or negative_half is None:
        print("❌ Could not create split shells")
        return None
    
    # Add positive half to document
    if not positive_half.isNull():
        shell_positive = doc.addObject("Part::Feature", "Shell_Positive_Half")
        shell_positive.Shape = positive_half
        shell_positive.ViewObject.ShapeColor = (0.0, 0.7, 0.3)  # Green
        shell_positive.ViewObject.Transparency = 20
        
        # Export positive half
        positive_step_path = export_path_base.replace(".step", "_positive_half.step")
        Part.export([shell_positive], positive_step_path)
        print(f"✅ Exported positive half: {positive_step_path}")
    
    # Add negative half to document  
    if not negative_half.isNull():
        shell_negative = doc.addObject("Part::Feature", "Shell_Negative_Half")
        shell_negative.Shape = negative_half
        shell_negative.ViewObject.ShapeColor = (0.0, 0.3, 0.7)  # Blue
        shell_negative.ViewObject.Transparency = 20
        
        # Export negative half
        negative_step_path = export_path_base.replace(".step", "_negative_half.step")
        Part.export([shell_negative], negative_step_path)
        print(f"✅ Exported negative half: {negative_step_path}")
    
    # Also create a single display half (just show positive half for cleaner view)
    display_half = doc.addObject("Part::Feature", "Shell_Display_Half")
    display_half.Shape = positive_half
    display_half.ViewObject.ShapeColor = (0.0, 0.5, 0.8)
    display_half.ViewObject.Transparency = 0  # Opaque for better visibility
    display_half.ViewObject.LineWidth = 2.0
    
    # Hide the original full shell for clarity
    return display_half

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

def run():
    print(f"\n🔪 Rudder Cutter v{VERSION} for {BOAT_NAME}")
    print(f"   Target shell thickness: {SHELL_THICKNESS}mm")
    print(f"   Mold clearance: {MOLD_CLEARANCE}mm")
    
    # Ensure output folders
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
    Part.export([cutter], CUTTER_STEP)
    print(f"✅ Exported Cutter STEP: {CUTTER_STEP}")
    
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
        
        # Create split shell for better visualization
        split_display = add_split_shell_to_document(shell_shape, doc, SHELL_STEP)
        if split_display:
            # Hide full shell when split is shown
            shell_foil.ViewObject.Visibility = False
            print("✅ Split shell created for visualization")
            print("   Tip: Toggle visibility of Shell_Foil to see full shell")
        
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

if __name__ == "__main__":
    run()