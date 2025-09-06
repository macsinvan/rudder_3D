# Multiboard_Geometry_Analyzer.py
# FreeCAD Macro to import and analyze Multiboard .3mf file
# Extracts dimensions and geometry patterns

import FreeCAD
import Mesh
import Part
import numpy as np
from pathlib import Path
import os

def analyze_multiboard_3mf():
    """Import and analyze Multiboard .3mf file to extract dimensions"""
    
    # Get path to Downloads folder and the specific file
    home = str(Path.home())
    file_path = os.path.join("~", home, "Downloads", "Multiboard Demo Pack - 6x6 Tile.3mf")
    
    print("="*70)
    print("MULTIBOARD GEOMETRY ANALYZER")
    print("="*70)
    print(f"Looking for file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"ERROR: File not found at {file_path}")
        print("Please ensure file is at: Downloads/Multiboard Demo Pack  FREE/")
        print("Looking for: 'Multiboard Demo Pack - 6x6 Tile.3mf'")
        
        # Try to list what's in the folder to help debug
        folder_path = os.path.join(home, "Downloads", "Multiboard Demo Pack  FREE")
        if os.path.exists(folder_path):
            print(f"\nFiles found in {folder_path}:")
            try:
                files = os.listdir(folder_path)
                for f in files[:10]:  # Show first 10 files
                    print(f"  - {f}")
                if len(files) > 10:
                    print(f"  ... and {len(files) - 10} more files")
            except Exception as e:
                print(f"Could not list files: {e}")
        return
    
    print("File found! Importing...")
    
    # Import the .3mf file
    try:
        Mesh.insert(file_path)
        print("Import successful!")
    except Exception as e:
        print(f"ERROR importing file: {e}")
        return
    
    # Get the imported mesh object
    doc = FreeCAD.ActiveDocument
    if not doc:
        doc = FreeCAD.newDocument("MultiboardAnalysis")
    
    # Find the mesh object (usually the last imported object)
    mesh_obj = None
    for obj in doc.Objects:
        if hasattr(obj, 'Mesh'):
            mesh_obj = obj
            break
    
    if not mesh_obj:
        print("ERROR: No mesh object found after import")
        return
    
    mesh = mesh_obj.Mesh
    print(f"\nMesh imported: {mesh.CountPoints} vertices, {mesh.CountFacets} faces")
    
    # Analyze overall dimensions
    print("\n" + "="*50)
    print("OVERALL DIMENSIONS:")
    print("="*50)
    
    bbox = mesh.BoundBox
    width = bbox.XMax - bbox.XMin
    height = bbox.YMax - bbox.YMin
    thickness = bbox.ZMax - bbox.ZMin
    
    print(f"Width (X):     {width:.3f} mm")
    print(f"Height (Y):    {height:.3f} mm")
    print(f"Thickness (Z): {thickness:.3f} mm")
    print(f"Bounding box: ({bbox.XMin:.2f}, {bbox.YMin:.2f}, {bbox.ZMin:.2f}) to ({bbox.XMax:.2f}, {bbox.YMax:.2f}, {bbox.ZMax:.2f})")
    
    # Analyze Z-levels to find recesses and features
    print("\n" + "="*50)
    print("Z-LEVEL ANALYSIS (Detecting recesses/features):")
    print("="*50)
    
    # Get all unique Z coordinates
    points = mesh.Points
    z_coords = [p.z for p in points]
    unique_z = sorted(list(set(round(z, 3) for z in z_coords)))
    
    print(f"Found {len(unique_z)} unique Z-levels:")
    for i, z in enumerate(unique_z[:10]):  # Show first 10
        count = sum(1 for p in points if abs(p.z - z) < 0.01)
        print(f"  Level {i}: Z = {z:.3f} mm ({count} vertices)")
    
    if len(unique_z) > 10:
        print(f"  ... and {len(unique_z) - 10} more levels")
    
    # Calculate recess depths
    if len(unique_z) >= 2:
        top_z = unique_z[-1]
        print(f"\nTop surface at Z = {top_z:.3f} mm")
        print("Potential recess depths from top:")
        for z in reversed(unique_z[:-1]):
            depth = top_z - z
            if depth < thickness/2:  # Only show reasonable recess depths
                print(f"  Depth: {depth:.3f} mm (at Z = {z:.3f})")
    
    # Analyze X-Y patterns to detect hole spacing
    print("\n" + "="*50)
    print("X-Y PATTERN ANALYSIS (Detecting spacing):")
    print("="*50)
    
    # Look for vertices at specific Z level (e.g., top surface)
    if len(unique_z) > 0:
        # Analyze points at top surface
        top_z = unique_z[-1]
        tolerance = 0.1
        top_points = [(p.x, p.y) for p in points if abs(p.z - top_z) < tolerance]
        
        if top_points:
            x_coords = sorted(list(set(round(x, 2) for x, y in top_points)))
            y_coords = sorted(list(set(round(y, 2) for x, y in top_points)))
            
            # Calculate spacings in X direction
            if len(x_coords) > 1:
                x_spacings = [x_coords[i+1] - x_coords[i] for i in range(len(x_coords)-1)]
                x_spacings_filtered = [s for s in x_spacings if s > 0.5]  # Filter out tiny gaps
                
                if x_spacings_filtered:
                    print(f"\nX-coordinates: {len(x_coords)} unique positions")
                    print(f"X range: {min(x_coords):.2f} to {max(x_coords):.2f} mm")
                    
                    # Find common spacings
                    from collections import Counter
                    spacing_counts = Counter(round(s, 1) for s in x_spacings_filtered)
                    common_spacings = spacing_counts.most_common(5)
                    print("Common X-spacings:")
                    for spacing, count in common_spacings:
                        print(f"  {spacing:.1f} mm (appears {count} times)")
            
            # Calculate spacings in Y direction
            if len(y_coords) > 1:
                y_spacings = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords)-1)]
                y_spacings_filtered = [s for s in y_spacings if s > 0.5]  # Filter out tiny gaps
                
                if y_spacings_filtered:
                    print(f"\nY-coordinates: {len(y_coords)} unique positions")
                    print(f"Y range: {min(y_coords):.2f} to {max(y_coords):.2f} mm")
                    
                    # Find common spacings
                    spacing_counts = Counter(round(s, 1) for s in y_spacings_filtered)
                    common_spacings = spacing_counts.most_common(5)
                    print("Common Y-spacings:")
                    for spacing, count in common_spacings:
                        print(f"  {spacing:.1f} mm (appears {count} times)")
    
    # Try to detect octagonal patterns
    print("\n" + "="*50)
    print("OCTAGON DETECTION (8-vertex patterns):")
    print("="*50)
    
    # Look for groups of 8 vertices at same Z level that might form octagons
    if len(unique_z) > 1:
        # Check a recess level (not top or bottom)
        for z_level in unique_z[1:-1]:
            level_points = [(p.x, p.y) for p in points if abs(p.z - z_level) < 0.01]
            
            if len(level_points) >= 8:
                # Try to find octagonal patterns by clustering nearby points
                # This is simplified - actual implementation would need clustering algorithm
                print(f"At Z = {z_level:.3f}: {len(level_points)} vertices (potential octagons)")
                
                # Estimate octagon size by finding nearby points
                if len(level_points) > 0:
                    test_point = level_points[0]
                    distances = []
                    for other in level_points[1:min(20, len(level_points))]:
                        dist = ((other[0] - test_point[0])**2 + (other[1] - test_point[1])**2)**0.5
                        if 2 < dist < 20:  # Reasonable range for octagon vertices
                            distances.append(dist)
                    
                    if distances:
                        avg_dist = sum(distances) / len(distances)
                        # For regular octagon, flat-to-flat ≈ vertex-to-vertex * 0.924
                        estimated_flat = avg_dist * 0.924
                        print(f"  Estimated octagon flat-to-flat: ~{estimated_flat:.1f} mm")
                
                break  # Just analyze one level for now
    
    # Look for holes (circular patterns)
    print("\n" + "="*50)
    print("HOLE ANALYSIS:")
    print("="*50)
    
    # Simple approach: look for circular vertex patterns at bottom Z
    if len(unique_z) > 0:
        bottom_z = unique_z[0]
        bottom_points = [(p.x, p.y) for p in points if abs(p.z - bottom_z) < 0.1]
        
        # Find clusters of points (potential hole centers)
        # This is simplified - you'd need proper clustering for accurate results
        print(f"Bottom surface has {len(bottom_points)} vertices")
        print("(Actual hole detection requires more sophisticated clustering)")
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nSUGGESTED PARAMETERS FOR MULTIBOARD:")
    print(f"- Tile dimensions: {width:.1f} x {height:.1f} x {thickness:.1f} mm")
    
    # Guess at parameters based on typical Multiboard patterns
    if abs(width - 150) < 5 and abs(height - 150) < 5:
        print("- This appears to be a 6x6 MU tile (150mm x 150mm)")
        print("- Grid unit: 25mm (standard Multiboard)")
        print("- Half-grid: 12.5mm (for hole spacing)")
    
    print("\nNOTE: For more accurate measurements, analyze the")
    print("actual STL/STEP files or measure critical features manually")
    
    return {
        'width': width,
        'height': height,
        'thickness': thickness,
        'bbox': bbox,
        'unique_z': unique_z,
        'vertex_count': mesh.CountPoints,
        'face_count': mesh.CountFacets
    }

# Run the analysis
if __name__ == "__main__":
    results = analyze_multiboard_3mf()
    
    if results:
        print("\n" + "="*50)
        print("Results saved to 'results' variable")
        print("You can access: results['width'], results['height'], etc.")