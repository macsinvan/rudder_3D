"""
Wedge Cutout Dimension Helper
Creates modified dimensions for foil cutout tool with specified tolerance
Specific to wedge-style tine construction
"""

def create_wedge_cutout_dimensions(dimensions, tolerance_mm=2.0):
    """
    Transform stock dimensions to cutout dimensions with specified tolerance.
    Specific to wedge-style tine construction.
    
    Args:
        dimensions: Dictionary with stock dimensions structure
        tolerance_mm: Clearance to add in mm (default 2.0mm)
    
    Returns:
        Dictionary with same structure but modified for cutout
    """
    import copy
    
    # Deep copy to avoid modifying original
    cutout_dims = copy.deepcopy(dimensions)
    
    # Modify posts
    if 'posts' in cutout_dims:
        for post in cutout_dims['posts']:
            # Expand diameters (2x tolerance for diameter)
            if 'diameter_start' in post:
                post['diameter_start'] += 2 * tolerance_mm
            if 'diameter_end' in post:
                post['diameter_end'] += 2 * tolerance_mm
            
            # Extend heights
            if 'start' in post:
                post['start'] -= tolerance_mm
            if 'end' in post:
                post['end'] += tolerance_mm
    
    # Modify tines (wedge-specific)
    if 'tines' in cutout_dims:
        for tine in cutout_dims['tines']:
            if tine.get('type') == 'wedge':
                # Expand width (2x tolerance for width)
                if 'width' in tine:
                    tine['width'] += 2 * tolerance_mm
                
                # Extend length radially
                if 'length' in tine:
                    tine['length'] += tolerance_mm
                
                # Increase plate thickness (gap between plates)
                if 'plate_thickness' in tine:
                    tine['plate_thickness'] += tolerance_mm
                
                # Adjust start position
                if 'start' in tine:
                    tine['start'] -= tolerance_mm
    
    # Update labels to indicate cutout
    if 'posts' in cutout_dims:
        for post in cutout_dims['posts']:
            if 'label' in post:
                post['label'] += ' (Cutout)'
    
    if 'tines' in cutout_dims:
        for tine in cutout_dims['tines']:
            if 'label' in tine:
                tine['label'] += ' (Cutout)'
    
    return cutout_dims


def validate_wedge_dimensions(dimensions):
    """
    Validate that dimensions dictionary has expected structure for wedge cutout.
    
    Args:
        dimensions: Dictionary to validate
    
    Returns:
        Tuple (is_valid, error_messages)
    """
    errors = []
    
    # Check for required top-level keys
    if 'posts' not in dimensions:
        errors.append("Missing 'posts' key")
    if 'tines' not in dimensions:
        errors.append("Missing 'tines' key")
    
    # Validate posts
    if 'posts' in dimensions:
        for i, post in enumerate(dimensions['posts']):
            if 'type' not in post:
                errors.append(f"Post {i} missing 'type'")
            if post.get('type') == 'cylinder':
                if 'diameter_start' not in post:
                    errors.append(f"Cylinder post {i} missing 'diameter_start'")
            elif post.get('type') == 'taper':
                if 'diameter_start' not in post:
                    errors.append(f"Taper post {i} missing 'diameter_start'")
                if 'diameter_end' not in post:
                    errors.append(f"Taper post {i} missing 'diameter_end'")
    
    # Validate tines
    if 'tines' in dimensions:
        for i, tine in enumerate(dimensions['tines']):
            if tine.get('type') == 'wedge':
                required = ['width', 'length', 'plate_thickness', 'start']
                for field in required:
                    if field not in tine:
                        errors.append(f"Wedge tine {i} missing '{field}'")
    
    return (len(errors) == 0, errors)


def print_dimension_comparison(original, cutout, tolerance_mm=2.0):
    """
    Print a comparison table of original vs cutout dimensions.
    
    Args:
        original: Original dimensions dictionary
        cutout: Cutout dimensions dictionary  
        tolerance_mm: Tolerance value used
    """
    print(f"\n📊 Dimension Comparison (Tolerance: {tolerance_mm}mm)")
    print("=" * 70)
    
    # Compare posts
    if 'posts' in original and 'posts' in cutout:
        print("\n📍 POSTS:")
        for i, (orig, cut) in enumerate(zip(original['posts'], cutout['posts'])):
            print(f"\n  {orig.get('label', f'Post {i}')}:")
            print(f"    Type: {orig.get('type')}")
            if 'diameter_start' in orig:
                print(f"    Diameter Start: {orig['diameter_start']}mm → {cut['diameter_start']}mm (+{cut['diameter_start']-orig['diameter_start']}mm)")
            if 'diameter_end' in orig:
                print(f"    Diameter End: {orig['diameter_end']}mm → {cut['diameter_end']}mm (+{cut['diameter_end']-orig['diameter_end']}mm)")
            if 'start' in orig:
                print(f"    Start: {orig['start']}mm → {cut['start']}mm ({cut['start']-orig['start']:+.1f}mm)")
            if 'end' in orig:
                print(f"    End: {orig['end']}mm → {cut['end']}mm ({cut['end']-orig['end']:+.1f}mm)")
    
    # Compare tines
    if 'tines' in original and 'tines' in cutout:
        print("\n🔧 TINES (Wedges):")
        for i, (orig, cut) in enumerate(zip(original['tines'], cutout['tines'])):
            print(f"\n  {orig.get('label', f'Tine {i}')}:")
            if 'width' in orig:
                print(f"    Width: {orig['width']}mm → {cut['width']}mm (+{cut['width']-orig['width']}mm)")
            if 'length' in orig:
                print(f"    Length: {orig['length']}mm → {cut['length']}mm (+{cut['length']-orig['length']}mm)")
            if 'plate_thickness' in orig:
                print(f"    Plate Thickness: {orig['plate_thickness']}mm → {cut['plate_thickness']}mm (+{cut['plate_thickness']-orig['plate_thickness']}mm)")
            if 'start' in orig:
                print(f"    Start: {orig['start']}mm → {cut['start']}mm ({cut['start']-orig['start']:+.1f}mm)")
            if 'angle' in orig:
                print(f"    Angle: {orig['angle']}° (unchanged)")
    
    print("\n" + "=" * 70)


# Example usage function
def example_usage():
    """Example of how to use the wedge cutout dimension helper"""
    
    # Sample dimensions from CSV (as parsed)
    stock_dimensions = {
        'boat_name': 'MackenSea',
        'version': '1.0.0',
        'posts': [
            {
                'type': 'cylinder',
                'start': 0,
                'end': 20,
                'diameter_start': 44,
                'label': 'Rudder Sleeve'
            },
            {
                'type': 'taper',
                'start': 20,
                'end': 604,
                'diameter_start': 44,
                'diameter_end': 20,
                'label': 'Rudder Taper'
            }
        ],
        'tines': [
            {
                'type': 'wedge',
                'start': 113,
                'width': 40,
                'length': 220,
                'plate_thickness': 5,
                'angle': 93,
                'label': 'Support 2'
            },
            {
                'type': 'wedge',
                'start': 365,
                'width': 40,
                'length': 220,
                'plate_thickness': 5,
                'angle': 90,
                'label': 'Support 1'
            },
            {
                'type': 'wedge',
                'start': 560,
                'width': 40,
                'length': 240,
                'plate_thickness': 5,
                'angle': 135,
                'label': 'Support 3'
            }
        ]
    }
    
    # Validate dimensions
    is_valid, errors = validate_wedge_dimensions(stock_dimensions)
    if not is_valid:
        print("❌ Validation errors:")
        for error in errors:
            print(f"   - {error}")
        return None
    
    # Create cutout dimensions with 2mm tolerance
    tolerance = 2.0
    cutout_dimensions = create_wedge_cutout_dimensions(stock_dimensions, tolerance)
    
    # Print comparison
    print_dimension_comparison(stock_dimensions, cutout_dimensions, tolerance)
    
    return cutout_dimensions


if __name__ == "__main__":
    # Run example
    cutout_dims = example_usage()
    
    if cutout_dims:
        print("\n✅ Cutout dimensions created successfully!")
        print(f"   Boat: {cutout_dims.get('boat_name')}")
        print(f"   Posts: {len(cutout_dims.get('posts', []))}")
        print(f"   Tines: {len(cutout_dims.get('tines', []))}")