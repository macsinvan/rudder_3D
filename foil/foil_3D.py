"""
Foil 3D Pipeline - Converts STEP outline profiles to 3D NACA foil via chord slicing and lofting.
Exports both STEP and STL files.
"""

import os
from PySide2 import QtWidgets
import FreeCAD as App, Part
from FreeCAD import Vector
import math

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth
VERSION = "1.3.0"  # Simplified version

# COMPLEXITY CONTROL - Set to 1 for full quality, higher for faster processing
COMPLEXITY_REDUCTION = 3  # Reduces point count and increases spacing

# Paths
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/output/outline"
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/foil"

# Files
PROFILES_STEP_FILE = f"{BOAT_NAME}_Outline.step"
FOIL_STEP_FILE = f"{BOAT_NAME}_Foil.step"
FOIL_STL_FILE = f"{BOAT_NAME}_Foil.stl"

# Configuration with complexity reduction
CONFIG = {
    'apex_at_top': 64.0,        # mm measured thickness at top
    'naca_points': max(20, 80 // COMPLEXITY_REDUCTION),  # 26 points (was 80)
    'slice_spacing': 3.0 * COMPLEXITY_REDUCTION,  # 9mm (was 3mm)
    'min_chord_length': 10.0,    # mm minimum chord to include
    'stl_tolerance': min(0.2, 0.05 * COMPLEXITY_REDUCTION),  # 0.15mm (was 0.05)
    'plane_size': 1000,          # mm sectioning plane size
}

print(f"🔧 Complexity reduction: {COMPLEXITY_REDUCTION}x")
print(f"   Points per section: {CONFIG['naca_points']} (was 80)")
print(f"   Slice spacing: {CONFIG['slice_spacing']}mm (was 3.0mm)")
print(f"   STL tolerance: {CONFIG['stl_tolerance']}mm (was 0.05mm)")


def naca_coordinates(chord_length, thickness_percent, num_pts=80):
    """Generate NACA 00XX coordinates with cosine point distribution."""
    # Cosine clustering for better point distribution at edges
    angles = [i * math.pi / (num_pts // 2) for i in range(num_pts // 2 + 1)]
    x_positions = [(1 - math.cos(angle)) / 2 for angle in angles]
    
    coords = []
    thickness_ratio = thickness_percent / 100.0
    
    # Generate airfoil coordinates
    for i, x_norm in enumerate(x_positions):
        x = x_norm * chord_length
        
        # NACA 4-digit thickness distribution
        if x_norm == 0:
            yt = 0
        else:
            yt = 5 * thickness_ratio * chord_length * (
                0.2969 * math.sqrt(x_norm) - 
                0.1260 * x_norm - 
                0.3516 * x_norm**2 + 
                0.2843 * x_norm**3 - 
                0.1015 * x_norm**4
            )
        
        # Add upper surface point (skip first to avoid duplicate at trailing edge)
        if i > 0:
            coords.append((x, yt))
    
    # Add lower surface points (reversed)
    for x, y in reversed(coords[:-1]):  # Skip last to avoid duplicate at leading edge
        coords.append((x, -y))
    
    # Close the polygon
    coords.append(coords[0])
    
    return coords


def get_profiles_step_path():
    """Get profiles STEP path - try organized location first, then dialog."""
    organized_path = f"{INPUT_FOLDER}/{PROFILES_STEP_FILE}"
    
    if os.path.exists(organized_path):
        print(f"📂 Using: {organized_path}")
        return organized_path
    
    print(f"🔍 Opening file dialog...")
    dlg = QtWidgets.QFileDialog()
    dlg.setWindowTitle(f"Select {BOAT_NAME} Profiles STEP")
    dlg.setNameFilter("STEP (*.step *.stp)")
    dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    
    if dlg.exec_():
        return dlg.selectedFiles()[0]
    
    print("❌ No file selected")
    return None


def export_geometry(shape, name_prefix):
    """Export shape as both STEP and STL."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # Export STEP
    step_path = f"{OUTPUT_FOLDER}/{name_prefix}.step"
    Part.export([shape], step_path)
    print(f"✅ Exported STEP: {step_path}")
    
    # Export STL with controlled tessellation
    import Mesh
    stl_path = f"{OUTPUT_FOLDER}/{name_prefix}.stl"
    mesh_obj = Mesh.Mesh(shape.Shape.tessellate(CONFIG['stl_tolerance']))
    
    # Check if watertight
    if mesh_obj.isSolid():
        print(f"✅ Mesh is watertight")
    else:
        print(f"⚠️ Mesh has open edges")
    
    print(f"📊 Mesh: {mesh_obj.CountPoints} vertices, {mesh_obj.CountFacets} facets")
    mesh_obj.write(stl_path)
    print(f"✅ Exported STL: {stl_path}")


def build_foil_from_step(doc):
    """Main pipeline: STEP → chords → NACA sections → loft → export."""
    
    print(f"\n🛥️ Foil Build v{VERSION} for {BOAT_NAME}")
    
    # Get input file
    step_path = get_profiles_step_path()
    if not step_path:
        return
    
    # Read wires from STEP
    compound = Part.read(step_path)
    subs = compound.SubShapes if hasattr(compound, 'SubShapes') else [compound]
    
    if len(subs) < 2:
        print("❌ STEP must contain outline and shrunk profile")
        return
    
    orig_wire = Part.Wire(subs[0].Edges)
    shrunk_wire = Part.Wire(subs[1].Edges)
    print(f"✅ Loaded wires: {len(orig_wire.Edges)} + {len(shrunk_wire.Edges)} edges")
    
    # Display wires
    for name, wire, color in [("Orig", orig_wire, (1.0, 0.6, 0.6)),
                              ("Shrunk", shrunk_wire, (1.0, 0.0, 0.0))]:
        feat = doc.addObject("Part::Feature", f"{BOAT_NAME}_{name}")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = color
        feat.ViewObject.LineWidth = 2
    
    # Generate slice levels
    bb = shrunk_wire.BoundBox
    z_min, z_max = bb.ZMin, bb.ZMax
    num_levels = int((z_max - z_min) / CONFIG['slice_spacing']) + 1
    levels = [z_min + i * CONFIG['slice_spacing'] for i in range(num_levels)]
    if levels[-1] != z_max:
        levels.append(z_max)
    print(f"🔪 Slicing at {len(levels)} levels (every {CONFIG['slice_spacing']}mm)")
    
    # Slice into chords
    chords = []
    for z in levels:
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        section = shrunk_wire.section(plane)
        
        if len(section.Vertexes) >= 2:
            pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
            chord_length = pts[-1].x - pts[0].x
            
            if chord_length > CONFIG['min_chord_length']:
                chords.append(((pts[0].x, z), (pts[-1].x, z)))
    
    if not chords:
        print("❌ No valid chords found")
        return
    
    print(f"✅ Found {len(chords)} chords")
    
    # Calculate NACA thickness from apex measurement
    top_chord = max(chords, key=lambda c: c[0][1])
    top_chord_length = top_chord[1][0] - top_chord[0][0]
    thickness_percent = (CONFIG['apex_at_top'] / top_chord_length) * 100.0
    thickness_percent = max(5.0, min(25.0, thickness_percent))  # Clamp 5-25%
    
    print(f"🎯 NACA 00{int(thickness_percent):02d} ({thickness_percent:.1f}% thick)")
    
    # Generate NACA sections
    section_wires = []
    for (x1, z), (x2, _) in chords:
        # Position and orientation
        p_le = Vector(x2, 0.0, z)  # Leading edge at min x
        p_te = Vector(x1, 0.0, z)  # Trailing edge at max x
        vec = p_te - p_le
        chord_len = vec.Length
        ux = vec.normalize()
        uy = ux.cross(Vector(0, 0, 1)).normalize()
        
        # Generate NACA points
        coords = naca_coordinates(chord_len, thickness_percent, CONFIG['naca_points'])
        pts3d = [p_le + ux * x + uy * y for x, y in coords]
        
        # Create wire
        wire = Part.makePolygon(pts3d)
        section_wires.append(wire)
    
    print(f"✅ Generated {len(section_wires)} NACA sections with {CONFIG['naca_points']} points each")
    estimated_points = len(section_wires) * CONFIG['naca_points']
    print(f"📊 Estimated total points: ~{estimated_points:,} (vs ~{200*80:,} at full quality)")
    
    # Loft sections
    loft = Part.makeLoft(section_wires, solid=True, ruled=False)
    
    # Create display object
    foil = doc.addObject("Part::Feature", f"{BOAT_NAME}_Foil")
    foil.Shape = loft
    foil.ViewObject.ShapeColor = (0.6, 0.8, 1.0)
    foil.ViewObject.DisplayMode = "Shaded"
    
    print("✅ Loft complete")
    
    # Export
    export_geometry(foil, BOAT_NAME + "_Foil")
    
    doc.recompute()
    print(f"🛥️ {BOAT_NAME} foil complete with {COMPLEXITY_REDUCTION}x complexity reduction!\n")


# Run the build
if __name__ == "__main__" or __name__ == "__builtin__":
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("FoilBuild")
    build_foil_from_step(doc)