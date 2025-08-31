"""
wedge_cutout_calc.py
Creates modified dimensions for wedge-style cutouts with tolerance
"""

def create_wedge_cutout_dimensions(dimensions, cutout_tolerance_mm):
    """
    Modify dimensions for wedge-style cutout with tolerance
    
    Args:
        dimensions: Original dimensions dictionary
        cutout_tolerance_mm: Tolerance to add (in mm)
    
    Returns:
        Modified dimensions dictionary for cutout
    """
    import copy
    
    # Deep copy to avoid modifying original
    cutout_dimensions = copy.deepcopy(dimensions)
    
    # Apply tolerance to posts (cylinders and tapers)
    for post in cutout_dimensions.get('posts', []):
        if 'diameter' in post:
            post['diameter'] += 2 * cutout_tolerance_mm
        if 'diameter_start' in post:
            post['diameter_start'] += 2 * cutout_tolerance_mm
        if 'diameter_end' in post:
            post['diameter_end'] += 2 * cutout_tolerance_mm
    
    # Apply tolerance to tines (wedges and plates)
    for tine in cutout_dimensions.get('tines', []):
        if 'width' in tine:
            tine['width'] += cutout_tolerance_mm
        if 'length' in tine:
            tine['length'] += cutout_tolerance_mm
        if 'plate_thickness' in tine:
            tine['plate_thickness'] += cutout_tolerance_mm
        
        # Add solid_v flag to all wedge tines for cutout
        # This ensures wedges are built as solid trapezoids instead of hollow V
        if tine['type'] == 'wedge':
            tine['solid_v'] = True
    
    # Update the boat name to indicate it's a cutout
    if 'boat_name' in cutout_dimensions:
        cutout_dimensions['boat_name'] = f"{cutout_dimensions['boat_name']}_Cutout"
    
    return cutout_dimensions