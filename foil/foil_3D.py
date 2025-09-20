"""
Foil 3D Pipeline - Converts STEP outline profiles to 3D NACA foil via chord slicing and lofting.
Version 1.7.1 - Production version with improved leading edge smoothness
Exports both STEP and STL files.
"""

import os
from PySide2 import QtWidgets
import FreeCAD as App, Part
from FreeCAD import Vector
import math

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth
VERSION = "1.7.1"  # Improved leading edge smoothness

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
    'naca_points': max(30, 60 // COMPLEXITY_REDUCTION),  # Increased for smoother leading edge
    'leading_edge_bias': 0.35,   # Concentrate 35% of points in first 10% of chord
    'base_slice_spacing': 10.0 * COMPLEXITY_REDUCTION,  # Base spacing
    'min_slice_spacing': 5.0,    # mm increased minimum spacing
    'max_slice_spacing': 20.0,   # mm increased maximum spacing
    'tip_zone_height': 10.0,    # mm reduced tip zone height
    'tip_spacing': 2.0,         # mm increased tip spacing
    'curvature_samples': 50,     # Reduced samples for faster analysis
    'min_chord_length': 2.0,     # mm minimum chord to use NACA
    'max_sections': 60,         # Maximum number of sections to generate
    'stl_tolerance': min(0.2, 0.05 * COMPLEXITY_REDUCTION),  # STL tolerance
    'plane_size': 1100,          # mm sectioning plane size
    'gap_tolerance': 0.1,        # mm tolerance for gap detection
    'diagnostic_slice_density': 0.5,  # mm spacing for diagnostic slices near tips
}

print(f"🔧 Complexity reduction: {COMPLEXITY_REDUCTION}x")
print(f"   Points per section: {CONFIG['naca_points']} (optimized for smooth leading edge)")
print(f"   Leading edge bias: {CONFIG['leading_edge_bias']*100:.0f}% of points in first 10% of chord")
print(f"   Base slice spacing: {CONFIG['base_slice_spacing']}mm")
print(f"   Adaptive spacing: {CONFIG['min_slice_spacing']}-{CONFIG['max_slice_spacing']}mm")
print(f"   Tip zone: {CONFIG['tip_zone_height']}mm with {CONFIG['tip_spacing']}mm spacing")
print(f"   Max sections: {CONFIG['max_sections']} (performance limit)")
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
                elif len(section.Vertexes) == 1:
                    # Single point convergence
                    chord_measurements.append((sample_z, 0.0))
        
        if chord_measurements:
            for z, chord in chord_measurements[:3]:  # Show first 3
                print(f"      Z={z:.1f}: chord={chord:.2f}mm")
            
            min_chord = min(c[1] for c in chord_measurements)
            min_z = [c[0] for c in chord_measurements if c[1] == min_chord][0]
            
            print(f"      Minimum chord: {min_chord:.2f}mm at Z={min_z:.1f}")
            
            diagnostics['measurements'][f'{end_name.lower()}_min_chord'] = min_chord
    
    # 4. Profile Bounds
    print("\n4️⃣ PROFILE BOUNDS")
    print("-" * 40)
    
    print(f"   BoundBox Z range: {z_min:.1f} to {z_max:.1f} (height: {z_max-z_min:.1f}mm)")
    print(f"   BoundBox X range: {bb.XMin:.1f} to {bb.XMax:.1f} (width: {bb.XMax-bb.XMin:.1f}mm)")
    
    # 7. Visual Debugging Objects (disabled to avoid downstream interference)
    # Diagnostic visualization removed - data still collected above
    
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
        print("\n✅ Profile passed basic validation")
    else:
        print("\n❌ Profile has critical issues that will prevent proper foil generation")
    
    print("="*80 + "\n")
    
    return diagnostics


def analyze_profile_curvature(wire, num_samples=50):
    """
    Analyze the curvature along the wire to identify regions needing more slices.
    Returns: list of (z_position, curvature_value) tuples
    """
    bb = wire.BoundBox
    z_min, z_max = bb.ZMin, bb.ZMax
    z_range = z_max - z_min
    
    curvatures = []
    
    for i in range(num_samples):
        z = z_min + (i / (num_samples - 1)) * z_range
        
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        section = wire.section(plane)
        
        if len(section.Vertexes) >= 2:
            pts = sorted([v.Point for v in section.Vertexes], key=lambda p: p.x)
            
            if i > 0 and len(curvatures) > 0:
                prev_chord = curvatures[-1][2] if len(curvatures[-1]) > 2 else 0
                curr_chord = pts[-1].x - pts[0].x
                
                curvature = abs(curr_chord - prev_chord) / (z_range / num_samples)
                curvatures.append((z, curvature, curr_chord))
            else:
                curr_chord = pts[-1].x - pts[0].x
                curvatures.append((z, 0.0, curr_chord))
    
    if curvatures:
        max_curv = max(c[1] for c in curvatures)
        if max_curv > 0:
            curvatures = [(z, c/max_curv, chord) for z, c, chord in curvatures]
    
    return curvatures


def generate_adaptive_levels(wire, base_spacing, min_spacing, max_spacing):
    """
    Generate slice levels with adaptive spacing based on profile curvature.
    Dense spacing at tip, adaptive elsewhere, with max section limit.
    """
    bb = wire.BoundBox
    z_min, z_max = bb.ZMin, bb.ZMax
    z_range = z_max - z_min
    
    print(f"🔍 Analyzing profile curvature...")
    
    levels = []
    
    # CRITICAL: Dense spacing near tip for proper closure (but not too dense)
    tip_zone_end = min(z_min + CONFIG['tip_zone_height'], z_max)
    z = z_min
    while z < tip_zone_end and z < z_max and len(levels) < CONFIG['max_sections'] // 3:
        levels.append(z)
        z += CONFIG['tip_spacing']
    print(f"   Added {len(levels)} levels in tip zone ({CONFIG['tip_zone_height']}mm)")
    
    # Calculate remaining budget
    remaining_sections = CONFIG['max_sections'] - len(levels) - 1  # -1 for top
    remaining_height = z_max - z
    
    if remaining_sections <= 0:
        # Just add the top
        if not levels or abs(levels[-1] - z_max) > 0.01:
            levels.append(z_max)
        print(f"   ⚠️ Section budget exhausted in tip zone")
        return levels
    
    # Calculate uniform spacing for remaining height
    uniform_spacing = remaining_height / remaining_sections
    uniform_spacing = max(uniform_spacing, min_spacing)
    uniform_spacing = min(uniform_spacing, max_spacing)
    
    print(f"   Using {uniform_spacing:.1f}mm spacing for main body")
    
    # Add sections with uniform spacing
    current_z = z
    while current_z < z_max - min_spacing and len(levels) < CONFIG['max_sections'] - 1:
        current_z += uniform_spacing
        if current_z < z_max - 0.01:  # Avoid getting too close to z_max
            levels.append(current_z)
    
    # Always include the top (but avoid duplicates)
    if not levels or abs(levels[-1] - z_max) > 0.01:
        levels.append(z_max)
    
    # Remove any duplicate levels (safety check)
    levels = sorted(list(set(levels)))
    
    # Report spacing distribution
    spacings = [levels[i+1] - levels[i] for i in range(len(levels)-1)]
    if spacings:
        avg_spacing = sum(spacings) / len(spacings)
        min_spacing_actual = min(spacings)
        max_spacing_actual = max(spacings)
    else:
        avg_spacing = base_spacing
        min_spacing_actual = base_spacing
        max_spacing_actual = base_spacing
    
    print(f"✨ Adaptive slicing complete:")
    print(f"   Levels: {len(levels)} (target max: {CONFIG['max_sections']})")
    print(f"   Spacing: min={min_spacing_actual:.1f}mm, avg={avg_spacing:.1f}mm, max={max_spacing_actual:.1f}mm")
    
    # Verify no duplicates
    if len(levels) != len(set(levels)):
        print(f"   ⚠️ Warning: Duplicate levels detected and removed")
    
    return levels


def naca_coordinates(chord_length, thickness_percent, num_pts=60):
    """Generate NACA 00XX coordinates with enhanced leading edge resolution."""
    
    # Create biased point distribution for better leading edge definition
    # More points concentrated at the leading edge where curvature is highest
    angles = []
    le_bias = CONFIG.get('leading_edge_bias', 0.35)  # 35% of points in first 10% of chord
    
    # Points for leading edge region (0 to 10% chord)
    le_points = int(num_pts * le_bias / 2)
    for i in range(le_points + 1):
        angle = (i / le_points) * math.pi * 0.3  # First 30% of the angle range
        angles.append(angle)
    
    # Points for the rest of the airfoil
    remaining_points = num_pts // 2 - le_points
    for i in range(1, remaining_points):
        angle = math.pi * 0.3 + (i / remaining_points) * math.pi * 0.7
        angles.append(angle)
    
    x_positions = [(1 - math.cos(angle)) / 2 for angle in angles]
    
    coords = []
    thickness_ratio = thickness_percent / 100.0
    
    for i, x_norm in enumerate(x_positions):
        x = x_norm * chord_length
        
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
        
        if i > 0:
            coords.append((x, yt))
    
    for x, y in reversed(coords[:-1]):
        coords.append((x, -y))
    
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
    
    if mesh_obj.isSolid():
        print(f"✅ Mesh is watertight")
    else:
        print(f"⚠️ Mesh has open edges")
    
    print(f"📊 Mesh: {mesh_obj.CountPoints} vertices, {mesh_obj.CountFacets} facets")
    mesh_obj.write(stl_path)
    print(f"✅ Exported STL: {stl_path}")


def validate_section(section_vertices, z_level, wire_bbox):
    """
    Validate section results before accepting them as a valid chord.
    Returns: (is_valid, cleaned_vertices, warning_message)
    """
    # Special handling for tip/convergence points
    if len(section_vertices) == 1:
        # Single vertex at tip - this is valid and important!
        return True, section_vertices, "Single point (tip/convergence)"
    
    if len(section_vertices) < 2:
        return False, [], f"Only {len(section_vertices)} vertices found"
    
    # Check for suspicious points
    suspicious_points = []
    valid_points = []
    
    for v in section_vertices:
        point = v.Point
        
        # Check if point is within reasonable bounds
        x_margin = wire_bbox.XLength * 0.1
        if point.x < wire_bbox.XMin - x_margin or point.x > wire_bbox.XMax + x_margin:
            suspicious_points.append(f"x={point.x:.1f} outside bounds")
            continue
            
        # Check Y coordinate should be near 0 (planar cut)
        if abs(point.y) > 1.0:
            suspicious_points.append(f"y={point.y:.3f} not planar")
            continue
            
        valid_points.append(v)
    
    # Accept whatever valid points we have (could be 1 for tip)
    if len(valid_points) == 0:
        warning = f"No valid points found"
        if suspicious_points:
            warning += f" (rejected: {', '.join(suspicious_points)})"
        return False, [], warning
    
    if len(valid_points) == 1:
        # Single valid point - likely near tip
        return True, valid_points, "Single valid point"
    
    # Check chord length is reasonable
    pts = sorted([v.Point for v in valid_points], key=lambda p: p.x)
    chord_length = pts[-1].x - pts[0].x
    
    if chord_length < 0:
        return False, [], f"Negative chord length: {chord_length:.2f}mm"
    
    if chord_length > wire_bbox.XLength * 1.2:
        return False, [], f"Chord length {chord_length:.1f}mm exceeds wire width"
    
    return True, valid_points, None


def build_foil_from_step(doc):
    """Main pipeline: STEP → chords → NACA sections → loft → export."""
    
    print(f"\n🛥️ Foil Build v{VERSION} for {BOAT_NAME}")
    print(f"   Enhanced tip handling and section validation")
    
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
    
    # Generate adaptive slice levels with enhanced tip handling
    levels = generate_adaptive_levels(
        shrunk_wire, 
        CONFIG['base_slice_spacing'],
        CONFIG['min_slice_spacing'],
        CONFIG['max_slice_spacing']
    )
    
    print(f"\n🔪 Slicing at {len(levels)} adaptive levels")
    
    # Get wire bounding box for validation
    wire_bbox = shrunk_wire.BoundBox
    
    # Slice into chords with improved validation
    chords = []
    single_point_sections = []
    skipped_sections = []
    
    for z in levels:
        plane = Part.makePlane(CONFIG['plane_size'], CONFIG['plane_size'], 
                              Vector(0, 0, z), Vector(0, 0, 1))
        section = shrunk_wire.section(plane)
        
        # Validate section with enhanced tip handling
        is_valid, valid_vertices, warning = validate_section(section.Vertexes, z, wire_bbox)
        
        if not is_valid:
            print(f"⚠️ Skipping section at Z={z:.1f}: {warning}")
            skipped_sections.append((z, warning))
            continue
        
        # Handle based on number of valid vertices
        if len(valid_vertices) == 1:
            # Single point - store for tip closure
            pt = valid_vertices[0].Point
            single_point_sections.append((z, pt))
            chords.append(((pt.x, z), (pt.x, z)))  # Zero-length chord
        else:
            # Normal chord
            pts = sorted([v.Point for v in valid_vertices], key=lambda p: p.x)
            chord_length = pts[-1].x - pts[0].x
            
            # Accept even very small chords near tip
            if chord_length >= 0:
                chords.append(((pts[0].x, z), (pts[-1].x, z)))
    
    if not chords:
        print("❌ No valid chords found")
        return
    
    print(f"✅ Found {len(chords)} valid chords")
    print(f"   Including {len(single_point_sections)} single-point sections")
    if skipped_sections:
        print(f"⚠️ Skipped {len(skipped_sections)} invalid sections")
    
    print(f"🎯 NACA 0016 base with thickness tapering for small chords")
    print(f"\n🔬 SECTION GENERATION OUTPUT:")
    print(f"{'Index':<6} {'Z':<10} {'Chord':<10} {'Thick%':<10} {'AbsThick':<10} {'Type':<15}")
    print("="*71)
    
    # Generate NACA sections with better tip handling
    section_wires = []
    
    for idx, ((x1, z), (x2, _)) in enumerate(chords):
        chord_len = abs(x2 - x1)
        
        # Handle different chord sizes
        if chord_len < 0.01:  # Essentially a point
            # Create tiny circle for tip closure
            center = Vector((x1 + x2) / 2, 0.0, z)
            circle = Part.makeCircle(1.0, center, Vector(0, 0, 1))
            wire = Part.Wire([circle])
            section_type = "TIP_CIRCLE"
            thickness_percent = 0
            absolute_thickness = 0
            
        elif chord_len < CONFIG['min_chord_length']:
            # Very small chord - create ellipse
            center = Vector((x1 + x2) / 2, 0.0, z)
            ellipse = Part.Ellipse(center, chord_len/2, chord_len * 0.1, 0)
            wire = Part.Wire([Part.Edge(ellipse)])
            section_type = "SMALL_ELLIPSE"
            thickness_percent = 10.0
            absolute_thickness = chord_len * 0.1
            
        else:
            # Normal NACA section
            # Position and orientation (fixed comments)
            p_le = Vector(x2, 0.0, z)  # Leading edge at max x (front of rudder)
            p_te = Vector(x1, 0.0, z)  # Trailing edge at min x (back of rudder)
            vec = p_te - p_le
            ux = vec.normalize()
            uy = ux.cross(Vector(0, 0, 1)).normalize()
            
            # Taper thickness for small chords
            if chord_len > 50.0:
                thickness_percent = 16.0
            elif chord_len > 20.0:
                thickness_percent = 8.0 + (chord_len - 20.0) / 30.0 * 8.0
            else:
                thickness_percent = max(4.0, 8.0 * (chord_len / 20.0))
            
            absolute_thickness = chord_len * (thickness_percent / 100.0)
            
            # Generate NACA points
            coords = naca_coordinates(chord_len, thickness_percent, CONFIG['naca_points'])
            pts3d = [p_le + ux * x + uy * y for x, y in coords]
            
            # Create wire
            wire = Part.makePolygon(pts3d)
            section_type = "NACA"
        
        # Store wire
        section_wires.append(wire)
        
        # Print diagnostic info
        print(f"{idx:<6} {z:<10.1f} {chord_len:<10.2f} {thickness_percent:<10.2f} "
              f"{absolute_thickness:<10.2f} {section_type:<15}")
    
    print(f"\n✅ Generated {len(section_wires)} sections")
    print(f"📦 Creating 3D loft from {len(section_wires)} sections...")
    
    # Single loft attempt - prioritize smoothness over speed
    try:
        # Use standard (smooth) loft for better surface quality
        print("   Attempting smooth loft for better surface quality...")
        loft = Part.makeLoft(section_wires, solid=True, ruled=False)
        print("   ✅ Loft successful")
    except Exception as e:
        print(f"   ⚠️ Smooth loft failed: {e}")
        print("   Attempting ruled loft as fallback...")
        try:
            loft = Part.makeLoft(section_wires, solid=True, ruled=True)
            print("   ✅ Ruled loft successful (may appear more faceted)")
        except Exception as e2:
            print(f"\n❌ All loft attempts failed: {e2}")
            print(f"   Geometry too complex with {len(section_wires)} sections")
            print(f"   Try reducing max_sections in CONFIG (currently {CONFIG['max_sections']})")
            return
    
    # Create display object
    foil = doc.addObject("Part::Feature", f"{BOAT_NAME}_Foil")
    foil.Shape = loft
    foil.ViewObject.ShapeColor = (0.6, 0.8, 1.0)
    foil.ViewObject.DisplayMode = "Shaded"
    
    # Export
    export_geometry(foil, BOAT_NAME + "_Foil")
    
    doc.recompute()
    print(f"🛥️ {BOAT_NAME} foil complete!\n")


# Run the build
if __name__ == "__main__" or __name__ == "__builtin__":
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("FoilBuild")
    build_foil_from_step(doc)