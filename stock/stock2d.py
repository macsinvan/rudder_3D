# stock/stock2d.py

import os
import csv
import math
import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from stock.plate import make_wedge_debug_block
from stock.wedge import build_wedge
from stock.io import read_stock_csv_sectioned
from stock.geom import radius_at as _radius_at_core, append_post_segment_from_row
from stock.draw import create_drawing_page, calculate_uniform_scale  # ← moved here
from stock.plate_math import compute_plate_angles  # ← present but unused in this pass

VERSION = "1.2.8"  # wedge(90°): fix post-end gap via correct pivot; alpha=atan((t/2)/length); no tip trim/strap

# ---------- Helpers ----------

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
                # Solid plate tine (single plate), angle-aware
                start = float(row_dict['start'])
                width = float(row_dict['width'])
                length_out = float(row_dict['length'])
                t = float(row_dict['plate_thickness'])
                angle_deg = float(row_dict.get('angle', '90') or 90.0)

                z_attach = -start
                try:
                    r = _radius_at(z_attach)
                except Exception as e:
                    print(f"  ⚠️ radius_at({z_attach:.1f}) failed: {e}; default r=0")
                    r = 0.0

                # NOTE: Regression fix — leave 90° as literal 90°, do not auto-adjust to 90−α here.
                # (If we later want an explicit 'auto' mode, we can add it in a separate step.)

                if abs(angle_deg - 90.0) < 1e-9:
                    # Flat/orthogonal plate
                    p = Part.makeBox(length_out, t, width)
                    p.Placement.Base = Vector(r, -t/2.0, -(start + width))
                    compound_shapes.append(p)
                    summaries.append(f"Plate '{label}' start={start} w={width} len={length_out} t={t} r_at={r:.2f}")
                    print(f"  ✓ Plate:   label='{label}', start={start}, width={width}, length={length_out}, t={t}, r_at={r:.2f}")
                else:
                    # Rotated plate (angle-aware)
                    tilt = 90.0 - angle_deg
                    rot_deg = -tilt
                    rot_rad = math.radians(abs(tilt))
                    extra = width * math.tan(rot_rad) if abs(tilt) > 1e-9 else 0.0
                    eff_len = length_out + extra

                    p = Part.makeBox(eff_len, t, width)
                    p.Placement.Base = Vector(r, -t/2.0, -(start + width))

                    pivot = Vector(r, 0.0, -start)
                    p = p.copy()
                    p.rotate(pivot, Vector(0, 1, 0), rot_deg)

                    x_cut = r + length_out * math.cos(math.radians(abs(tilt)))
                    trim = Part.makeBox(x_cut + 10000.0, 20000.0, 20000.0,
                                        Vector(-10000.0, -10000.0, -10000.0))
                    p = p.common(trim)
                    if p.isNull():
                        print("  ⚠️ Plate became null after trim; check angle/length inputs and x_cut.")

                    compound_shapes.append(p)
                    summaries.append(
                        f"Plate '{label}' start={start} w={width} len={length_out} t={t} "
                        f"angle={angle_deg} r_at={r:.2f}"
                    )
                    print(f"  ✓ Plate*:  label='{label}', start={start}, width={width}, length={length_out}, "
                          f"t={t}, angle={angle_deg:.2f}°, rot={rot_deg:.2f}°")

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
        print(f"📦 Solids: {len(compound_shapes)}  "
              f"BBox: X[{bbox.XMin:.1f},{bbox.XMax:.1f}] "
              f"Y[{bbox.YMin:.1f},{bbox.YMax:.1f}] "
              f"Z[{bbox.ZMin:.1f},{bbox.ZMax:.1f}]")
    except Exception as e:
        print(f"⚠️ Could not compute bbox summary: {e}")
    return body