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

# Configuration - Simplified and Essential Parameters Only
CONFIG = {
    # NACA Profile Settings
    'naca_profile': '0012',      # NACA 4-digit code (0012 = 12% thick, symmetric)
    'naca_points': 50,           # Number of points in airfoil cross-section
    
    # Slicing Settings - Keep It Simple
    'slice_spacing': 4.0,        # mm uniform spacing - captures all detail
    'min_chord_length': 10.0,    # mm minimum chord length to include
    
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
VERSION = "1.0.3"
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
    
    # Improved adaptive algorithm with minimum spacing enforcement
    levels = []
    current_z = bb.ZMin
    
    # Always include start
    levels.append(current_z)
    
    # Generate levels with adaptive spacing but enforce minimum distance
    min_spacing = config['fine_spacing']  # Never go below fine spacing
    max_spacing = config['coarse_spacing']
    
    while current_z < bb.ZMax and len(levels) < config['max_sections']:
        # Sample local geometry to estimate spacing needed
        try:
            # Create planes at small intervals to check local variation
            test_spacing = min_spacing * 2  # Test spacing
            if current_z + test_spacing < bb.ZMax:
                plane1 = Part.makePlane(config['plane_size'], config['plane_size'], 
                                       Vector(0, 0, current_z), Vector(0, 0, 1))
                plane2 = Part.makePlane(config['plane_size'], config['plane_size'], 
                                       Vector(0, 0, current_z + test_spacing), Vector(0, 0, 1))
                
                section1 = wire.section(plane1)
                section2 = wire.section(plane2)
                
                # Check if chord length changes significantly
                if (len(section1.Vertexes) >= 2 and len(section2.Vertexes) >= 2):
                    pts1 = sorted([v.Point for v in section1.Vertexes], key=lambda p: p.x)
                    pts2 = sorted([v.Point for v in section2.Vertexes], key=lambda p: p.x)
                    
                    chord1 = pts1[-1].x - pts1[0].x
                    chord2 = pts2[-1].x - pts2[0].x
                    
                    # If chord changes rapidly, use fine spacing
                    chord_change = abs(chord2 - chord1) / chord1 if chord1 > 0 else 0
                    
                    if chord_change > config['curvature_threshold']:
                        spacing = min_spacing
                    else:
                        spacing = max_spacing
                else:
                    spacing = config['slice_spacing']  # Default spacing if no intersection
            else:
                spacing = min_spacing  # Near end, use fine spacing
                
        except:
            spacing = config['slice_spacing']  # Fallback to default
        
        # Advance by chosen spacing, but don't exceed max Z
        current_z += spacing
        if current_z < bb.ZMax:
            levels.append(current_z)
    
    # Always include end
    if levels[-1] != bb.ZMax:
        levels.append(bb.ZMax)
    
    # Ensure minimum sections by adding intermediate levels if needed
    while len(levels) < config['min_sections'] and len(levels) > 1:
        new_levels = [levels[0]]
        for i in range(len(levels) - 1):
            new_levels.append(levels[i])
            # Only add intermediate if gap is large enough
            gap = levels[i+1] - levels[i]
            if gap > min_spacing * 2:
                mid_z = (levels[i] + levels[i+1]) / 2
                new_levels.append(mid_z)
        new_levels.append(levels[-1])
        levels = new_levels
    
    # Ensure no levels are too close together (minimum spacing enforcement)
    filtered_levels = [levels[0]]
    for level in levels[1:]:
        if level - filtered_levels[-1] >= min_spacing * 0.9:  # Small tolerance
            filtered_levels.append(level)
    
    return sorted(filtered_levels)

def run():
    """
    Single full-pipeline macro: outline → chords → NACA sections → loft
    """
    print(f"FoilBuildFull v{VERSION}")
    print(f"Config: NACA {CONFIG['naca_profile']}, {CONFIG['slice_spacing']}mm uniform spacing, {CONFIG['naca_points']} pts/section")
    
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

    # 4) Generate uniform slice levels
    bb = shrunk_wire.BoundBox
    total_height = bb.ZMax - bb.ZMin
    if total_height < CONFIG['slice_spacing']:
        print(f"❌ Wire height ({total_height:.1f}mm) too small for slicing.")
        return
    
    # Simple uniform spacing
    num_levels = int(total_height / CONFIG['slice_spacing']) + 1
    levels = [bb.ZMin + i * CONFIG['slice_spacing'] for i in range(num_levels)]
    # Always include the end
    if levels[-1] != bb.ZMax:
        levels.append(bb.ZMax)
    
    print(f"🔪 Uniform slicing: {len(levels)} levels from Z={bb.ZMin:.1f} to Z={bb.ZMax:.1f}")
    
    # 5) Slice chords via Part.section with validation
    chords = []
    for z in levels:
        plane = Part.makePlane(PLANE_SIZE, PLANE_SIZE, Vector(0, 0, z), Vector(0, 0, 1))
        section = shrunk_wire.section(plane)
        verts = section.Vertexes
        if len(verts) >= 2:
            pts = sorted([v.Point for v in verts], key=lambda p: p.x)
            chord_length = pts[-1].x - pts[0].x
            if chord_length > CONFIG['min_chord_length']:
                chords.append(((pts[0].x, z), (pts[-1].x, z)))
    
    if not chords:
        print("❌ No valid chords found - check wire geometry.")
        return
    print(f"✅ Found {len(chords)} valid chords for sections (chords > {CONFIG['min_chord_length']}mm).")

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
    
    print(f"Built {len(sections)} NACA sections.")

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