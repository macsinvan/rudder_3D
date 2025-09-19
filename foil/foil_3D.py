"""
Foil 3D Pipeline - Converts STEP outline profiles to 3D NACA foil via chord slicing and lofting.
Version 1.5.0 - Enhanced diagnostics for tip closure analysis
Exports both STEP and STL files.
"""

import os
from PySide2 import QtWidgets
import FreeCAD as App, Part
from FreeCAD import Vector
import math

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth
VERSION = "1.5.0"  # Enhanced diagnostics version

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
    'min_slice_spacing': 1.0,    # mm minimum spacing even in high curvature
    'max_slice_spacing': 5.0,   # mm maximum spacing in straight sections
    'curvature_samples': 100,     # Number of points to sample for curvature analysis
    'min_chord_length': 20.0,    # mm minimum chord to include
    'stl_tolerance': min(0.2, 0.05 * COMPLEXITY_REDUCTION),  # STL tolerance
    'plane_size': 1100,          # mm sectioning plane size
    'gap_tolerance': 0.1,        # mm tolerance for gap detection
    'diagnostic_slice_density': 0.5,  # mm spacing for diagnostic slices near tips
}

print(f"🔧 Complexity reduction: {COMPLEXITY_REDUCTION}x")
print(f"   Points per section: {CONFIG['naca_points']} (was 80)")
print(f"   Base slice spacing: {CONFIG['base_slice_spacing']}mm")
print(f"   Adaptive spacing: {CONFIG['min_slice_spacing']}-{CONFIG['max_slice_spacing']}mm")
print(f"   STL tolerance: {CONFIG['stl_tolerance']}mm")


def comprehensive_profile_diagnostics(wire, doc):
    """
    Perform comprehensive diagnostics on the input profile.
    Returns: dict with diagnostic results and flags
    """
    print("\n" + "="*80)
    print("🔬 COMPREHENSIVE PROFILE DIAGNOSTICS")
    print("="*80)
    
    diagnostics = {
        'valid': True,
        'warnings': [],
        'errors': [],
        'measurements': {}
    }
    
    # 1. Wire Topology Validation
    print("\n1️⃣ WIRE TOPOLOGY VALIDATION")
    print("-" * 40)
    
    is_closed = wire.isClosed()
    is_valid = wire.isValid()
    num_edges = len(wire.Edges)
    num_vertices = len(wire.Vertexes)
    
    print(f"   Is Closed: {is_closed}")
    print(f"   Is Valid: {is_valid}")
    print(f"   Number of Edges: {num_edges}")
    print(f"   Number of Vertices: {num_vertices}")
    
    diagnostics['measurements']['is_closed'] = is_closed
    diagnostics['measurements']['num_edges'] = num_edges
    
    if not is_closed:
        diagnostics['warnings'].append("Wire is not closed - may have open endpoints")
    if not is_valid:
        diagnostics['errors'].append("Wire validation failed")
        diagnostics['valid'] = False
    
    # 2. Gap and Discontinuity Detection
    print("\n2️⃣ GAP AND DISCONTINUITY DETECTION")
    print("-" * 40)
    
    gaps = []
    for i, edge in enumerate(wire.Edges):
        next_edge = wire.Edges[(i + 1) % len(wire.Edges)]
        gap_dist = edge.Vertexes[-1].Point.distanceToPoint(next_edge.Vertexes[0].Point)
        
        if gap_dist > CONFIG['gap_tolerance']:
            gaps.append((i, gap_dist))
            print(f"   ⚠️ Gap detected between edge {i} and {i+1}: {gap_dist:.3f}mm")
    
    if gaps:
        max_gap = max(g[1] for g in gaps)
        diagnostics['warnings'].append(f"Found {len(gaps)} gaps, max: {max_gap:.3f}mm")
        print(f"   Total gaps found: {len(gaps)}, Maximum gap: {max_gap:.3f}mm")
    else:
        print(f"   ✅ No gaps detected (tolerance: {CONFIG['gap_tolerance']}mm)")
    
    # 3. Endpoint Convergence Check
    print("\n3️⃣ ENDPOINT CONVERGENCE CHECK")
    print("-" * 40)
    
    bb = wire.BoundBox
    z_min, z_max = bb.ZMin, bb.ZMax
    
    # Check convergence at both ends with dense sampling
    for end_name, z_pos in [("BOTTOM (tip)", z_min), ("TOP", z_max)]:
        print(f"\n   Analyzing {end_name} at Z={z_pos:.1f}:")
        
        # Sample near the endpoint
        sample_positions = [z_pos + i * CONFIG['diagnostic_slice_density'] 
                          for i in range(-5, 6)]
        
        chord_measurements = []
        for sample_z in sample_positions:
            if z_min <= sample_z <= z_max:
                plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                                     Vector(0, 0, sample_z), Vector(0, 0, 1))
                section = wire.section(plane)
                
                if len(section.Vertexes) >= 2:
                    pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
                    chord = pts[-1].x - pts[0].x
                    chord_measurements.append((sample_z, chord))
        
        if chord_measurements:
            for z, chord in chord_measurements[:3]:  # Show first 3
                print(f"      Z={z:.1f}: chord={chord:.2f}mm")
            
            min_chord = min(c[1] for c in chord_measurements)
            min_z = [c[0] for c in chord_measurements if c[1] == min_chord][0]
            
            print(f"      Minimum chord: {min_chord:.2f}mm at Z={min_z:.1f}")
            
            if end_name == "BOTTOM (tip)" and min_chord > 10.0:
                diagnostics['errors'].append(f"Tip doesn't close: minimum chord is {min_chord:.2f}mm")
                diagnostics['valid'] = False
    
    # 4. Profile Bounds vs Actual Closure
    print("\n4️⃣ PROFILE BOUNDS VS ACTUAL CLOSURE")
    print("-" * 40)
    
    print(f"   BoundBox Z range: {z_min:.1f} to {z_max:.1f} (height: {z_max-z_min:.1f}mm)")
    
    # Find actual convergence points by sampling
    convergence_threshold = 5.0  # Consider converged if chord < 5mm
    actual_bottom = None
    actual_top = None
    
    # Sample from bottom up
    for z in range(int(z_min)-10, int(z_max)+10):
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                             Vector(0, 0, float(z)), Vector(0, 0, 1))
        section = wire.section(plane)
        
        if len(section.Vertexes) >= 2:
            pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
            chord = pts[-1].x - pts[0].x
            
            if chord < convergence_threshold and actual_bottom is None:
                actual_bottom = z
            if chord >= convergence_threshold:
                actual_top = z
    
    if actual_bottom:
        print(f"   Actual convergence bottom: Z={actual_bottom:.1f} (vs BBox: {z_min:.1f})")
    else:
        print(f"   ⚠️ No convergence found at bottom (threshold: {convergence_threshold}mm)")
    
    # 5. Chord Progression Analysis
    print("\n5️⃣ CHORD PROGRESSION ANALYSIS")
    print("-" * 40)
    
    # Sample chord lengths throughout the profile
    num_samples = 50
    chord_profile = []
    
    for i in range(num_samples + 1):
        z = z_min + (i / num_samples) * (z_max - z_min)
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        section = wire.section(plane)
        
        if len(section.Vertexes) >= 2:
            pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
            chord = pts[-1].x - pts[0].x
            chord_profile.append((z, chord))
    
    if chord_profile:
        # Check for monotonic progression near tip
        bottom_10 = chord_profile[:10]
        reversals = []
        
        for i in range(1, len(bottom_10)):
            if bottom_10[i][1] < bottom_10[i-1][1]:  # Chord got smaller (expected)
                pass
            else:  # Chord increased (unexpected near tip)
                reversals.append(i)
        
        if reversals:
            print(f"   ⚠️ Non-monotonic chord progression near tip at indices: {reversals}")
            diagnostics['warnings'].append(f"Chord progression reversal near tip")
        else:
            print(f"   ✅ Chord progression is monotonic near tip")
        
        # Show progression
        print(f"\n   Chord progression (first 5 samples from tip):")
        for z, chord in chord_profile[:5]:
            print(f"      Z={z:.1f}: {chord:.2f}mm")
    
    # 6. Extended Range Probing
    print("\n6️⃣ EXTENDED RANGE PROBING")
    print("-" * 40)
    
    # Check beyond bounding box
    extend_distance = 20.0
    extended_checks = [
        ("Below minimum", z_min - extend_distance),
        ("Above maximum", z_max + extend_distance)
    ]
    
    for desc, z in extended_checks:
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        section = wire.section(plane)
        
        if len(section.Vertexes) > 0:
            print(f"   ⚠️ {desc} (Z={z:.1f}): Found {len(section.Vertexes)} vertices!")
            diagnostics['warnings'].append(f"Geometry exists beyond BoundBox at Z={z:.1f}")
        else:
            print(f"   ✅ {desc} (Z={z:.1f}): No geometry found")
    
    # 7. Visual Debugging Objects
    print("\n7️⃣ CREATING VISUAL DEBUG MARKERS")
    print("-" * 40)
    
    # Create markers at critical points
    if chord_profile:
        # Mark minimum chord location
        min_chord_data = min(chord_profile, key=lambda x: x[1])
        marker_pt = Part.Vertex(Vector(0, 0, min_chord_data[0]))
        marker = doc.addObject("Part::Feature", "MinChordMarker")
        marker.Shape = marker_pt
        marker.ViewObject.PointSize = 10
        marker.ViewObject.PointColor = (1.0, 0.0, 0.0)
        print(f"   Created marker at minimum chord: Z={min_chord_data[0]:.1f}, chord={min_chord_data[1]:.2f}mm")
    
    # Create diagnostic slice wireframes near tip
    print(f"   Creating diagnostic slices near tip...")
    for i in range(5):
        z = z_min + i * CONFIG['diagnostic_slice_density']
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        section = wire.section(plane)
        
        if len(section.Vertexes) >= 2:
            pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
            debug_line = Part.makeLine(pts[0], pts[-1])
            feat = doc.addObject("Part::Feature", f"DiagSlice_{i}")
            feat.Shape = debug_line
            feat.ViewObject.LineColor = (0.0, 1.0, 0.0)
            feat.ViewObject.LineWidth = 3
    
    # Summary
    print("\n" + "="*80)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*80)
    
    if diagnostics['errors']:
        print("\n❌ ERRORS:")
        for error in diagnostics['errors']:
            print(f"   • {error}")
    
    if diagnostics['warnings']:
        print("\n⚠️ WARNINGS:")
        for warning in diagnostics['warnings']:
            print(f"   • {warning}")
    
    if diagnostics['valid']:
        print("\n✅ Profile passed basic validation, but check warnings above")
    else:
        print("\n❌ Profile has critical issues that will prevent proper foil generation")
    
    print("="*80 + "\n")
    
    return diagnostics


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
    print(f"   Enhanced diagnostics for tip closure analysis")
    
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
    
    # Run comprehensive diagnostics
    diagnostics = comprehensive_profile_diagnostics(shrunk_wire, doc)
    
    if not diagnostics['valid']:
        print("\n⛔ STOPPING: Critical profile issues detected. Fix the profile and retry.")
        return
    
    if diagnostics['warnings']:
        response = input("\n⚠️ Warnings detected. Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted by user.")
            return
    
    # Generate adaptive slice levels based on profile curvature
    levels = generate_adaptive_levels(
        shrunk_wire, 
        CONFIG['base_slice_spacing'],
        CONFIG['min_slice_spacing'],
        CONFIG['max_slice_spacing']
    )
    
    print(f"\n🔪 Slicing at {len(levels)} adaptive levels")
    
    # Slice into chords
    chords = []
    breakdown_z = None  # Track where breakdown occurs
    
    for z in levels:
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        section = shrunk_wire.section(plane)
        
        if len(section.Vertexes) >= 2:
            pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
            chord_length = pts[-1].x - pts[0].x
            
            if chord_length > CONFIG['min_chord_length']:
                # Check for breakdown condition ONLY for chords we're going to use
                if chord_length * 0.16 < 2.0:  # 16% thickness would be less than 2mm
                    print(f"⚠️ Breakdown detected at Z={z:.1f}: thickness would be {chord_length * 0.16:.2f}mm")
                    breakdown_z = z
                    break
                
                chords.append(((pts[0].x, z), (pts[-1].x, z)))
    
    if not chords:
        print("❌ No valid chords found")
        return
    
    print(f"✅ Found {len(chords)} chords")
    
    print(f"🎯 NACA 0016 base with thickness tapering for small chords")
    print(f"\n🔬 SECTION GENERATION OUTPUT:")
    print(f"{'Index':<6} {'Z':<10} {'Chord':<10} {'Thick%':<10} {'AbsThick':<10} {'Valid':<10} {'Area':<10} {'Edges':<10}")
    print("="*86)
    
    # Generate NACA sections with detailed diagnostics
    section_wires = []
    last_valid_wire = None
    last_valid_center = None
    prev_area = None
    problematic_sections = []
    
    for idx, ((x1, z), (x2, _)) in enumerate(chords):
        # Position and orientation
        p_le = Vector(x2, 0.0, z)  # Leading edge at min x
        p_te = Vector(x1, 0.0, z)  # Trailing edge at max x
        vec = p_te - p_le
        chord_len = vec.Length
        ux = vec.normalize()
        uy = ux.cross(Vector(0, 0, 1)).normalize()
        
        # Taper thickness for small chords
        if chord_len > 50.0:
            thickness_percent = 16.0
        elif chord_len > 20.0:
            thickness_percent = 8.0 + (chord_len - 20.0) / 30.0 * 8.0
        else:
            thickness_percent = 8.0
        
        absolute_thickness = chord_len * (thickness_percent / 100.0)
        
        # Generate NACA points
        coords = naca_coordinates(chord_len, thickness_percent, CONFIG['naca_points'])
        pts3d = [p_le + ux * x + uy * y for x, y in coords]
        
        # Create wire and validate
        wire = Part.makePolygon(pts3d)
        
        # Validation checks
        is_valid = wire.isValid()
        is_null = wire.isNull()
        num_edges = len(wire.Edges)
        
        # Try to get area
        try:
            face = Part.Face(wire)
            area = face.Area
            
            # Check for area collapse
            if prev_area is not None and area < prev_area * 0.5:
                problematic_sections.append(idx)
                
            prev_area = area
        except:
            area = -1  # Error getting area
            problematic_sections.append(idx)
        
        # Print diagnostic info
        status = "OK" if is_valid and not is_null else "FAIL"
        if idx in problematic_sections:
            status = "PROBLEM"
            
        print(f"{idx:<6} {z:<10.1f} {chord_len:<10.2f} {thickness_percent:<10.2f} {absolute_thickness:<10.2f} {status:<10} {area:<10.2f} {num_edges:<10}")
        
        # Store wire regardless for now (to see full pattern)
        section_wires.append(wire)
        last_valid_wire = wire
        last_valid_center = (p_le + p_te) * 0.5
    
    # Report problems
    if problematic_sections:
        print(f"\n⚠️ Problematic sections detected at indices: {problematic_sections}")
        print("   These sections show area collapse or validation issues")
        
        # Option: Remove problematic sections
        print(f"\n🔧 Attempting to remove problematic sections...")
        clean_wires = []
        for idx, wire in enumerate(section_wires):
            if idx not in problematic_sections:
                clean_wires.append(wire)
            else:
                # Stop adding sections after first problem
                print(f"   Stopping at section {idx}")
                break
        
        if len(clean_wires) > 10:  # Need minimum sections for loft
            section_wires = clean_wires
            print(f"   Using {len(section_wires)} clean sections")
        else:
            print(f"   Not enough clean sections, using all")
    
    # Add end cap if breakdown was detected OR if first chord is too large
    first_chord_length = chords[0][1][0] - chords[0][0][0]
    if breakdown_z is not None or first_chord_length > 50.0:
        print(f"\n🔧 Adding tip closure strategy...")
        
        # Strategy: Create tapered cap sections
        if section_wires:
            # Get the first (tip) section
            tip_wire = section_wires[0]
            bb = tip_wire.BoundBox
            
            # Create progressively smaller sections
            cap_sections = []
            num_cap_sections = 5
            
            for i in range(1, num_cap_sections + 1):
                scale_factor = 1.0 - (i / (num_cap_sections + 1))
                
                if scale_factor > 0.05:  # Don't go too small
                    # Create scaled version
                    transform = App.Matrix()
                    center = Vector((bb.XMin + bb.XMax)/2, (bb.YMin + bb.YMax)/2, bb.ZMin)
                    transform.scale(scale_factor, scale_factor, 1.0)
                    
                    scaled_wire = tip_wire.copy()
                    scaled_wire.transformShape(transform, True)
                    scaled_wire.translate(center * (1 - scale_factor))
                    scaled_wire.translate(Vector(0, 0, -i * 2))  # Move down
                    
                    cap_sections.append(scaled_wire)
                    print(f"   Added cap section {i} at scale {scale_factor:.2f}")
            
            # Prepend cap sections to main sections
            section_wires = cap_sections + section_wires
    
    print(f"\n✅ Final: {len(section_wires)} sections for lofting")
    
    # Estimate complexity reduction
    uniform_levels = int((levels[-1] - levels[0]) / CONFIG['base_slice_spacing']) + 1
    complexity_reduction = (1 - len(levels) / uniform_levels) * 100
    print(f"📊 Complexity reduced by {complexity_reduction:.0f}% vs uniform slicing")
    
    # Loft sections
    try:
        loft = Part.makeLoft(section_wires, solid=True, ruled=False)
        print("✅ Loft complete")
    except Exception as e:
        print(f"❌ Loft failed: {e}")
        print("   Trying with ruled=True...")
        try:
            loft = Part.makeLoft(section_wires, solid=True, ruled=True)
            print("✅ Loft complete (ruled)")
        except Exception as e2:
            print(f"❌ Ruled loft also failed: {e2}")
            return
    
    # Create display object
    foil = doc.addObject("Part::Feature", f"{BOAT_NAME}_Foil")
    foil.Shape = loft
    foil.ViewObject.ShapeColor = (0.6, 0.8, 1.0)
    foil.ViewObject.DisplayMode = "Shaded"
    
    # Export
    export_geometry(foil, BOAT_NAME + "_Foil")
    
    doc.recompute()
    print(f"🛥️ {BOAT_NAME} foil complete with enhanced diagnostics!\n")


# Run the build
if __name__ == "__main__" or __name__ == "__builtin__":
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("FoilBuild")
    build_foil_from_step(doc)