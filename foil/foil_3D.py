# foil/foil_3D.py
"""
Foil 3D Pipeline - Boat-Centric Version with Enhanced Surface Quality
Converts STEP outline profiles to 3D NACA foil via chord slicing and lofting.
Enhanced for smoother surfaces and better mesh quality.
"""

import sys, os
from PySide2 import QtWidgets
import FreeCAD as App, FreeCADGui as Gui, Part
from FreeCAD import Vector
import math
from foil.geometry import slice_chords
from rudderlib_foil.naca import naca4_coordinates

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth - change this for different boats
VERSION = "1.1.1"

# Derived paths - everything flows from boat name
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/output/outline"  # Takes input from outline output
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/foil"

# File specifications
PROFILES_STEP_FILE = f"{BOAT_NAME}_Outline.step"  # Input from outline step
FOIL_STEP_FILE = f"{BOAT_NAME}_Foil.step"          # Output for integration step

# Configuration - Enhanced for Smooth Surfaces
CONFIG = {
    # NACA Profile Settings - MackenSea Specific Measurements
    'naca_camber': '00',         # NACA camber digits (00 = symmetric, 23 = cambered)
    'thickness_percent': None,   # % thickness - leave blank to use apex measurement
    'apex_at_top': 64.0,         # mm measured thickness at top (44mm stock + 10mm each side)
    'thickness_tolerance': 2.0,  # mm tolerance for contradiction warning
    'naca_points': 80,           # Balanced: Good quality without excessive points (was 150)
    'use_cosine_clustering': True,  # Keep: Significant quality improvement, minimal cost
    
    # Slicing Settings - Balanced Performance
    'slice_spacing': 3.0,        # Balanced: Better than original 4.0mm, faster than 2.0mm
    'adaptive_slicing': False,   # Disabled: Too much processing overhead
    'curvature_threshold': 0.1,  # Unused when adaptive_slicing=False
    'min_chord_length': 10.0,    # mm minimum chord length to include
    
    # Surface Quality Settings - Performance Optimized
    'use_bspline_sections': False,   # Disabled: Polygons are fast and adequate
    'bspline_degree': 3,            # Unused when use_bspline_sections=False
    'surface_smoothing': False,     # Disabled: Minimal visual benefit, significant cost
    'smoothing_iterations': 2,      # Unused when surface_smoothing=False
    
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
SLICE_SPACING = CONFIG['slice_spacing']
PLANE_SIZE = CONFIG['plane_size'] 
NACA_POINTS = CONFIG['naca_points']


def cosine_point_distribution(n_points):
    """
    Enhanced: Generate cosine-clustered parameter distribution for better airfoil point spacing.
    Clusters more points at leading and trailing edges where curvature is highest.
    
    Args:
        n_points: Total number of points
        
    Returns:
        List of parameters from 0 to 1 with cosine clustering
    """
    if n_points < 4:
        return [i / (n_points - 1) for i in range(n_points)]
    
    # Half-cosine distribution from 0 to pi
    angles = [i * math.pi / (n_points - 1) for i in range(n_points)]
    # Convert to 0-1 range with clustering at ends
    params = [(1 - math.cos(angle)) / 2 for angle in angles]
    return params


def enhanced_naca_coordinates(chord_length, thickness_percent, num_pts=150, use_cosine=True):
    """
    Enhanced: Generate NACA coordinates with better point distribution and optional cosine clustering.
    
    Args:
        chord_length: Length of chord
        thickness_percent: NACA thickness percentage
        num_pts: Number of points
        use_cosine: Whether to use cosine clustering
        
    Returns:
        List of (x, z) coordinates for NACA airfoil
    """
    if use_cosine:
        # Use cosine clustering for better surface quality
        params = cosine_point_distribution(num_pts // 2 + 1)  # Half airfoil
        x_coords = [p * chord_length for p in params]
        
        # Generate upper and lower surfaces with cosine distribution
        coords = []
        thickness_ratio = thickness_percent / 100.0
        
        # Upper surface (reversed for proper ordering)
        for x in reversed(x_coords[:-1]):  # Skip last point to avoid duplication
            x_norm = x / chord_length
            # NACA 4-digit thickness distribution
            yt = 5 * thickness_ratio * chord_length * (
                0.2969 * math.sqrt(x_norm) - 
                0.1260 * x_norm - 
                0.3516 * x_norm**2 + 
                0.2843 * x_norm**3 - 
                0.1015 * x_norm**4
            )
            coords.append((x, yt))
        
        # Lower surface
        for x in x_coords:
            x_norm = x / chord_length
            yt = 5 * thickness_ratio * chord_length * (
                0.2969 * math.sqrt(x_norm) - 
                0.1260 * x_norm - 
                0.3516 * x_norm**2 + 
                0.2843 * x_norm**3 - 
                0.1015 * x_norm**4
            )
            coords.append((x, -yt))
            
        return coords
    else:
        # Fall back to original function
        return naca4_coordinates(chord_length, thickness_percent, num_pts=num_pts)


def calculate_wire_curvature(wire, num_samples=50):
    """
    Enhanced: Calculate approximate curvature along a wire for adaptive slicing.
    
    Args:
        wire: FreeCAD wire object
        num_samples: Number of sample points along wire
        
    Returns:
        List of (parameter, curvature) tuples
    """
    try:
        curvatures = []
        for i in range(num_samples):
            param = i / (num_samples - 1)
            # Sample three close points to estimate curvature
            if param < 0.01:
                p1 = wire.valueAt(0)
                p2 = wire.valueAt(0.01)
                p3 = wire.valueAt(0.02)
            elif param > 0.99:
                p1 = wire.valueAt(0.98)
                p2 = wire.valueAt(0.99)
                p3 = wire.valueAt(1.0)
            else:
                p1 = wire.valueAt(param - 0.01)
                p2 = wire.valueAt(param)
                p3 = wire.valueAt(param + 0.01)
            
            # Estimate curvature using three-point method
            a = (p2 - p1).Length
            b = (p3 - p2).Length
            c = (p3 - p1).Length
            
            if a > 0 and b > 0 and c > 0:
                # Area of triangle
                s = (a + b + c) / 2
                area = math.sqrt(max(0, s * (s - a) * (s - b) * (s - c)))
                curvature = 4 * area / (a * b * c) if (a * b * c) > 0 else 0
            else:
                curvature = 0
                
            curvatures.append((param, curvature))
        
        return curvatures
    except:
        # Fallback to uniform distribution if curvature calculation fails
        return [(i / (num_samples - 1), 0.1) for i in range(num_samples)]


def generate_adaptive_slice_levels(wire, config):
    """
    Enhanced: Generate slice levels with adaptive spacing based on curvature.
    
    Args:
        wire: FreeCAD wire to analyze
        config: Configuration dictionary
        
    Returns:
        List of Z-levels for slicing
    """
    bb = wire.BoundBox
    total_height = bb.ZMax - bb.ZMin
    
    if not config.get('adaptive_slicing', False) or total_height < config['slice_spacing']:
        # Fall back to uniform spacing
        num_levels = int(total_height / config['slice_spacing']) + 1
        levels = [bb.ZMin + i * config['slice_spacing'] for i in range(num_levels)]
        if levels[-1] != bb.ZMax:
            levels.append(bb.ZMax)
        return levels
    
    try:
        # Calculate curvature along the wire
        curvatures = calculate_wire_curvature(wire)
        curvature_threshold = config.get('curvature_threshold', 0.1)
        base_spacing = config['slice_spacing']
        
        levels = [bb.ZMin]
        current_z = bb.ZMin
        
        for i, (param, curvature) in enumerate(curvatures[1:], 1):
            # Adapt spacing based on curvature
            if curvature > curvature_threshold:
                spacing = base_spacing * 0.5  # Finer spacing at high curvature
            else:
                spacing = base_spacing
            
            # Map parameter to Z coordinate
            target_z = bb.ZMin + param * total_height
            
            # Add intermediate levels if needed
            while current_z + spacing < target_z:
                current_z += spacing
                if current_z <= bb.ZMax:
                    levels.append(current_z)
        
        # Always include the end
        if levels[-1] != bb.ZMax:
            levels.append(bb.ZMax)
            
        print(f"🎯 Adaptive slicing: {len(levels)} levels (avg spacing: {total_height/(len(levels)-1):.1f}mm)")
        return levels
        
    except Exception as e:
        print(f"⚠️ Adaptive slicing failed, falling back to uniform: {e}")
        # Fallback to uniform spacing
        num_levels = int(total_height / config['slice_spacing']) + 1
        levels = [bb.ZMin + i * config['slice_spacing'] for i in range(num_levels)]
        if levels[-1] != bb.ZMax:
            levels.append(bb.ZMax)
        return levels


def create_bspline_section(points, degree=3):
    """
    Enhanced: Create a B-spline curve from points instead of a polygon for smoother sections.
    
    Args:
        points: List of FreeCAD Vector points
        degree: B-spline degree (3 = cubic)
        
    Returns:
        FreeCAD Wire object with B-spline curve
    """
    try:
        if len(points) < degree + 1:
            # Fall back to polygon if insufficient points
            return Part.makePolygon(points)
        
        # Create B-spline curve
        bspline = Part.BSplineCurve()
        bspline.interpolate(points)
        edge = Part.Edge(bspline)
        return Part.Wire([edge])
    except:
        # Fallback to polygon if B-spline creation fails
        return Part.makePolygon(points)


def cleanup_sections(doc, sections):
    """
    Clean up construction sections after successful loft creation.
    
    Args:
        doc: FreeCAD document
        sections: List of section feature objects to remove
    """
    try:
        for section in sections:
            doc.removeObject(section.Name)
        print(f"🧹 Cleaned up {len(sections)} construction sections")
    except Exception as e:
        print(f"⚠️ Section cleanup failed: {e}")


def apply_surface_smoothing(shape, iterations=2):
    """
    Enhanced: Apply surface smoothing to reduce mesh artifacts.
    
    Args:
        shape: FreeCAD shape to smooth
        iterations: Number of smoothing iterations
        
    Returns:
        Smoothed shape
    """
    try:
        smoothed = shape
        for i in range(iterations):
            # Apply different smoothing techniques
            if hasattr(smoothed, 'smooth'):
                smoothed = smoothed.smooth()
            elif hasattr(smoothed, 'makeOffsetShape'):
                # Alternative: small offset and back
                temp = smoothed.makeOffsetShape(0.01, 0.01)
                smoothed = temp.makeOffsetShape(-0.01, 0.01)
        
        print(f"✅ Applied {iterations} smoothing iterations")
        return smoothed
    except Exception as e:
        print(f"⚠️ Surface smoothing failed: {e}")
        return shape


def get_profiles_step_path():
    """
    Get profiles STEP path using boat-centric logic:
    1. Try organized location first (from outline output)
    2. Fall back to file dialog if not found
    """
    organized_path = f"{INPUT_FOLDER}/{PROFILES_STEP_FILE}"
    
    if os.path.exists(organized_path):
        print(f"🚤 Using organized profiles file: {organized_path}")
        return organized_path
    else:
        print(f"🔍 {PROFILES_STEP_FILE} not found in organized location")
        print(f"   Expected: {organized_path}")
        print(f"🔍 Opening file dialog for manual selection...")
        
        # Fall back to file dialog
        dlg = QtWidgets.QFileDialog()
        dlg.setWindowTitle(f"Select {BOAT_NAME} Profiles STEP")
        dlg.setNameFilter("STEP (*.step *.stp)")
        dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        
        if dlg.exec_():
            manual_path = dlg.selectedFiles()[0]
            print(f"🔍 User selected: {manual_path}")
            return manual_path
        else:
            print("❌ No profiles file selected. Aborting.")
            return None


def ensure_output_folder():
    """Ensure output folder exists for this boat"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


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
    thickness_percent = config.get('thickness_percent')
    tolerance = config.get('thickness_tolerance', 2.0)
    
    if apex_measured is not None:
        # Find the top chord (maximum Z) to calculate percentage
        if not chords:
            print(f"❌ No chords available for apex calculation, using fallback 12%")
            calculated_percent = 12.0
        else:
            top_chord = max(chords, key=lambda chord: chord[0][1])  # Max Z value
            top_chord_length = top_chord[1][0] - top_chord[0][0]  # x2 - x1
            
            if top_chord_length <= 0:
                print(f"❌ Invalid top chord length, using fallback 12%")
                calculated_percent = 12.0
            else:
                calculated_percent = (apex_measured / top_chord_length) * 100.0
                print(f"🚤 Apex measurement: {apex_measured:.1f}mm on {top_chord_length:.1f}mm chord")
                print(f"🎯 CALCULATED NACA PERCENTAGE: {calculated_percent:.1f}%")
                
                # Check for contradiction if both values provided
                if thickness_percent is not None:
                    expected_apex = (thickness_percent / 100.0) * top_chord_length
                    difference = abs(apex_measured - expected_apex)
                    
                    if difference > tolerance:
                        print(f"⚠️ WARNING: Apex measurement ({apex_measured:.1f}mm) contradicts thickness % ({thickness_percent:.1f}%)")
                        print(f"    Expected apex for {thickness_percent:.1f}%: {expected_apex:.1f}mm (difference: {difference:.1f}mm > {tolerance:.1f}mm tolerance)")
                        print(f"    Using measured apex value ({calculated_percent:.1f}%)")
                    else:
                        print(f"✅ Apex measurement consistent with specified {thickness_percent:.1f}% (within {tolerance:.1f}mm tolerance)")
    elif thickness_percent is not None:
        calculated_percent = thickness_percent
        print(f"🚤 Using specified thickness: {thickness_percent:.1f}%")
    else:
        # Neither specified, use default
        calculated_percent = 12.0
        print(f"🚤 No thickness specified, using default: {calculated_percent:.1f}%")
    
    # Ensure reasonable bounds
    if calculated_percent < 5.0:
        print(f"⚠️ WARNING: Thickness {calculated_percent:.1f}% is very thin, clamping to 5%")
        calculated_percent = 5.0
    elif calculated_percent > 25.0:
        print(f"⚠️ WARNING: Thickness {calculated_percent:.1f}% is very thick, clamping to 25%")
        calculated_percent = 25.0
    
    # Build NACA profile code
    naca_profile = f"{config.get('naca_camber', '00')}{int(calculated_percent):02d}"
    
    return calculated_percent, naca_profile


def build_foil_from_step(doc: App.Document):
    """
    Enhanced single full-pipeline function: outline STEP → chords → NACA sections → loft
    Now with improved surface quality and smoother mesh generation.
    """
    print(f"\n🛥️ Enhanced Foil Build v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📂 Boat folder: {BOAT_FOLDER}")
    print(f"Enhanced config: {CONFIG['slice_spacing']}mm spacing, {CONFIG['naca_points']} pts/section")
    print(f"Surface enhancements: B-splines={CONFIG['use_bspline_sections']}, Smoothing={CONFIG['surface_smoothing']}")

    # Get profiles STEP path
    step_path = get_profiles_step_path()
    if not step_path:
        raise FileNotFoundError("No profiles STEP file selected")
    
    # Ensure output folder exists
    ensure_output_folder()

    # Read outline & shrunk profile with validation
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
    for name, wire, color in [(f"{BOAT_NAME}_Orig", orig_wire, CONFIG['orig_wire_color']),
                              (f"{BOAT_NAME}_Shrunk", shrunk_wire, CONFIG['shrunk_wire_color'])]:
        feat = doc.addObject("Part::Feature", name)
        feat.Shape = wire
        feat.ViewObject.ShapeColor = color
        feat.ViewObject.LineWidth = 2

    # Enhanced: Generate adaptive slice levels
    levels = generate_adaptive_slice_levels(shrunk_wire, CONFIG)
    
    print(f"🔪 Enhanced slicing: {len(levels)} levels with adaptive spacing")
    
    # Slice chords via Part.section with validation
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

    # Calculate NACA thickness based on config
    thickness_percent, naca_profile = calculate_naca_thickness(chords, CONFIG)
    print(f"🎯 Using NACA {naca_profile} ({thickness_percent:.1f}% thick)")

    # Enhanced: Generate NACA sections with improved point distribution and B-splines
    sections = []
    section_shapes = []  # Keep shapes separate from display objects
    
    for idx, ((x1, z1), (x2, z2)) in enumerate(chords):       
        p_le = Vector(x2, 0.0, z1)  # trailing edge (minimum x)
        p_te = Vector(x1, 0.0, z2)  # leading edge (maximum x)
        vec = p_te.sub(p_le)
        length = vec.Length
        ux = vec.normalize()
        uy = ux.cross(Vector(0.0, 0.0, 1.0)).normalize()

        # Enhanced: Use improved NACA coordinate generation
        coords = enhanced_naca_coordinates(
            length, 
            thickness_percent, 
            num_pts=CONFIG['naca_points'],
            use_cosine=CONFIG['use_cosine_clustering']
        )
        
        pts3 = [p_le + ux * x + uy * z for x, z in coords]
        
        # Enhanced: Create B-spline sections for smoother curves
        if CONFIG['use_bspline_sections']:
            wire = create_bspline_section(pts3, CONFIG['bspline_degree'])
        else:
            wire = Part.makePolygon(pts3)
        
        # Store shape for lofting
        section_shapes.append(wire)
        
        # Create display object (hidden by default)
        feat = doc.addObject("Part::Feature", f"{BOAT_NAME}_Section_{idx}")
        feat.Shape = wire
        feat.ViewObject.ShapeColor = CONFIG['section_color']
        feat.ViewObject.LineWidth = 1
        feat.ViewObject.Visibility = False  # Hide construction sections
        sections.append(feat)
    
    print(f"Built {len(sections)} enhanced NACA sections (hidden for clean workspace).")

    # Enhanced: Loft sections with validation and surface quality improvements
    # Validate shapes before lofting
    print(f"🔍 Validating {len(section_shapes)} sections for lofting...")
    valid_shapes = []
    for i, shape in enumerate(section_shapes):
        if shape.isValid():
            valid_shapes.append(shape)
        else:
            print(f"❌ Invalid section {i}, skipping")
    
    if len(valid_shapes) < 2:
        print(f"❌ Need at least 2 valid sections for lofting, got {len(valid_shapes)}")
        return
    
    print(f"✅ {len(valid_shapes)} valid sections ready for enhanced lofting")
    
    try:
        # Enhanced: Create loft with better surface quality
        loft = Part.makeLoft(valid_shapes, solid=True, ruled=False)
        
        # Enhanced: Apply surface smoothing if enabled
        if CONFIG['surface_smoothing']:
            loft = apply_surface_smoothing(loft, CONFIG['smoothing_iterations'])
        
        lf = doc.addObject("Part::Feature", f"{BOAT_NAME}_Foil")
        lf.Shape = loft
        lf.ViewObject.ShapeColor = CONFIG['loft_color']
        lf.ViewObject.DisplayMode = "Shaded"
        
        # Clean up construction sections after successful loft
        cleanup_sections(doc, sections)
        
        print("✅ Enhanced loft created with surface improvements.")
        
        # Export foil to organized output folder
        try:
            step_path = f"{OUTPUT_FOLDER}/{FOIL_STEP_FILE}"
            Part.export([lf], step_path)
            print(f"✅ Exported enhanced foil STEP: {step_path}")
        except Exception as e:
            print(f"❌ Foil STEP export failed: {e}")
            
    except Exception as e:
        print(f"❌ Enhanced loft failed: {e}")
        print(f"🔄 Trying ruled loft as fallback...")
        try:
            loft = Part.makeLoft(valid_shapes, solid=True, ruled=True)
            
            # Apply smoothing to fallback loft too
            if CONFIG['surface_smoothing']:
                loft = apply_surface_smoothing(loft, CONFIG['smoothing_iterations'])
            
            lf = doc.addObject("Part::Feature", f"{BOAT_NAME}_Foil_Ruled")
            lf.Shape = loft
            lf.ViewObject.ShapeColor = CONFIG['loft_color']
            lf.ViewObject.DisplayMode = "Shaded"
            
            # Clean up construction sections after successful fallback loft
            cleanup_sections(doc, sections)
            
            print("✅ Enhanced ruled loft created as fallback.")
            
            # Export fallback foil
            try:
                step_path = f"{OUTPUT_FOLDER}/{FOIL_STEP_FILE}"
                Part.export([lf], step_path)
                print(f"✅ Exported enhanced ruled foil STEP: {step_path}")
            except Exception as e:
                print(f"❌ Foil STEP export failed: {e}")
                
        except Exception as e2:
            print(f"❌ Enhanced ruled loft also failed: {e2}")
            return

    doc.recompute()
    print(f"🛥️ {BOAT_NAME} enhanced foil geometry complete!")
    print(f"🎯 Surface quality improvements applied:")
    print(f"   - {CONFIG['naca_points']} point sections with cosine clustering")
    print(f"   - {CONFIG['slice_spacing']}mm adaptive slicing")
    print(f"   - B-spline sections: {CONFIG['use_bspline_sections']}")
    print(f"   - Surface smoothing: {CONFIG['surface_smoothing']}")
    print(f"   - Construction sections automatically cleaned up")
    print(f"📁 Next step: Use {step_path} for stock integration")