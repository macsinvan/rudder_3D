# Macros/Build_New_Profile.py
"""
Parametric Rudder Profile Generator - Boat-Centric Version
Generates standard rudder outlines from parametric specifications.
Creates wire and face objects equivalent to CSV-based workflow.
Everything organized by boat name.
"""
import sys, os
import math
from PySide2 import QtWidgets

# Add project root so Python finds our modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
import csv

# Configuration - Boat-Centric
BOAT_NAME = "MackenSea"  # Single source of truth - change this for different boats
VERSION = "1.0.0"  # Initial parametric generator version

# Derived paths - everything flows from boat name
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/input"
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/01_outline"

# File specifications
NEW_SPEC_CSV = f"New_{BOAT_NAME}_Rudder.csv"
NEW_PROFILE_STEP = f"New_{BOAT_NAME}_Outline.step"

# Parameters
OFFSET_DIST = -5.0  # mm inward offset for shrink
GRID_SPACING = 10   # mm grid spacing
GRID_MARGIN = 50    # mm beyond bounds
MACRO_NAME = f"New_Rudder_Profile_{BOAT_NAME}"

# Color scheme for generated profile (green tones to distinguish from existing)
NEW_PROFILE_COLORS = {
    'fill': (0.6, 1.0, 0.6),      # Light green
    'wire': (0.0, 0.8, 0.0),      # Green
    'shrunk': (0.0, 0.5, 0.0)     # Dark green
}


class RudderSpec:
    """Container for rudder specification parameters"""
    def __init__(self):
        # Defaults based on MackenSea
        self.boat_name = "MackenSea"
        self.rudder_type = "spade_balanced"
        
        # Overall dimensions
        self.rudder_span = 800
        self.root_chord = 240
        self.tip_chord = 160
        self.taper_ratio = 0.67
        
        # Position and balance
        self.balance_ratio = 0.20
        self.stock_position_percent = 20.0
        self.stock_diameter = 44
        
        # Planform shape
        self.shape_type = "tapered_elliptical"
        self.leading_edge_type = "curved"
        self.trailing_edge_type = "straight"
        self.aspect_ratio = 3.33
        
        # Leading edge
        self.le_root_radius = 25
        self.le_tip_radius = 12
        self.le_sweep_angle = 8
        
        # Trailing edge
        self.te_thickness = 2
        self.te_sweep_angle = 4
        self.te_cutoff_height = 20
        
        # Hull integration
        self.top_cutout_type = "custom"
        self.top_cutout_depth = 45
        self.top_cutout_width = 120
        self.top_cutout_curve_radius = 60


def read_rudder_spec(csv_path):
    """Read parametric rudder specification from CSV"""
    spec = RudderSpec()
    
    if not os.path.exists(csv_path):
        print(f"⚠️ Spec file not found: {csv_path}")
        print("   Using default MackenSea parameters")
        return spec
    
    print(f"📋 Reading rudder specification: {csv_path}")
    
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            
            if len(row) >= 2:
                param = row[0].strip().upper()
                value = row[1].strip()
                
                try:
                    # Parse numeric parameters
                    if param == 'RUDDER_SPAN':
                        spec.rudder_span = float(value)
                    elif param == 'ROOT_CHORD':
                        spec.root_chord = float(value)
                    elif param == 'TIP_CHORD':
                        spec.tip_chord = float(value)
                    elif param == 'BALANCE_RATIO':
                        spec.balance_ratio = float(value)
                    elif param == 'STOCK_POSITION_PERCENT':
                        spec.stock_position_percent = float(value)
                    elif param == 'STOCK_DIAMETER':
                        spec.stock_diameter = float(value)
                    elif param == 'LE_ROOT_RADIUS':
                        spec.le_root_radius = float(value)
                    elif param == 'LE_TIP_RADIUS':
                        spec.le_tip_radius = float(value)
                    elif param == 'LE_SWEEP_ANGLE':
                        spec.le_sweep_angle = float(value)
                    elif param == 'TE_THICKNESS':
                        spec.te_thickness = float(value)
                    elif param == 'TE_SWEEP_ANGLE':
                        spec.te_sweep_angle = float(value)
                    elif param == 'TOP_CUTOUT_DEPTH':
                        spec.top_cutout_depth = float(value)
                    elif param == 'TOP_CUTOUT_WIDTH':
                        spec.top_cutout_width = float(value)
                    elif param == 'TOP_CUTOUT_CURVE_RADIUS':
                        spec.top_cutout_curve_radius = float(value)
                    # String parameters
                    elif param == 'BOAT_NAME':
                        spec.boat_name = value
                    elif param == 'SHAPE_TYPE':
                        spec.shape_type = value
                    elif param == 'LEADING_EDGE_TYPE':
                        spec.leading_edge_type = value
                    elif param == 'TRAILING_EDGE_TYPE':
                        spec.trailing_edge_type = value
                        
                except ValueError:
                    print(f"   ⚠️ Could not parse {param}: {value}")
    
    print(f"   ✅ Loaded spec for {spec.boat_name}")
    print(f"   📐 Dimensions: {spec.root_chord}mm x {spec.rudder_span}mm (root x span)")
    print(f"   ⚖️ Balance: {spec.balance_ratio*100:.1f}% forward of stock")
    
    return spec


def generate_rudder_outline(spec):
    """Generate rudder outline geometry from specification"""
    print(f"🔧 Generating SIMPLE tapered rudder outline...")
    
    # Baby steps: Create simple 4-point trapezoid first
    points = []
    
    # Start at top-left (leading edge root) and go clockwise
    # 1. Top-left: Leading edge at root
    points.append((0, 0))
    
    # 2. Bottom-left: Leading edge at tip  
    points.append((0, -spec.rudder_span))
    
    # 3. Bottom-right: Trailing edge at tip
    points.append((spec.tip_chord, -spec.rudder_span))
    
    # 4. Top-right: Trailing edge at root
    points.append((spec.root_chord, 0))
    
    # That's it - simple trapezoid!
    
    print(f"   📐 Generated {len(points)} outline points (simple trapezoid):")
    for i, (x, z) in enumerate(points):
        print(f"      {i}: ({x:.1f}, {z:.1f})")
    
    return points


def create_rudder_geometry(points, spec, doc):
    """Create FreeCAD geometry from rudder outline points"""
    print(f"   🔧 Creating geometry from {len(points)} points...")
    
    # Remove duplicate points that are too close together
    cleaned_points = []
    tolerance = 0.1  # mm
    
    for i, point in enumerate(points):
        if i == 0:
            cleaned_points.append(point)
        else:
            prev_point = cleaned_points[-1]
            distance = math.sqrt((point[0] - prev_point[0])**2 + (point[1] - prev_point[1])**2)
            if distance > tolerance:
                cleaned_points.append(point)
            else:
                print(f"   🧹 Removed duplicate point {i}: {point} (too close to {prev_point})")
    
    print(f"   ✅ Cleaned to {len(cleaned_points)} unique points")
    
    # Convert points to vectors
    vectors = [Vector(p[0], 0, p[1]) for p in cleaned_points]
    
    # Create edges - all as lines for simplicity
    edges = []
    
    for i in range(len(vectors)):
        next_idx = (i + 1) % len(vectors)
        
        # Double-check distance before creating edge
        distance = vectors[i].distanceToPoint(vectors[next_idx])
        if distance > tolerance:
            try:
                edge = Part.makeLine(vectors[i], vectors[next_idx])
                edges.append(edge)
            except Exception as e:
                print(f"   ⚠️ Failed to create edge {i}->{next_idx}: {e}")
        else:
            print(f"   ⚠️ Skipping edge {i}->{next_idx}: points too close ({distance:.3f}mm)")
    
    if not edges:
        print("   ❌ No valid edges created")
        return None, cleaned_points
    
    print(f"   ✅ Created {len(edges)} edges")
    
    # Create wire
    try:
        wire = Part.Wire(edges)
        print(f"   ✅ Wire created, closed: {wire.isClosed()}")
        
        if not wire.isClosed():
            print("   🔗 Wire not closed, attempting to close...")
            # Try to close manually
            last_pt = wire.Edges[-1].Vertexes[-1].Point
            first_pt = wire.Edges[0].Vertexes[0].Point
            distance = last_pt.distanceToPoint(first_pt)
            print(f"   📏 Gap distance: {distance:.3f}mm")
            
            if distance > tolerance:
                try:
                    closing_edge = Part.makeLine(last_pt, first_pt)
                    wire = Part.Wire(edges + [closing_edge])
                    print(f"   ✅ Added closing edge, now closed: {wire.isClosed()}")
                except Exception as e:
                    print(f"   ⚠️ Failed to add closing edge: {e}")
    except Exception as e:
        print(f"   ❌ Failed to create wire: {e}")
        return None, cleaned_points
    
    # Create objects (same structure as CSV workflow)
    objects_for_export = []
    
    # Fill object
    try:
        face = Part.Face(wire)
        fill_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_NewProfile_Fill")
        fill_obj.Shape = face
        fill_obj.ViewObject.ShapeColor = NEW_PROFILE_COLORS['fill']
        fill_obj.ViewObject.Transparency = 70
        print("   ✅ Created fill face")
    except Exception as e:
        print(f"   ⚠️ Could not create face: {e}")
    
    # Wire object
    wire_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_NewProfile_Wire")
    wire_obj.Shape = wire
    wire_obj.ViewObject.ShapeColor = NEW_PROFILE_COLORS['wire']
    wire_obj.ViewObject.LineWidth = 3
    objects_for_export.append(wire_obj)
    print("   ✅ Created wire object")
    
    # Shrunk wire
    try:
        shrunk_wire = wire.makeOffset2D(OFFSET_DIST)
        shrunk_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_NewProfile_Shrunk")
        shrunk_obj.Shape = shrunk_wire
        shrunk_obj.ViewObject.ShapeColor = NEW_PROFILE_COLORS['shrunk']
        shrunk_obj.ViewObject.LineWidth = 2
        objects_for_export.append(shrunk_obj)
        print("   ✅ Created shrunk wire")
    except Exception as e:
        print(f"   ⚠️ Could not create shrunk wire: {e}")
    
    print(f"   ✅ Created NewProfile objects successfully")
    return objects_for_export, cleaned_points


def ensure_output_folder():
    """Ensure output folder exists for this boat"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def run():
    print(f"\n🚤 Parametric Rudder Profile Generator v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📂 Boat folder: {BOAT_FOLDER}")
    print(f"📐 Mode: Parametric generation from specification")
    
    # Ensure output folder exists
    ensure_output_folder()
    
    # Read specification
    spec_path = f"{INPUT_FOLDER}/{NEW_SPEC_CSV}"
    spec = read_rudder_spec(spec_path)
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")
    
    # Generate rudder outline
    print(f"\n📋 PARAMETRIC GENERATION:")
    outline_points = generate_rudder_outline(spec)
    
    if not outline_points:
        print("❌ Failed to generate rudder outline. Aborting.")
        return
    
    # Create geometry
    new_objects, points = create_rudder_geometry(outline_points, spec, doc)
    
    if not new_objects:
        print("❌ Failed to create geometry. Aborting.")
        return
    
    # Export objects
    new_step_path = f"{OUTPUT_FOLDER}/{NEW_PROFILE_STEP}"
    try:
        Part.export(new_objects, new_step_path)
        print(f"✅ Exported New Profile STEP: {new_step_path}")
    except Exception as e:
        print(f"❌ New Profile STEP export failed: {e}")
    
    # Draw grid
    if points:
        print(f"\n🔧 Drawing grid based on {len(points)} generated points...")
        xs = [p[0] for p in points]
        zs = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)
        start_x, end_x = 0, int(max_x) + GRID_MARGIN
        start_z, end_z = 0, int(min_z) - GRID_MARGIN
        
        # Vertical lines
        for x in range(start_x, end_x + 1, GRID_SPACING):
            p1 = Vector(x, 0, start_z)
            p2 = Vector(x, 0, end_z)
            line = Part.makeLine(p1, p2)
            obj = doc.addObject("Part::Feature", f"Grid_V_{x}")
            obj.Shape = line
            color = (0.4,0.4,0.4) if x % (GRID_SPACING*10)==0 else (0.8,0.8,0.8)
            width = 2 if x % (GRID_SPACING*10)==0 else 1
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineWidth = width
        
        # Horizontal lines
        for z in range(start_z, end_z - 1, -GRID_SPACING):
            p1 = Vector(start_x, 0, z)
            p2 = Vector(end_x, 0, z)
            line = Part.makeLine(p1, p2)
            obj = doc.addObject("Part::Feature", f"Grid_H_{z}")
            obj.Shape = line
            color = (0.4,0.4,0.4) if z % (GRID_SPACING*10)==0 else (0.8,0.8,0.8)
            width = 2 if z % (GRID_SPACING*10)==0 else 1
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineWidth = width
    
    # Finalize view
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.activeDocument().activeView().viewFront()
    
    # Summary
    print(f"\n🚤 {BOAT_NAME} parametric rudder generation complete!")
    print(f"📐 Generated: {spec.root_chord}mm x {spec.rudder_span}mm rudder")
    print(f"📁 STEP file exported to: {OUTPUT_FOLDER}")
    print(f"🎨 Green color scheme distinguishes from existing CSV-based profiles")


if __name__ == "__main__":
    run()