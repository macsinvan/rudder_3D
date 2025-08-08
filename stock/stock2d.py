# outline/stock/stock2d.py

import os
import csv
import FreeCAD as App
import FreeCADGui as Gui
import Part
import TechDraw
import TechDrawGui
from FreeCAD import Vector
from stock.io import read_stock_csv_sectioned  # NEW: use shared CSV reader

VERSION = "1.1.1"  # print-only update

# ---------- Helpers ----------

def make_wedge_debug_block(start: float, width: float, length_out: float, plate_thickness: float) -> Part.Shape:
    """
    Debug helper: simple rectangular block to validate tine Z placement.
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

    # NEW: use the section-aware reader; keep the rest identical
    rows, meta_info = read_stock_csv_sectioned(csv_path)
    summaries = []

    for row_dict in rows:
        # NOTE: do not change logic that was previously working
        # shape_type comes from 'type' when present (post sections)
        # or from the presence of the header name 'wedge' (tine section)
        shape_type = row_dict.get('type', '').lower()
        if not shape_type and 'wedge' in row_dict:
            shape_type = 'wedge'  # keep behavior that rendered tine previously

        label = row_dict.get('label', '')

        try:
            if shape_type == 'cylinder':
                # build down in -Z
                z0 = -float(row_dict['start'])
                z1 = -float(row_dict['end'])
                base_z = min(z0, z1)
                height = abs(z1 - z0)
                d = float(row_dict['diameter_start'])
                cyl = Part.makeCylinder(d / 2.0, height, Vector(0, 0, base_z))
                compound_shapes.append(cyl)
                summaries.append(f"Cylinder '{label}' h={height} d={d}")
                print(f"  ✓ Cylinder: label='{label}', d={d}, z0={z0}, z1={z1}, base={base_z}, h={height}")

            elif shape_type == 'taper':
                z0 = -float(row_dict['start'])
                z1 = -float(row_dict['end'])
                height = abs(z1 - z0)
                d1 = float(row_dict['diameter_start'])  # top
                d2 = float(row_dict['diameter_end'])    # bottom
                # place so it tapers as Z decreases
                cone = Part.makeCone(d2 / 2.0, d1 / 2.0, height, Vector(0, 0, z0 - height))
                compound_shapes.append(cone)
                summaries.append(f"Taper '{label}' h={height} d1={d1}→d2={d2}")
                print(f"  ✓ Taper:   label='{label}', d_top={d1}, d_bot={d2}, base={z0 - height}, h={height}")

            elif shape_type == 'wedge':
                # tine wedge (debug block form)
                start = float(row_dict['start'])
                width = float(row_dict['width'])
                length_out = float(row_dict['length'])
                t = float(row_dict['plate_thickness'])
                wedge = make_wedge_debug_block(start, width, length_out, t)
                compound_shapes.append(wedge)
                summaries.append(f"Tine '{label}' start={start} w={width} len={length_out} t={t}")
                print(f"  ✓ Tine:    label='{label}', start={start}, width={width}, length={length_out}, t={t}")

            else:
                print(f"  ❌ Unknown type in row: {row_dict}")
                # keep behavior (just skip)

        except Exception as e:
            print(f"  ❌ Error parsing row {row_dict} → {e}")
            # keep loop going without changing behavior

    if meta_info:
        print(f"📌 Meta: {meta_info}")
    print(f"📊 Components: {', '.join(summaries) if summaries else 'none'}")

    if not compound_shapes:
        raise ValueError("❌ No valid stock geometry found in CSV.")

    compound = Part.makeCompound(compound_shapes)
    body.Shape = compound
    doc.recompute()
    
    # Summary line with counts and bbox
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