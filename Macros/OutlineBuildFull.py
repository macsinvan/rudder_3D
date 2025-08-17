# Macros/OutlineBuildFull.py
"""
Comprehensive Rudder Outline Builder - Boat-Centric Version
Processes both Profile and Outline CSV files with explicit geometry.
Creates wire and face objects with shrunk versions for each CSV.
Everything organized by boat name.
No point visualization - clean geometry focus.
"""
import sys, os
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
VERSION = "2.2.19"  # LINE and ARC only - no CURVE support

# Derived paths - everything flows from boat name
BOAT_FOLDER = os.path.expanduser(f"~/Rudder_Code/boats/{BOAT_NAME}")
INPUT_FOLDER = f"{BOAT_FOLDER}/input"
OUTPUT_FOLDER = f"{BOAT_FOLDER}/output/outline"

# File specifications
PROFILE_CSV = f"{BOAT_NAME}_Rudder_Profile.csv"
OUTLINE_CSV = f"{BOAT_NAME}_Rudder_Outline.csv"
PROFILE_STEP = f"{BOAT_NAME}_Profile.step"
OUTLINE_STEP = f"{BOAT_NAME}_Outline.step"

# Parameters
OFFSET_DIST = -5.0  # mm inward offset for shrink
GRID_SPACING = 10   # mm grid spacing
GRID_MARGIN = 50    # mm beyond bounds
MACRO_NAME = f"Rudder_Outline_{BOAT_NAME}"

# Color schemes for visual distinction
PROFILE_COLORS = {
    'fill': (1.0, 0.8, 0.6),      # Light orange
    'wire': (1.0, 0.5, 0.0),      # Orange
    'shrunk': (0.8, 0.2, 0.0)     # Dark orange
}

OUTLINE_COLORS = {
    'fill': (0.6, 0.8, 1.0),      # Light blue  
    'wire': (0.0, 0.5, 1.0),      # Blue
    'shrunk': (0.0, 0.2, 0.8)     # Dark blue
}


def read_explicit_csv(path: str):
    """
    Read CSV with SEGMENT block format:
    SEGMENT,LINE
    x1,y1
    x2,y2
    SEGMENT,ARC
    x1,y1
    x2,y2
    x3,y3
    etc.
    
    Validates segments strictly - fails on any invalid segment.
    """
    segments = []
    current_type = None
    current_points = []
    
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        reading_coordinates = False
        
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
                
            # Look for coordinate section header
            if len(row) >= 2 and row[0].strip().upper() == 'X' and row[1].strip().upper() == 'Y':
                reading_coordinates = True
                continue
                
            if not reading_coordinates:
                continue
                
            # Check if this is a SEGMENT header
            if len(row) >= 2 and row[0].strip().upper() == 'SEGMENT':
                # Save previous segment if we have one
                if current_type and current_points:
                    segments.append((current_type, current_points.copy()))
                
                # Start new segment
                current_type = row[1].strip().lower()
                current_points = []
                continue
            
            # Try to parse as coordinate point
            if len(row) >= 2:
                try:
                    x = float(row[0].strip())
                    y = float(row[1].strip())
                    # Transform: CSV Y becomes FreeCAD -Z (consistent with existing system)
                    current_points.append((x, -y))
                except ValueError:
                    continue
    
    # Don't forget the last segment
    if current_type and current_points:
        segments.append((current_type, current_points.copy()))
    
    # STRICT VALIDATION - No tolerance for bad input (LINES and ARCS only)
    print(f"   📐 Validating {len(segments)} geometry segments...")
    
    for i, (seg_type, points) in enumerate(segments):
        if seg_type == 'line':
            if len(points) < 2:
                error_msg = f"CSV ERROR: LINE segment {i} has {len(points)} points, needs at least 2"
                print(f"   ❌ {error_msg}")
                from PySide2 import QtWidgets
                QtWidgets.QMessageBox.critical(None, "CSV Validation Error", error_msg)
                raise ValueError(error_msg)
                
        elif seg_type == 'arc':
            if len(points) != 3:
                error_msg = f"CSV ERROR: ARC segment {i} has {len(points)} points, needs exactly 3"
                print(f"   ❌ {error_msg}")
                from PySide2 import QtWidgets
                QtWidgets.QMessageBox.critical(None, "CSV Validation Error", error_msg)
                raise ValueError(error_msg)
                
        else:
            error_msg = f"CSV ERROR: Invalid segment type '{seg_type}' in segment {i}.\n"
            error_msg += f"Only LINE and ARC segments are supported.\n"
            error_msg += f"CURVE segments are no longer allowed - use multiple ARCs instead."
            print(f"   ❌ {error_msg}")
            from PySide2 import QtWidgets
            QtWidgets.QMessageBox.critical(None, "CSV Validation Error", error_msg)
            raise ValueError(error_msg)
    
    # CONTINUITY VALIDATION - Check segments connect properly
    print(f"   🔗 Checking segment continuity...")
    tolerance = 0.1  # mm tolerance for point matching
    
    for i in range(len(segments) - 1):
        current_seg_type, current_points = segments[i]
        next_seg_type, next_points = segments[i + 1]
        
        # Get end point of current segment
        current_end = current_points[-1]
        # Get start point of next segment  
        next_start = next_points[0]
        
        # Calculate distance between end and start points
        distance = ((current_end[0] - next_start[0])**2 + (current_end[1] - next_start[1])**2)**0.5
        
        if distance > tolerance:
            error_msg = f"CSV ERROR: Segment {i} ({current_seg_type.upper()}) does not connect to segment {i+1} ({next_seg_type.upper()})\n"
            error_msg += f"  Segment {i} ends at: ({current_end[0]:.3f}, {current_end[1]:.3f})\n"
            error_msg += f"  Segment {i+1} starts at: ({next_start[0]:.3f}, {next_start[1]:.3f})\n"
            error_msg += f"  Gap distance: {distance:.3f}mm (tolerance: {tolerance}mm)"
            print(f"   ❌ {error_msg}")
            from PySide2 import QtWidgets
            QtWidgets.QMessageBox.critical(None, "CSV Continuity Error", error_msg)
            raise ValueError(error_msg)
    
    # Check if outline closes (first point = last point)
    if len(segments) > 0:
        first_point = segments[0][1][0]  # First point of first segment
        last_point = segments[-1][1][-1]  # Last point of last segment
        distance = ((first_point[0] - last_point[0])**2 + (first_point[1] - last_point[1])**2)**0.5
        
        if distance > tolerance:
            error_msg = f"CSV ERROR: Outline does not close properly\n"
            error_msg += f"  First point: ({first_point[0]:.3f}, {first_point[1]:.3f})\n"
            error_msg += f"  Last point: ({last_point[0]:.3f}, {last_point[1]:.3f})\n"
            error_msg += f"  Gap distance: {distance:.3f}mm (tolerance: {tolerance}mm)"
            print(f"   ❌ {error_msg}")
            from PySide2 import QtWidgets
            QtWidgets.QMessageBox.critical(None, "CSV Closure Error", error_msg)
            raise ValueError(error_msg)
    
    print(f"   ✅ All segments validated successfully:")
    for i, (seg_type, points) in enumerate(segments):
        start_pt = points[0] if points else "none"
        end_pt = points[-1] if points else "none"
        print(f"      {i}: {seg_type.upper()} with {len(points)} points: {start_pt} -> {end_pt}")
    
    print(f"   ✅ All segments are continuous and outline closes properly")
    
    return segments


def create_edges_from_segments(segments):
    """
    Create FreeCAD edges from geometry segments.
    Assumes segments are already validated - only LINE and ARC types allowed.
    """
    edges = []
    
    for seg_type, points in segments:
        if seg_type == 'line':
            for i in range(len(points) - 1):
                p1 = Vector(points[i][0], 0, points[i][1])
                p2 = Vector(points[i+1][0], 0, points[i+1][1])
                edges.append(Part.makeLine(p1, p2))
                
        elif seg_type == 'arc':
            # Exactly 3 points guaranteed by validation
            p1 = Vector(points[0][0], 0, points[0][1])
            p2 = Vector(points[1][0], 0, points[1][1])
            p3 = Vector(points[2][0], 0, points[2][1])
            edges.append(Part.Arc(p1, p2, p3).toShape())
    
    print(f"   ✅ Created {len(edges)} edges from {len(segments)} segments (LINE and ARC only)")
    return edges


def process_csv_file(csv_filename, object_prefix, colors, doc):
    """
    Process a single CSV file and create FreeCAD objects.
    Returns (objects_for_export, all_points) or (None, None) if file not found or invalid.
    """
    csv_path = f"{INPUT_FOLDER}/{csv_filename}"
    
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_filename} not found, skipping...")
        return None, None
    
    print(f"🔄 Processing {csv_filename}...")
    
    # Parse CSV with strict validation - will raise exception on bad input
    try:
        segments = read_explicit_csv(csv_path)
    except ValueError as e:
        print(f"   ❌ CSV validation failed: {e}")
        return None, None
    
    if not segments:
        error_msg = f"No valid segments found in {csv_filename}"
        print(f"   ❌ {error_msg}")
        from PySide2 import QtWidgets
        QtWidgets.QMessageBox.critical(None, "CSV Processing Error", error_msg)
        return None, None
    
    # Create edges - no error handling needed since segments are validated
    edges = create_edges_from_segments(segments)
    if not edges:
        error_msg = f"No edges created from {csv_filename}"
        print(f"   ❌ {error_msg}")
        from PySide2 import QtWidgets
        QtWidgets.QMessageBox.critical(None, "Geometry Creation Error", error_msg)
        return None, None
    
    # Build wire
    try:
        wire = Part.Wire(edges)
        print(f"   🔧 Created wire with {len(wire.Edges)} edges, closed: {wire.isClosed()}")
        
        if not wire.isClosed():
            # Try to close the wire
            last_pt = wire.Edges[-1].Vertexes[-1].Point
            first_pt = wire.Edges[0].Vertexes[0].Point
            gap_distance = last_pt.distanceToPoint(first_pt)
            print(f"   📏 Gap distance: {gap_distance:.3f}mm")
            
            if gap_distance > 0.1:  # If not already connected
                closing_edge = Part.makeLine(last_pt, first_pt)
                wire = Part.Wire(edges + [closing_edge])
                print(f"   🔗 Added closing edge, now closed: {wire.isClosed()}")
        
        # Simple validation
        print(f"   ✅ Final wire: {len(wire.Edges)} edges, closed: {wire.isClosed()}, valid: {wire.isValid()}")
        
    except Exception as e:
        error_msg = f"Failed to create wire from {csv_filename}: {e}"
        print(f"   ❌ {error_msg}")
        from PySide2 import QtWidgets
        QtWidgets.QMessageBox.critical(None, "Wire Creation Error", error_msg)
        return None, None

    # Create objects with proper naming
    objects_for_export = []
    
    # Fill object
    try:
        face = Part.Face(wire)
        fill_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Fill")
        fill_obj.Shape = face
        fill_obj.ViewObject.ShapeColor = colors['fill']
        fill_obj.ViewObject.Transparency = 70
    except Exception as e:
        print(f"   ⚠️ Could not create face: {e}")

    # Wire object
    wire_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Wire")
    wire_obj.Shape = wire
    wire_obj.ViewObject.ShapeColor = colors['wire']
    wire_obj.ViewObject.LineWidth = 3
    objects_for_export.append(wire_obj)

    # Shrunk wire
    try:
        print(f"   🔧 Creating shrunk wire with {OFFSET_DIST}mm offset...")
        
        # Try different makeOffset2D parameters for better curve handling
        try:
            # Method 1: High precision offset with join type specified
            print(f"   🎯 Attempting high-precision offset...")
            shrunk_wire_raw = wire.makeOffset2D(OFFSET_DIST, 0.01, True, True, False)  # offset, tol, fill, openResult, intersection
            print(f"   ✅ High-precision offset successful")
        except:
            try:
                # Method 2: Standard precision with different parameters
                print(f"   🎯 Attempting standard offset with join settings...")
                shrunk_wire_raw = wire.makeOffset2D(OFFSET_DIST, 0.1, True, True)  # offset, tolerance, fill, openResult
                print(f"   ✅ Standard offset successful")
            except:
                try:
                    # Method 3: Simple offset (original method)
                    print(f"   🎯 Falling back to simple offset...")
                    shrunk_wire_raw = wire.makeOffset2D(OFFSET_DIST)
                    print(f"   ✅ Simple offset successful")
                except Exception as e:
                    print(f"   ❌ All offset methods failed: {e}")
                    return None, None
        
        # DEBUG: Create a visual object for the raw shrunk wire to inspect shape
        print(f"   🔍 Creating debug object for raw shrunk wire inspection...")
        debug_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Shrunk_RAW_DEBUG")
        debug_obj.Shape = shrunk_wire_raw
        debug_obj.ViewObject.ShapeColor = (1.0, 0.0, 1.0)  # Magenta for easy identification
        debug_obj.ViewObject.LineWidth = 3
        print(f"   🔍 DEBUG: Look for magenta '{debug_obj.Name}' object to inspect raw offset shape")
        
        # Use raw shrunk wire directly (no simplification for now)
        print(f"   🚧 USING RAW SHRUNK WIRE (no simplification)")
        shrunk_wire = shrunk_wire_raw
        
        # Final validation
        print(f"   📊 Final shrunk wire: {len(shrunk_wire.Edges)} edges, closed: {shrunk_wire.isClosed()}")
        
        # Check edge count consistency
        if len(shrunk_wire.Edges) != len(wire.Edges):
            print(f"   📊 Edge count comparison:")
            print(f"      Original: {len(wire.Edges)} edges")
            print(f"      Shrunk: {len(shrunk_wire.Edges)} edges")
            print(f"      Difference: {len(shrunk_wire.Edges) - len(wire.Edges)} edges")
        
        # Check closure consistency
        if wire.isClosed() and not shrunk_wire.isClosed():
            warning_msg = f"SHRUNK WIRE WARNING: Closure mismatch!\n"
            warning_msg += f"  Original wire: CLOSED\n"
            warning_msg += f"  Shrunk wire: OPEN\n"
            warning_msg += f"  This will cause foil generation problems!"
            print(f"   ⚠️ {warning_msg}")
            
        # Check bounding box consistency
        orig_bb = wire.BoundBox
        shrunk_bb = shrunk_wire.BoundBox
        orig_diagonal = orig_bb.DiagonalLength
        shrunk_diagonal = shrunk_bb.DiagonalLength
        
        print(f"   📏 Bounding box comparison:")
        print(f"      Original: {orig_diagonal:.1f}mm diagonal")
        print(f"      Shrunk: {shrunk_diagonal:.1f}mm diagonal")
        
        # Shrunk should be smaller but not dramatically different
        size_ratio = shrunk_diagonal / orig_diagonal if orig_diagonal > 0 else 0
        if size_ratio < 0.5 or size_ratio > 1.0:
            warning_msg = f"SHRUNK WIRE WARNING: Suspicious size change!\n"
            warning_msg += f"  Size ratio: {size_ratio:.2f} (expected: 0.7-0.95)\n"
            warning_msg += f"  Shrunk wire may be malformed"
            print(f"   ⚠️ {warning_msg}")
            
        # Check if shrunk wire is valid
        if not shrunk_wire.isValid():
            error_msg = f"SHRUNK WIRE ERROR: Invalid geometry created by offset operation!"
            print(f"   ❌ {error_msg}")
            from PySide2 import QtWidgets
            QtWidgets.QMessageBox.warning(None, "Shrunk Wire Warning", error_msg)
        
        # Create shrunk wire object (the normal one for export)
        shrunk_obj = doc.addObject("Part::Feature", f"{BOAT_NAME}_{object_prefix}_Shrunk")
        shrunk_obj.Shape = shrunk_wire
        shrunk_obj.ViewObject.ShapeColor = colors['shrunk']
        shrunk_obj.ViewObject.LineWidth = 2
        objects_for_export.append(shrunk_obj)
        
        print(f"   ✅ Shrunk wire created with enhanced offset parameters")
        print(f"   🔍 INSPECT: Compare magenta debug object vs normal shrunk object")
        
    except Exception as e:
        error_msg = f"SHRUNK WIRE ERROR: Offset operation failed: {e}"
        print(f"   ❌ {error_msg}")
        from PySide2 import QtWidgets
        QtWidgets.QMessageBox.warning(None, "Shrunk Wire Error", error_msg)

    # Get all points for grid calculation
    all_points = []
    for seg_type, points in segments:
        all_points.extend(points)

    print(f"   ✅ Created {object_prefix} objects with {len(segments)} segments")
    return objects_for_export, all_points


def ensure_output_folder():
    """Ensure output folder exists for this boat"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def run():
    print(f"\n🚤 Rudder Outline Builder v{VERSION}")
    print(f"🚤 Boat: {BOAT_NAME}")
    print(f"📂 Boat folder: {BOAT_FOLDER}")
    print(f"📐 Mode: Dual CSV processing (Profile + Outline)")
    
    # Ensure output folder exists
    ensure_output_folder()
    
    # New document
    if MACRO_NAME in App.listDocuments():
        App.closeDocument(MACRO_NAME)
    doc = App.newDocument(MACRO_NAME)
    Gui.activateWorkbench("PartWorkbench")

    # Process Profile CSV
    print(f"\n📋 PROFILE PROCESSING:")
    profile_objects, profile_points = process_csv_file(PROFILE_CSV, "Profile", PROFILE_COLORS, doc)
    
    # Process Outline CSV
    print(f"\n📋 OUTLINE PROCESSING:")
    outline_objects, outline_points = process_csv_file(OUTLINE_CSV, "Outline", OUTLINE_COLORS, doc)
    
    # Check if we got any valid results
    if not profile_objects and not outline_objects:
        print("❌ No valid CSV files found. Aborting.")
        return
    
    # Export Profile objects
    if profile_objects:
        profile_step_path = f"{OUTPUT_FOLDER}/{PROFILE_STEP}"
        try:
            print(f"   🔧 Exporting {len(profile_objects)} profile objects...")
            
            # Pre-export validation - log what we're sending
            for i, obj in enumerate(profile_objects):
                edge_count = len(obj.Shape.Edges) if hasattr(obj.Shape, 'Edges') else 0
                print(f"      Object {i}: {obj.Name} - Valid: {obj.Shape.isValid()}, Edges: {edge_count}")
            
            Part.export(profile_objects, profile_step_path)
            print(f"✅ Exported Profile STEP: {profile_step_path}")
            
            # Post-export validation - verify file integrity
            import os
            file_size = os.path.getsize(profile_step_path)
            print(f"   📏 File size: {file_size} bytes")
            
            # Test import to verify data integrity
            try:
                test_compound = Part.read(profile_step_path)
                test_subs = getattr(test_compound, 'SubShapes', [test_compound])
                print(f"   🔍 STEP Export Validation:")
                print(f"      File contains {len(test_subs)} objects")
                
                for i, sub in enumerate(test_subs):
                    edge_count = len(sub.Edges) if hasattr(sub, 'Edges') else 0
                    print(f"      Object {i}: {edge_count} edges")
                    
                    # Compare with original
                    if i < len(profile_objects):
                        orig_edges = len(profile_objects[i].Shape.Edges)
                        if edge_count != orig_edges:
                            warning_msg = f"EXPORT WARNING: Edge count changed during STEP export!\n"
                            warning_msg += f"  Object {i} ({profile_objects[i].Name}):\n"
                            warning_msg += f"  Original: {orig_edges} edges\n"
                            warning_msg += f"  Exported: {edge_count} edges\n"
                            warning_msg += f"  Lost: {orig_edges - edge_count} edges"
                            print(f"   ⚠️ {warning_msg}")
                            
            except Exception as e:
                error_msg = f"EXPORT VALIDATION ERROR: Cannot re-read exported STEP file: {e}"
                print(f"   ❌ {error_msg}")
                
        except Exception as e:
            print(f"❌ Profile STEP export failed: {e}")
    
    # Export Outline objects  
    if outline_objects:
        outline_step_path = f"{OUTPUT_FOLDER}/{OUTLINE_STEP}"
        try:
            print(f"   🔧 Exporting {len(outline_objects)} outline objects...")
            
            # Pre-export validation - log what we're sending
            for i, obj in enumerate(outline_objects):
                edge_count = len(obj.Shape.Edges) if hasattr(obj.Shape, 'Edges') else 0
                print(f"      Object {i}: {obj.Name} - Valid: {obj.Shape.isValid()}, Edges: {edge_count}")
            
            Part.export(outline_objects, outline_step_path)
            print(f"✅ Exported Outline STEP: {outline_step_path}")
            
            # Post-export validation - verify file integrity
            import os
            file_size = os.path.getsize(outline_step_path)
            print(f"   📏 File size: {file_size} bytes")
            
            # Test import to verify data integrity
            try:
                test_compound = Part.read(outline_step_path)
                test_subs = getattr(test_compound, 'SubShapes', [test_compound])
                print(f"   🔍 STEP Export Validation:")
                print(f"      File contains {len(test_subs)} objects")
                
                for i, sub in enumerate(test_subs):
                    edge_count = len(sub.Edges) if hasattr(sub, 'Edges') else 0
                    print(f"      Object {i}: {edge_count} edges")
                    
                    # Compare with original
                    if i < len(outline_objects):
                        orig_edges = len(outline_objects[i].Shape.Edges)
                        if edge_count != orig_edges:
                            warning_msg = f"EXPORT WARNING: Edge count changed during STEP export!\n"
                            warning_msg += f"  Object {i} ({outline_objects[i].Name}):\n"
                            warning_msg += f"  Original: {orig_edges} edges\n"
                            warning_msg += f"  Exported: {edge_count} edges\n"
                            warning_msg += f"  Lost: {orig_edges - edge_count} edges"
                            print(f"   ⚠️ {warning_msg}")
                            from PySide2 import QtWidgets
                            QtWidgets.QMessageBox.warning(None, "STEP Export Warning", warning_msg)
                            
            except Exception as e:
                error_msg = f"EXPORT VALIDATION ERROR: Cannot re-read exported STEP file: {e}"
                print(f"   ❌ {error_msg}")
                
        except Exception as e:
            print(f"❌ Outline STEP export failed: {e}")

    # Draw grid (use outline points if available, otherwise profile points)
    grid_points = outline_points if outline_points else profile_points
    if grid_points:
        print(f"\n🔧 Drawing grid based on {len(grid_points)} points...")
        xs = [p[0] for p in grid_points]
        zs = [p[1] for p in grid_points]
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
    print(f"\n🚤 {BOAT_NAME} dual outline building complete!")
    profile_status = "✅ Profile processed" if profile_objects else "⚠️ Profile skipped"
    outline_status = "✅ Outline processed" if outline_objects else "⚠️ Outline skipped"
    print(f"📐 Results: {profile_status}, {outline_status}")
    print(f"📁 STEP files exported to: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    run()