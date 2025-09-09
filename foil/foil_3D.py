"""
Foil 3D Pipeline - Converts STEP outline profiles to 3D NACA foil via chord slicing and lofting.
Version 1.4.0 - Adaptive slicing based on profile curvature
Exports both STEP and STL files.
"""

import os
from PySide2 import QtWidgets
import FreeCAD as App, Part
from FreeCAD import Vector
import math

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth
VERSION = "1.4.0"  # Adaptive slicing version

# COMPLEXITY CONTROL - Set to 1 for full quality, higher for faster processing
COMPLEXITY_REDUCTION = 1  # Reduces point count and adjusts spacing

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
    'naca_points': max(20, 80 // COMPLEXITY_REDUCTION),  # Points per section
    'base_slice_spacing': 3.0 * COMPLEXITY_REDUCTION,  # Base spacing
    'min_slice_spacing': 2.0,    # mm minimum spacing even in high curvature
    'max_slice_spacing': 15.0,   # mm maximum spacing in straight sections
    'curvature_samples': 50,     # Number of points to sample for curvature analysis
    'min_chord_length': 10.0,    # mm minimum chord to include
    'stl_tolerance': min(0.2, 0.05 * COMPLEXITY_REDUCTION),  # STL tolerance
    'plane_size': 1000,          # mm sectioning plane size
}

print(f"🔧 Complexity reduction: {COMPLEXITY_REDUCTION}x")
print(f"   Points per section: {CONFIG['naca_points']} (was 80)")
print(f"   Base slice spacing: {CONFIG['base_slice_spacing']}mm")
print(f"   Adaptive spacing: {CONFIG['min_slice_spacing']}-{CONFIG['max_slice_spacing']}mm")
print(f"   STL tolerance: {CONFIG['stl_tolerance']}mm")


def analyze_profile_curvature(wire, num_samples=50):
    """
    Analyze the curvature along the wire to identify regions needing more slices.
    Returns: list of (z_position, curvature_value) tuples
    """
    # Get bounds
    bb = wire.BoundBox
    z_min, z_max = bb.ZMin, bb.ZMax
    z_range = z_max - z_min
    
    curvatures = []
    
    # Sample points along the wire height
    for i in range(num_samples):
        z = z_min + (i / (num_samples - 1)) * z_range
        
        # Create cutting plane
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        section = wire.section(plane)
        
        if len(section.Vertexes) >= 2:
            # Get chord endpoints
            pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
            
            # Calculate local "curvature" as change in chord length
            if i > 0 and len(curvatures) > 0:
                prev_chord = curvatures[-1][2] if len(curvatures[-1]) > 2 else 0
                curr_chord = pts[-1].x - pts[0].x
                
                # Curvature metric: rate of chord change
                curvature = abs(curr_chord - prev_chord) / (z_range / num_samples)
                curvatures.append((z, curvature, curr_chord))
            else:
                # First point, no curvature yet
                curr_chord = pts[-1].x - pts[0].x
                curvatures.append((z, 0.0, curr_chord))
    
    # Normalize curvatures
    if curvatures:
        max_curv = max(c[1] for c in curvatures)
        if max_curv > 0:
            curvatures = [(z, c/max_curv, chord) for z, c, chord in curvatures]
    
    return curvatures


def generate_adaptive_levels(wire, base_spacing, min_spacing, max_spacing):
    """
    Generate slice levels with adaptive spacing based on profile curvature.
    More slices where profile changes rapidly, fewer in uniform regions.
    """
    bb = wire.BoundBox
    z_min, z_max = bb.ZMin, bb.ZMax
    z_range = z_max - z_min
    
    print(f"🔍 Analyzing profile curvature...")
    
    # Analyze curvature
    curvatures = analyze_profile_curvature(wire, CONFIG['curvature_samples'])
    
    if not curvatures:
        # Fallback to uniform spacing
        print("   Using uniform spacing (curvature analysis failed)")
        num_levels = int(z_range / base_spacing) + 1
        return [z_min + i * base_spacing for i in range(num_levels)]
    
    # Generate adaptive levels
    levels = [z_min]  # Start at bottom
    current_z = z_min
    
    while current_z < z_max - min_spacing:
        # Find curvature at current position
        current_curvature = 0.0
        for i in range(len(curvatures) - 1):
            if curvatures[i][0] <= current_z <= curvatures[i+1][0]:
                # Interpolate curvature
                t = (current_z - curvatures[i][0]) / (curvatures[i+1][0] - curvatures[i][0])
                current_curvature = curvatures[i][1] * (1-t) + curvatures[i+1][1] * t
                break
        
        # Calculate spacing based on curvature
        # High curvature (1.0) -> min_spacing
        # Low curvature (0.0) -> max_spacing
        spacing = min_spacing + (1.0 - current_curvature) * (max_spacing - min_spacing)
        
        # Apply complexity reduction influence
        spacing = min(max_spacing, spacing * (1 + (COMPLEXITY_REDUCTION - 1) * 0.3))
        
        # Ensure we don't overshoot
        next_z = min(current_z + spacing, z_max)
        
        # Add level if it's not too close to the end
        if next_z < z_max - min_spacing * 0.5:
            levels.append(next_z)
            current_z = next_z
        else:
            break
    
    # Always include the top
    if levels[-1] != z_max:
        levels.append(z_max)
    
    # Report spacing distribution
    spacings = [levels[i+1] - levels[i] for i in range(len(levels)-1)]
    avg_spacing = sum(spacings) / len(spacings) if spacings else base_spacing
    
    print(f"✨ Adaptive slicing complete:")
    print(f"   Levels: {len(levels)} (vs {int(z_range/base_spacing)+1} uniform)")
    print(f"   Spacing: min={min(spacings):.1f}mm, avg={avg_spacing:.1f}mm, max={max(spacings):.1f}mm")
    
    # Identify regions
    high_detail_zones = []
    low_detail_zones = []
    for i, spacing in enumerate(spacings):
        z_mid = (levels[i] + levels[i+1]) / 2
        if spacing <= base_spacing * 0.7:
            high_detail_zones.append(f"{levels[i]:.0f}-{levels[i+1]:.0f}")
        elif spacing >= base_spacing * 1.5:
            low_detail_zones.append(f"{levels[i]:.0f}-{levels[i+1]:.0f}")
    
    if high_detail_zones:
        print(f"   High detail zones (Z): {', '.join(high_detail_zones[:3])}{'...' if len(high_detail_zones) > 3 else ''}")
    if low_detail_zones:
        print(f"   Low detail zones (Z): {', '.join(low_detail_zones[:3])}{'...' if len(low_detail_zones) > 3 else ''}")
    
    return levels


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
    print(f"   Using adaptive slicing for optimal geometry")
    
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
    
    # Generate adaptive slice levels based on profile curvature
    levels = generate_adaptive_levels(
        shrunk_wire, 
        CONFIG['base_slice_spacing'],
        CONFIG['min_slice_spacing'],
        CONFIG['max_slice_spacing']
    )
    
    print(f"🔪 Slicing at {len(levels)} adaptive levels")
    
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
    
    # Estimate complexity reduction
    uniform_levels = int((levels[-1] - levels[0]) / CONFIG['base_slice_spacing']) + 1
    complexity_reduction = (1 - len(levels) / uniform_levels) * 100
    print(f"📊 Complexity reduced by {complexity_reduction:.0f}% vs uniform slicing")
    print(f"   Total points: ~{len(section_wires) * CONFIG['naca_points']:,} (vs ~{uniform_levels * CONFIG['naca_points']:,} uniform)")
    
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
    print(f"🛥️ {BOAT_NAME} foil complete with adaptive slicing!\n")


# Run the build
if __name__ == "__main__" or __name__ == "__builtin__":
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("FoilBuild")
    build_foil_from_step(doc)