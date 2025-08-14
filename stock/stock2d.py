# stock/stock2d.py
# Main module for building rudder stock geometry from CSV data

import os
import math
import FreeCAD as App
import Part
from FreeCAD import Vector

from stock.io import read_stock_csv_sectioned
from stock.geom import radius_at as _radius_at_core, append_post_segment_from_row
from stock.draw import create_drawing_page, calculate_uniform_scale
from stock.wedge import build_wedge
from stock.plate import build_plate
from stock.cylinder import build_cylinder
from stock.taper import build_taper
from stock.wedge_angled import build_wedge as build_wedge_angled
from stock.heel_cutter import apply_heel_cutter_workflow

VERSION = "1.2.8"

def build_stock_from_csv(doc: App.Document) -> App.DocumentObject:
    print(f"\nBuilding build_stock_from_csv v{VERSION}")

    csv_path = os.path.join(os.path.dirname(__file__), 'stock_sample.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    print(f"Reading CSV: {csv_path}")

    body = doc.addObject("Part::Feature", "RudderStock")
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

    rows, meta_info = read_stock_csv_sectioned(csv_path)
    summaries = []

    # Track which shapes belong to post vs non-post
    post_shape_indices = []
    non_post_shape_indices = []

    for row_dict in rows:
        shape_type = (row_dict.get('type') or '').strip().lower()
        if not shape_type:
            if 'plate' in row_dict:
                shape_type = 'plate'
            elif 'wedge' in row_dict:
                shape_type = 'wedge'

        try:
            # Track compound_shapes length before adding new shapes
            shapes_before = len(compound_shapes)

            if shape_type == 'cylinder':
                parts, summary = build_cylinder(row_dict)
                compound_shapes.extend(parts)
                summaries.append(summary)
                # Mark these as post shapes
                shapes_after = len(compound_shapes)
                new_indices = list(range(shapes_before, shapes_after))
                post_shape_indices.extend(new_indices)
                append_post_segment_from_row(post_segments, row_dict)

            elif shape_type == 'taper':
                parts, summary = build_taper(row_dict)
                compound_shapes.extend(parts)
                summaries.append(summary)
                # Mark these as post shapes
                shapes_after = len(compound_shapes)
                new_indices = list(range(shapes_before, shapes_after))
                post_shape_indices.extend(new_indices)
                append_post_segment_from_row(post_segments, row_dict)

            elif shape_type == 'plate':
                plate_parts, plate_summary = build_plate(row_dict, _radius_at)
                compound_shapes.extend(plate_parts)
                summaries.append(plate_summary)
                # Mark these as non-post shapes
                shapes_after = len(compound_shapes)
                new_indices = list(range(shapes_before, shapes_after))
                non_post_shape_indices.extend(new_indices)

            elif shape_type == 'wedge':
                try:
                    angle_val = float(row_dict.get('angle', '90') or 90.0)
                except Exception:
                    angle_val = 90.0
                if abs(angle_val - 90.0) < 1e-9:
                    wedge_parts, wedge_summary = build_wedge(row_dict, _radius_at)
                else:
                    wedge_parts, wedge_summary = build_wedge_angled(row_dict, _radius_at)
                compound_shapes.extend(wedge_parts)
                summaries.append(wedge_summary)
                # Mark these as non-post shapes
                shapes_after = len(compound_shapes)
                new_indices = list(range(shapes_before, shapes_after))
                non_post_shape_indices.extend(new_indices)

            else:
                print(f"  Unknown type in row: {row_dict}")

        except Exception as e:
            print(f"  Error parsing row {row_dict} -> {e}")

    # Apply smart heel cutting with tracked indices
    compound_shapes = apply_heel_cutter_workflow(doc, post_segments, summaries, compound_shapes, post_shape_indices, non_post_shape_indices)

    if meta_info:
        print(f"Meta: {meta_info}")
    print(f"Components: {', '.join(summaries) if summaries else 'none'}")

    if not compound_shapes:
        raise ValueError("No valid stock geometry found in CSV.")

    compound = Part.makeCompound(compound_shapes)
    body.Shape = compound
    doc.recompute()

    try:
        bbox = body.Shape.BoundBox
        print(f"Solids: {len(compound_shapes)}  "
              f"BBox: X[{bbox.XMin:.1f},{bbox.XMax:.1f}] "
              f"Y[{bbox.YMin:.1f},{bbox.YMax:.1f}] "
              f"Z[{bbox.ZMin:.1f},{bbox.ZMax:.1f}]")
    except Exception as e:
        print(f"Could not compute bbox summary: {e}")

    return body