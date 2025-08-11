# stock/stock2d.py

import os
import csv
import math
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector

from stock.plate import make_wedge_debug_block, build_plate
from stock.wedge import build_wedge
from stock.io import read_stock_csv_sectioned
from stock.geom import radius_at as _radius_at_core, append_post_segment_from_row
from stock.draw import create_drawing_page, calculate_uniform_scale

VERSION = "1.2.8"  # wedge(90°): inside-edge tangent; plate 90° stays literal; refactors moved to modules

# ---------- Core build ----------

def build_stock_from_csv(doc: App.Document) -> App.DocumentObject:
    print(f"\n📄 build_stock_from_csv v{VERSION}")

    csv_path = os.path.join(os.path.dirname(__file__), 'stock_sample.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ CSV file not found: {csv_path}")
    print(f"📂 Reading CSV: {csv_path}")

    body = doc.addObject("Part::Feature", "RudderStock")
    compound_shapes = []

    # Collect post segments so we can query radius later
    post_segments = []
    _radius_debug_done = False

    def _radius_at(z_world: float) -> float:
        nonlocal _radius_debug_done
        if not _radius_debug_done:
            print(f"🔎 radius_at(): {len(post_segments)} post segment(s) available")
            for i, seg in enumerate(post_segments, 1):
                print(f"   •[{i}] {seg['kind']}  Z[{seg['z_bot']:.1f},{seg['z_top']:.1f}]  "
                      f"R[{seg['r_bot']:.2f},{seg['r_top']:.2f}]")
            _radius_debug_done = True
        return _radius_at_core(z_world, post_segments)

    # Read rows/meta
    rows, meta_info = read_stock_csv_sectioned(csv_path)
    summaries = []

    for row_dict in rows:
        # Decide handler from CSV: explicit 'type', or section header key (plate / wedge)
        shape_type = (row_dict.get('type') or '').strip().lower()
        if not shape_type:
            if 'plate' in row_dict:
                shape_type = 'plate'
            elif 'wedge' in row_dict:
                shape_type = 'wedge'

        label = row_dict.get('label', '')

        try:
            if shape_type == 'cylinder':
                z0 = -float(row_dict['start'])
                z1 = -float(row_dict['end'])
                base_z = min(z0, z1)
                height = abs(z1 - z0)
                d = float(row_dict['diameter_start'])
                cyl = Part.makeCylinder(d / 2.0, height, Vector(0, 0, base_z))
                compound_shapes.append(cyl)
                summaries.append(f"Cylinder '{label}' h={height} d={d}")
                print(f"  ✓ Cylinder: label='{label}', d={d}, z0={z0}, z1={z1}, base={base_z}, h={height}")

                append_post_segment_from_row(post_segments, row_dict)

            elif shape_type == 'taper':
                z0 = -float(row_dict['start'])
                z1 = -float(row_dict['end'])
                height = abs(z1 - z0)
                d1 = float(row_dict['diameter_start'])  # top
                d2 = float(row_dict['diameter_end'])    # bottom
                cone = Part.makeCone(d2 / 2.0, d1 / 2.0, height, Vector(0, 0, z0 - height))
                compound_shapes.append(cone)
                summaries.append(f"Taper '{label}' h={height} d1={d1}→d2={d2}")
                print(f"  ✓ Taper:   label='{label}', d_top={d1}, d_bot={d2}, base={z0 - height}, h={height}")

                append_post_segment_from_row(post_segments, row_dict)

            elif shape_type == 'plate':
                # MOVE-ONLY: delegate to stock.plate.build_plate (behavior unchanged)
                plate_parts, plate_summary = build_plate(row_dict, _radius_at)
                compound_shapes.extend(plate_parts)
                summaries.append(plate_summary)

            elif shape_type == 'wedge':
                wedge_parts, wedge_summary = build_wedge(row_dict, _radius_at)
                compound_shapes.extend(wedge_parts)
                summaries.append(wedge_summary)

            else:
                print(f"  ❌ Unknown type in row: {row_dict}")

        except Exception as e:
            print(f"  ❌ Error parsing row {row_dict} → {e}")

    if meta_info:
        print(f"📌 Meta: {meta_info}")
    print(f"📊 Components: {', '.join(summaries) if summaries else 'none'}")

    if not compound_shapes:
        raise ValueError("❌ No valid stock geometry found in CSV.")

    compound = Part.makeCompound(compound_shapes)
    body.Shape = compound
    doc.recompute()

    try:
        bbox = body.Shape.BoundBox
        print(
            f"📦 Solids: {len(compound_shapes)}  "
            f"BBox: X[{bbox.XMin:.1f},{bbox.XMax:.1f}] "
            f"Y[{bbox.YMin:.1f},{bbox.YMax:.1f}] "
            f"Z[{bbox.ZMin:.1f},{bbox.ZMax:.1f}]"
        )
    except Exception as e:
        print(f"⚠️ Could not compute bbox summary: {e}")

    return body