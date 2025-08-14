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
    # NACA Profile Settings - Flexible Thickness Specification
    'naca_camber': '00',         # NACA camber digits (00 = symmetric, 23 = cambered)
    'thickness_percent': 12.0,   # % thickness if no apex measurement (fallback)
    'apex_at_top': None,         # mm actual measured thickness at top (overrides %)
    'thickness_tolerance': 2.0,  # mm tolerance for contradiction warning
    'naca_points': 50,           # Number of points in airfoil cross-section
    
    # Slicing Settings - Keep It Simple
    'slice_spacing': 4.0,        # mm uniform spacing - fast execution with good quality
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
VERSION = "1.1.0"
SLICE_SPACING = CONFIG['slice_spacing']
PLANE_SIZE = CONFIG['plane_size'] 
NACA_POINTS = CONFIG['naca_points']

def calculate_naca_thickness(chords, config):
    """
    Calculate NACA thickness percentage based on config and chord data.
    Handles both percentage specification and measured apex thickness.
    
    Args:
        chords: List of ((x1, z1), (x2, z2)) chord endpoints
        config: Configuration dictionary
        
    Returns:
        (thickness_percent, naca_profile_code)
    """
    apex_measured = config.get('apex_at_top')
    thickness_percent = config.get('thickness_percent', 12.0)
    tolerance = config.get('thickness_tolerance', 2.0)
    
    if apex_measured is not None:
        # Find the top chord (maximum Z) to calculate percentage
        if not chords:
            print(f"❌ No chords available for apex calculation, using fallback {thickness_percent}%")
            calculated_percent = thickness_percent
        else:
            top_chord = max(chords, key=lambda chord: chord[0][1])  # Max Z value
            top_chord_length = top_chord[1][0] - top_chord[0][0]  # x2 - x1
            
            if top_chord_length <= 0:
                print(f"❌ Invalid top chord length, using fallback {thickness_percent}%")
                calculated_percent = thickness_percent
            else:
                calculated_percent = (apex_measured / top_chord_length) * 100.0
                print(f"📏 Apex measurement: {apex_measured:.1f}mm on {top_chord_length:.1f}mm chord = {calculated_percent:.1f}%")
                
                # Check for contradiction if both values provided
                if thickness_percent != 12.0:  # 12.0 is our default, so not user-specified
                    expected_apex = (thickness_percent / 100.0) * top_chord_length
                    difference = abs(apex_measured - expected_apex)
                    
                    if difference > tolerance:
                        print(f"⚠️  WARNING: Apex measurement ({apex_measured:.1f}mm) contradicts thickness % ({thickness_percent:.1f}%)")
                        print(f"    Expected apex for {thickness_percent:.1f}%: {expected_apex:.1f}mm (difference: {difference:.1f}mm > {tolerance:.1f}mm tolerance)")
                        print(f"    Using measured apex value ({calculated_percent:.1f}%)")
    else:
        calculated_percent = thickness_percent
        print(f"📐 Using specified thickness: {thickness_percent:.1f}%")
    
    # Ensure reasonable bounds
    if calculated_percent < 5.0:
        print(f"⚠️  WARNING: Thickness {calculated_percent:.1f}% is very thin, clamping to 5%")
        calculated_percent = 5.0
    elif calculated_percent > 25.0:
        print(f"⚠️  WARNING: Thickness {calculated_percent:.1f}% is very thick, clamping to 25%")
        calculated_percent = 25.0
    
    # Build NACA profile code
    naca_profile = f"{config.get('naca_camber', '00')}{int(calculated_percent):02d}"
    
    return calculated_percent, naca_profile

def run():
    """
    Single full-pipeline macro: outline → chords → NACA sections → loft
    """
    print(f"FoilBuildFull v{VERSION}")
    print(f"Config: {CONFIG['slice_spacing']}mm uniform spacing, {CONFIG['naca_points']} pts/section")
    
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

    # 6) Calculate NACA thickness based on config
    thickness_percent, naca_profile = calculate_naca_thickness(chords, CONFIG)
    print(f"🎯 Using NACA {naca_profile} ({thickness_percent:.1f}% thick)")

    # 7) Generate NACA sections
    sections = []
    for idx, ((x1, z1), (x2, z2)) in enumerate(chords):       
        p_le = Vector(x1, 0.0, z1)  # leading edge (minimum x)
        p_te = Vector(x2, 0.0, z2)  # trailing edge (maximum x)
        vec = p_te.sub(p_le)
        length = vec.Length
        ux = vec.normalize()
        uy = ux.cross(Vector(0.0, 0.0, 1.0)).normalize()

        coords = naca4_coordinates(length, thickness_percent, num_pts=CONFIG['naca_points'])
        pts3 = [p_le + ux * x + uy * z for x, z in coords]
        wire = Part.makePolygon(pts3)
        feat = doc.addObject("Part::Feature", f"Section_{idx}")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = CONFIG['section_color']
        feat.ViewObject.LineWidth = 1
        sections.append(feat)
    
    print(f"Built {len(sections)} NACA sections.")

    # 8) Loft sections with validation
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

    # 9) Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()

if __name__ == '__main__':
    run()