"""
stock_3D.py - Clean Version
Builds 3D rudder stock geometry from dimensions dictionary ONLY
No CSV knowledge whatsoever
"""

import FreeCAD as App
import Part

# Import geometry builders
from stock.geom import radius_at as _radius_at_core, append_post_segment_from_row
from stock.wedge import build_wedge
from stock.plate import build_plate
from stock.cylinder import build_cylinder
from stock.taper import build_taper
from stock.wedge_angled import build_wedge as build_wedge_angled
from stock.heel_cutter import apply_heel_cutter_workflow


def build_stock_from_dimensions(doc: App.Document, dimensions: dict) -> App.DocumentObject:
    """
    Build stock geometry from dimensions dictionary
    
    Args:
        doc: FreeCAD document
        dimensions: Dictionary with structure:
            {
                'boat_name': str,
                'posts': [
                    {'type': 'cylinder'|'taper', 'start': float, 'end': float, 
                     'diameter_start': float, 'diameter_end': float, 'label': str}
                ],
                'tines': [
                    {'type': 'wedge'|'plate', 'start': float, 'width': float,
                     'length': float, 'plate_thickness': float, 'angle': float, 
                     'solid_v': bool, 'label': str}
                ]
            }
    
    Returns:
        FreeCAD DocumentObject containing the stock geometry
    """
    boat_name = dimensions.get('boat_name', 'Stock')
    print(f"\n⚓ Building {boat_name} Stock from Dimensions")
    
    # Create the main body object
    body = doc.addObject("Part::Feature", f"{boat_name}_RudderStock")
    compound_shapes = []
    
    # Track post segments for radius queries
    post_segments = []
    _radius_debug_done = False
    
    def _radius_at(z_world: float) -> float:
        nonlocal _radius_debug_done
        if not _radius_debug_done:
            print(f"radius_at(): {len(post_segments)} post segment(s) available")
            for i, seg in enumerate(post_segments, 1):
                print(f"   [{i}] {seg['kind']}  Z[{seg['z_bot']:.1f},{seg['z_top']:.1f}]  "
                      f"R[{seg['r_bot']:.2f},{seg['r_top']:.2f}]")
            _radius_debug_done = True
        return _radius_at_core(z_world, post_segments)
    
    summaries = []
    
    # Track which shapes belong to post vs non-post
    post_shape_indices = []
    non_post_shape_indices = []
    
    # Process posts (cylinders and tapers)
    for post in dimensions.get('posts', []):
        try:
            shapes_before = len(compound_shapes)
            
            # Convert to row_dict format expected by builders
            row_dict = {
                'type': post['type'],
                'start': post['start'],
                'end': post['end'],
                'diameter': post.get('diameter_start'),  # For cylinder
                'diameter_start': post.get('diameter_start'),  # For taper
                'diameter_end': post.get('diameter_end'),  # For taper
                'label': post.get('label', '')
            }
            
            if post['type'] == 'cylinder':
                parts, summary = build_cylinder(row_dict)
                compound_shapes.extend(parts)
                summaries.append(summary)
                # Mark these as post shapes
                shapes_after = len(compound_shapes)
                new_indices = list(range(shapes_before, shapes_after))
                post_shape_indices.extend(new_indices)
                append_post_segment_from_row(post_segments, row_dict)
                
            elif post['type'] == 'taper':
                parts, summary = build_taper(row_dict)
                compound_shapes.extend(parts)
                summaries.append(summary)
                # Mark these as post shapes
                shapes_after = len(compound_shapes)
                new_indices = list(range(shapes_before, shapes_after))
                post_shape_indices.extend(new_indices)
                append_post_segment_from_row(post_segments, row_dict)
            
            else:
                print(f"  Unknown post type: {post['type']}")
                
        except Exception as e:
            print(f"  Error building post {post}: {e}")
    
    # Process tines (wedges and plates)
    for tine in dimensions.get('tines', []):
        try:
            shapes_before = len(compound_shapes)
            
            # Convert to row_dict format expected by builders
            row_dict = {
                'type': tine['type'],
                'start': tine['start'],
                'width': tine.get('width'),
                'length': tine.get('length'),
                'plate_thickness': tine.get('plate_thickness', 5),
                'angle': tine.get('angle', 90),
                'label': tine.get('label', '')
            }
            
            if tine['type'] == 'plate':
                plate_parts, plate_summary = build_plate(row_dict, _radius_at)
                compound_shapes.extend(plate_parts)
                summaries.append(plate_summary)
                # Mark these as non-post shapes
                shapes_after = len(compound_shapes)
                new_indices = list(range(shapes_before, shapes_after))
                non_post_shape_indices.extend(new_indices)
                
            elif tine['type'] == 'wedge':
                # Get solid_v from tine dictionary (will be True for cutouts, False for stock)
                solid_v = tine.get('solid_v', False)
                
                angle_val = float(tine.get('angle', 90))
                if abs(angle_val - 90.0) < 1e-9:
                    wedge_parts, wedge_summary = build_wedge(row_dict, _radius_at, solid_v=solid_v)
                else:
                    wedge_parts, wedge_summary = build_wedge_angled(row_dict, _radius_at, solid_v=solid_v)
                compound_shapes.extend(wedge_parts)
                summaries.append(wedge_summary)
                # Mark these as non-post shapes
                shapes_after = len(compound_shapes)
                new_indices = list(range(shapes_before, shapes_after))
                non_post_shape_indices.extend(new_indices)
            
            else:
                print(f"  Unknown tine type: {tine['type']}")
                
        except Exception as e:
            print(f"  Error building tine {tine}: {e}")
    
    # Apply smart heel cutting with visibility control
    compound_shapes = apply_heel_cutter_workflow(
        doc, post_segments, summaries, compound_shapes,
        post_shape_indices, non_post_shape_indices,
        debug_visible=False
    )
    
    print(f"Components: {', '.join(summaries) if summaries else 'none'}")
    
    if not compound_shapes:
        raise ValueError("No valid stock geometry found in dimensions.")
    
    # Create compound shape
    compound = Part.makeCompound(compound_shapes)
    body.Shape = compound
    doc.recompute()
    
    # Print summary
    try:
        bbox = body.Shape.BoundBox
        print(f"Solids: {len(compound_shapes)}  "
              f"BBox: X[{bbox.XMin:.1f},{bbox.XMax:.1f}] "
              f"Y[{bbox.YMin:.1f},{bbox.YMax:.1f}] "
              f"Z[{bbox.ZMin:.1f},{bbox.ZMax:.1f}]")
    except Exception as e:
        print(f"Could not compute bbox summary: {e}")
    
    print(f"⚓ {boat_name} stock geometry complete!")
    
    return body