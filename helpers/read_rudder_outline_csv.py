"""
Read Rudder Outline CSV Helper
Reads CSV files with LINE and ARC segments for rudder profile and outline.
"""
import csv


def read_csv(path):
    """Read CSV with SEGMENT blocks. Returns list of (type, points).
    
    Args:
        path: Path to CSV file
        
    Returns:
        List of tuples (segment_type, points)
        where segment_type is 'line' or 'arc'
        and points is a list of (x, y) coordinates
        
    Raises:
        ValueError: If segments have invalid point counts
    """
    segments = []
    current_type = None
    current_points = []
    
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        reading = False
        
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            
            # Look for coordinate section
            if len(row) >= 2 and row[0].strip().upper() == 'X' and row[1].strip().upper() == 'Y':
                reading = True
                continue
            
            if not reading:
                continue
            
            # Check for SEGMENT header
            if len(row) >= 2 and row[0].strip().upper() == 'SEGMENT':
                # Save previous segment
                if current_type and current_points:
                    segments.append((current_type, current_points.copy()))
                
                # Start new segment
                current_type = row[1].strip().lower()
                current_points = []
                continue
            
            # Parse coordinate
            if len(row) >= 2:
                try:
                    x = float(row[0].strip())
                    y = float(row[1].strip())
                    # Transform: CSV Y becomes FreeCAD -Z
                    current_points.append((x, -y))
                except ValueError:
                    continue
    
    # Don't forget last segment
    if current_type and current_points:
        segments.append((current_type, current_points.copy()))
    
    # Quick validation
    for i, (seg_type, points) in enumerate(segments):
        if seg_type == 'line' and len(points) < 2:
            raise ValueError(f"LINE segment {i} needs at least 2 points")
        elif seg_type == 'arc' and len(points) != 3:
            raise ValueError(f"ARC segment {i} needs exactly 3 points")
        elif seg_type not in ['line', 'arc']:
            raise ValueError(f"Unsupported segment type: {seg_type}")
    
    return segments