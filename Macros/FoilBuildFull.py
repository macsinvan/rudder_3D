# Macros/FoilBuildFull.py
"""
Foil Build Full Pipeline
Converts STEP outline profiles to 3D NACA foil via chord slicing and lofting.
"""

import sys, os
# Ensure our packages are findable
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)  # so 'outline' package is found
sys.path.insert(0, os.path.join(project, "foil"))  # so 'rudderlib_foil' package is found

from PySide2 import QtWidgets
import FreeCAD as App, FreeCADGui as Gui, Part
from FreeCAD import Vector
from outline.geometry import slice_chords
from rudderlib_foil.naca import naca4_coordinates

# Configuration - Easily adjustable parameters
CONFIG = {
    # NACA Profile Settings
    'naca_profile': '0012',      # NACA 4-digit code (0012 = 12% thick, symmetric)
    'naca_points': 50,           # Number of points in airfoil cross-section
    
    # Slicing Settings  
    'slice_spacing': 10.0,       # mm default spacing between chord slices
    'adaptive_slicing': False,   # Disable adaptive slicing temporarily for debugging
    'fine_spacing': 5.0,         # mm spacing in high-curvature areas
    'coarse_spacing': 20.0,      # mm spacing in straight areas
    'curvature_threshold': 0.01, # Curvature threshold for fine vs coarse spacing
    'min_sections': 5,           # Minimum number of sections to generate
    'max_sections': 50,          # Maximum number of sections to generate
    'min_chord_length': 1.0,     # mm minimum chord length to include
    
    # Geometry Settings
    'plane_size': 1000,          # mm size of sectioning planes
    'min_wire_size': 1.0,        # mm minimum wire diagonal for validation
    
    # Visual Settings
    'section_color': (0.0, 0.0, 1.0),      # Blue for airfoil sections
    'orig_wire_color': (1.0, 0.6, 0.6),    # Light red for original outline
    'shrunk_wire_color': (1.0, 0.0, 0.0),  # Red for shrunk outline  
    'loft_color': (0.6, 0.8, 1.0),         # Light blue for final loft
}

# Constants (derived from config)
VERSION = "1.0.2"
SLICE_SPACING = CONFIG['slice_spacing']
PLANE_SIZE = CONFIG['plane_size'] 
NACA_PROFILE = CONFIG['naca_profile']
NACA_POINTS = CONFIG['naca_points']

def calculate_adaptive_levels(wire, config):
    """
    Calculate adaptive slice levels based on wire curvature.
    Returns list of Z levels with fine spacing in curved areas, coarse in straight areas.
    """
    bb = wire.BoundBox
    total_height = bb.ZMax - bb.ZMin
    
    if not config['adaptive_slicing']:
        # Fall back to uniform spacing
        num_levels = int(total_height / config['slice_spacing']) + 1
        return [bb.ZMin + i * config['slice_spacing'] for i in range(num_levels)]
    
    # Sample wire at regular intervals to analyze curvature
    sample_spacing = total_height / 100  # 100 sample points
    sample_levels = [bb.ZMin + i * sample_spacing for i in range(101)]
    
    curvatures = []
    for z in sample_levels:
        # Create a small plane to intersect wire
        plane = Part.makePlane(config['plane_size'], config['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        try:
            section = wire.section(plane)
            if len(section.Vertexes) >= 2:
                # Simple curvature estimate: change in chord length
                pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
                chord_length = pts[-1].x - pts[0].x
                curvatures.append(chord_length)
            else:
                curvatures.append(0)
        except:
            curvatures.append(0)
    
    # Calculate local curvature (rate of change of chord length)
    local_curvatures = []
    for i in range(len(curvatures)):
        if i == 0 or i == len(curvatures) - 1:
            local_curvatures.append(0)
        else:
            # Second derivative approximation
            curvature = abs(curvatures[i+1] - 2*curvatures[i] + curvatures[i-1])
            local_curvatures.append(curvature)
    
    # Generate adaptive levels
    levels = [bb.ZMin]  # Always include start
    current_z = bb.ZMin
    
    while current_z < bb.ZMax and len(levels) < config['max_sections']:
        # Find curvature at current position
        sample_idx = min(int((current_z - bb.ZMin) / sample_spacing), len(local_curvatures) - 1)
        curvature = local_curvatures[sample_idx] if sample_idx < len(local_curvatures) else 0
        
        # Choose spacing based on curvature
        if curvature > config['curvature_threshold']:
            spacing = config['fine_spacing']
        else:
            spacing = config['coarse_spacing']
        
        current_z += spacing
        if current_z < bb.ZMax:
            levels.append(current_z)
    
    # Always include end
    if levels[-1] != bb.ZMax:
        levels.append(bb.ZMax)
    
    # Ensure minimum sections
    while len(levels) < config['min_sections'] and len(levels) > 1:
        # Insert levels between existing ones
        new_levels = [levels[0]]
        for i in range(len(levels) - 1):
            new_levels.append(levels[i])
            mid_z = (levels[i] + levels[i+1]) / 2
            new_levels.append(mid_z)
        new_levels.append(levels[-1])
        levels = new_levels
    
    return sorted(levels)

def run():
    """
    Single full-pipeline macro: outline → chords → NACA sections → loft
    """
    print(f"FoilBuildFull v{VERSION}")
    slicing_mode = "adaptive" if CONFIG['adaptive_slicing'] else "uniform"
    print(f"Config: NACA {CONFIG['naca_profile']}, {slicing_mode} slicing, {CONFIG['naca_points']} pts/section")
    
    # 1) STEP file selection
    dlg = QtWidgets.QFileDialog()
    dlg.setWindowTitle("Select RudderProfiles STEP")
    dlg.setNameFilter("STEP (*.step *.stp)")
    dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    if not dlg.exec_():
        print("No STEP selected. Aborting.")
        return
    step_path = dlg.selectedFiles()[0]
    print(f"Loading STEP: {step_path}")

    # 2) New document
    doc_name = "FoilBuildFull"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    Gui.activateWorkbench("PartWorkbench")

    # 3) Read outline & shrunk profile with validation
    try:
        compound = Part.read(step_path)
        subs = getattr(compound, 'SubShapes', [compound])
        if len(subs) < 2:
            print("❌ STEP must include outline and shrunk profile.")
            return
        
        # Validate we can create wires
        if not subs[0].Edges or not subs[1].Edges:
            print("❌ STEP shapes must contain edges to form wires.")
            return
            
        orig_wire = Part.Wire(subs[0].Edges)
        shrunk_wire = Part.Wire(subs[1].Edges)
        
        # Validate wires are reasonable
        if orig_wire.BoundBox.DiagonalLength < CONFIG['min_wire_size']:
            print("❌ Original wire too small - check STEP file units.")
            return
        if shrunk_wire.BoundBox.DiagonalLength < CONFIG['min_wire_size']:
            print("❌ Shrunk wire too small - check STEP file units.")
            return
            
        print(f"✅ Loaded wires: Orig={len(orig_wire.Edges)} edges, Shrunk={len(shrunk_wire.Edges)} edges")
        
    except Exception as e:
        print(f"❌ Failed to read STEP file: {e}")
        return

    # Draw original & shrunk wires
    for name, wire, color in [("Orig", orig_wire, CONFIG['orig_wire_color']),
                              ("Shrunk", shrunk_wire, CONFIG['shrunk_wire_color'])]:
        feat = doc.addObject("Part::Feature", f"{name}_Wire")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = color
        feat.ViewObject.LineWidth = 2

    # 4) Calculate adaptive slice levels
    bb = shrunk_wire.BoundBox
    total_height = bb.ZMax - bb.ZMin
    if total_height < CONFIG['fine_spacing']:
        print(f"❌ Wire height ({total_height:.1f}mm) too small for slicing.")
        return
    
    levels = calculate_adaptive_levels(shrunk_wire, CONFIG)
    print(f"🔪 Adaptive slicing: {len(levels)} levels from Z={bb.ZMin:.1f} to Z={bb.ZMax:.1f}")
    
    # 5) Slice chords via Part.section with validation
    chords = []
    for z in levels:
        plane = Part.makePlane(PLANE_SIZE, PLANE_SIZE, Vector(0, 0, z), Vector(0, 0, 1))
        section = shrunk_wire.section(plane)
        verts = section.Vertexes
        if len(verts) >= 2:
            pts = sorted([v.Point for v in verts], key=lambda p: p.x)
            chord_length = pts[-1].x - pts[0].x
            if chord_length > CONFIG['min_chord_length']:  # Configurable minimum chord length
                chords.append(((pts[0].x, z), (pts[-1].x, z)))
    
    if not chords:
        print("❌ No valid chords found - check wire geometry.")
        return
    print(f"✅ Found {len(chords)} valid chords for sections.")

    # 6) Generate NACA sections
    sections = []
    for idx, ((x1, z1), (x2, z2)) in enumerate(chords):
        p_le = Vector(x1, 0.0, z1)  # leading edge (minimum x)
        p_te = Vector(x2, 0.0, z2)  # trailing edge (maximum x)
        vec = p_te.sub(p_le)
        length = vec.Length
        ux = vec.normalize()
        uy = ux.cross(Vector(0.0, 0.0, 1.0)).normalize()

        coords = naca4_coordinates(length, float(CONFIG['naca_profile'][2:]), num_pts=CONFIG['naca_points'])
        pts3 = [p_le + ux * x + uy * z for x, z in coords]
        wire = Part.makePolygon(pts3)
        feat = doc.addObject("Part::Feature", f"Section_{idx}")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = CONFIG['section_color']
        feat.ViewObject.LineWidth = 1
        sections.append(feat)
    print(f"Built {len(sections)} sections.")

    # 7) Loft sections with validation
    shapes = [o.Shape for o in sections]
    
    # Validate shapes before lofting
    print(f"🔍 Validating {len(shapes)} sections for lofting...")
    valid_shapes = []
    for i, shape in enumerate(shapes):
        if shape.isValid():
            valid_shapes.append(shape)
        else:
            print(f"❌ Invalid section {i}, skipping")
    
    if len(valid_shapes) < 2:
        print(f"❌ Need at least 2 valid sections for lofting, got {len(valid_shapes)}")
        return
    
    print(f"✅ {len(valid_shapes)} valid sections ready for lofting")
    
    try:
        loft = Part.makeLoft(valid_shapes, solid=False, ruled=False)
        lf = doc.addObject("Part::Feature", "Foil_Loft")
        lf.Shape = loft
        lf.ViewObject.ShapeColor = CONFIG['loft_color']
        lf.ViewObject.DisplayMode = "Shaded"
        print("✅ Loft created.")
    except Exception as e:
        print(f"❌ Loft failed: {e}")
        print("🔄 Trying ruled loft as fallback...")
        try:
            loft = Part.makeLoft(valid_shapes, solid=False, ruled=True)
            lf = doc.addObject("Part::Feature", "Foil_Loft_Ruled")
            lf.Shape = loft
            lf.ViewObject.ShapeColor = CONFIG['loft_color']
            lf.ViewObject.DisplayMode = "Shaded"
            print("✅ Ruled loft created as fallback.")
        except Exception as e2:
            print(f"❌ Ruled loft also failed: {e2}")
            return

    # 8) Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == '__main__':
    run()