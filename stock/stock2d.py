# stock/stock2d.py

import os
import csv
import math
import FreeCAD as App
import FreeCADGui as Gui
import Part
import TechDraw
import TechDrawGui
from FreeCAD import Vector
from stock.io import read_stock_csv_sectioned
from stock.geom import radius_at as _radius_at_core, append_post_segment_from_row

VERSION = "1.2.8"  # wedge(90°): fix post-end gap via correct pivot; alpha=atan((t/2)/length); no tip trim/strap

# ---------- Helpers ----------

def make_wedge_debug_block(start: float, width: float, length_out: float, plate_thickness: float) -> Part.Shape:
    """
    Simple rectangular block to validate tine Z placement.
    - Top face at Z = -start (we build downwards)
    - Extends downward by 'width'
    - Extends outboard along +X by 'length_out'
    - Visible thickness across Y = 2 * plate_thickness
    """
    box = Part.makeBox(length_out, 2.0 * plate_thickness, width)
    # Place min corner so top face is at -start and block extends downward by 'width'
    box.Placement.Base = Vector(0.0, -plate_thickness, -(start + width))
    return box

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

                if abs(angle_deg - 90.0) < 1e-9:
                    p = Part.makeBox(length_out, t, width)
                    p.Placement.Base = Vector(r, -t/2.0, -(start + width))
                    compound_shapes.append(p)
                    summaries.append(f"Plate '{label}' start={start} w={width} len={length_out} t={t} r_at={r:.2f}")
                    print(f"  ✓ Plate:   label='{label}', start={start}, width={width}, length={length_out}, t={t}, r_at={r:.2f}")
                else:
                    tilt = 90.0 - angle_deg
                    rot_deg = -tilt
                    rot_rad = math.radians(abs(tilt))
                    extra = width * math.tan(rot_rad) if abs(tilt) > 1e-9 else 0.0
                    eff_len = length_out + extra

                    p = Part.makeBox(eff_len, t, width)
                    p.Placement.Base = Vector(r, -t/2.0, -(start + width))

                    pivot = Vector(r, 0.0, -start)
                    p = p.copy()
                    p.rotate(pivot, Vector(0,1,0), rot_deg)

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
                # Two steel strips (V)
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

                if abs(angle_deg - 90.0) < 1e-9:
                    # TEST: hard-code the opening angle to 20° and pivot at the TIP (x = r + length_out)
                    alpha_deg = 20.0

                    # Top strip
                    p_top = Part.makeBox(length_out, t, width)
                    p_top.Placement.Base = Vector(r, +0.5 * t, -(start + width))
                    tip_pivot_top = Vector(r + length_out, +0.5 * t, -start)  # changed pivot (tip)
                    p_top = p_top.copy()
                    p_top.rotate(tip_pivot_top, Vector(0, 0, 1), -alpha_deg)

                    # Bottom strip
                    p_bot = Part.makeBox(length_out, t, width)
                    p_bot.Placement.Base = Vector(r, -1.5 * t, -(start + width))
                    tip_pivot_bot = Vector(r + length_out, -0.5 * t, -start)  # changed pivot (tip)
                    p_bot = p_bot.copy()
                    p_bot.rotate(tip_pivot_bot, Vector(0, 0, 1), +alpha_deg)

                    compound_shapes.extend([p_top, p_bot])  # no strap in this test
                    summaries.append(
                        f"Wedge90 '{label}' start={start} w={width} len(edge)={length_out} t={t} r_at={r:.2f} alphaTest={alpha_deg:.3f}° (tip pivot)"
                    )
                    print(
                        f"  ✓ Wedge90: label='{label}', r={r:.2f}, t={t}, len={length_out}, alphaTest={alpha_deg:.3f}° (tip pivot)"
                    )
                else:
                    # Keep existing angled behavior (unchanged)
                    t_end = 2.0
                    tilt   = 90.0 - angle_deg
                    rot_deg = -tilt
                    rot_rad = math.radians(abs(tilt))
                    extra   = width * math.tan(rot_rad) if abs(tilt) > 1e-9 else 0.0
                    eff_len = length_out + extra

                    p_top = Part.makeBox(eff_len, t, width)
                    p_bot = Part.makeBox(eff_len, t, width)
                    p_top.Placement.Base = Vector(r,  +t/2.0, -(start + width))
                    p_bot.Placement.Base = Vector(r,  -t - t/2.0, -(start + width))

                    pivot = Vector(r, 0.0, -start)
                    p_top = p_top.copy(); p_top.rotate(pivot, Vector(0,1,0), rot_deg)
                    p_bot = p_bot.copy(); p_bot.rotate(pivot, Vector(0,1,0), rot_deg)

                    x_cut = r + length_out * math.cos(math.radians(abs(tilt)))
                    trim  = Part.makeBox(x_cut + 10000.0, 20000.0, 20000.0,
                                         Vector(-10000.0, -10000.0, -10000.0))
                    p_top = p_top.common(trim)
                    p_bot = p_bot.common(trim)
                    if p_top.isNull() or p_bot.isNull():
                        print("  ⚠️ Wedge plates became null after trim; check angle/length inputs and x_cut.")

                    strap = Part.makeBox(t_end, 3.0 * t, width)
                    strap.Placement.Base = Vector(x_cut - t_end, -1.5 * t, -(start + width))

                    compound_shapes.extend([p_top, p_bot, strap])
                    summaries.append(
                        f"Wedge '{label}' start={start} w={width} len={length_out} t={t} "
                        f"angle={angle_deg} r_at={r:.2f}"
                    )
                    print(
                        f"  ✓ Wedge*:  label='{label}', start={start}, width={width}, length={length_out}, "
                        f"t={t}, angle={angle_deg:.2f}°, rot={rot_deg:.2f}°, x_cut={x_cut:.2f}, r_at={r:.2f}"
                    )

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

# ---------- Drawing ----------

def calculate_uniform_scale(length_mm, diameter_mm, page_width=180, page_height=257, buffer=10):
    max_w = page_width - 2 * buffer
    max_h = page_height - 2 * buffer
    return min(max_w / diameter_mm, max_h / length_mm)

def create_drawing_page(doc: App.Document, stock_obj: App.DocumentObject,
                        length: float, diameter: float,
                        title: str = "Rudder Stock Drawing"):
    page = doc.addObject('TechDraw::DrawPage', 'StockDrawing')
    template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    template.Template = "/Applications/FreeCAD.app/Contents/Resources/share/Mod/TechDraw/Templates/A4_Portrait_blank.svg"
    page.Template = template

    scale = calculate_uniform_scale(length, diameter)

    side_view = doc.addObject('TechDraw::DrawViewPart', 'SideView')
    side_view.Source = [stock_obj]
    side_view.Direction = (0, 1, 0)
    side_view.ScaleType = "Custom"
    side_view.Scale = scale
    side_view.X = 90
    side_view.Y = 128
    page.addView(side_view)

    doc.recompute()
    Gui.activeDocument().setEdit(page.Name)
    doc.recompute()
    Gui.updateGui()

    pdf_path = os.path.expanduser("~/Rudder_Code/output/stock_drawing.pdf")
    TechDrawGui.exportPageAsPdf(page, pdf_path)
    print(f"✅ Drawing exported to: {pdf_path}")
    return page