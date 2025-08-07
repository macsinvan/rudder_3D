import csv
import os
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part
import TechDraw
import TechDrawGui
from FreeCAD import Vector

def load_stock_csv():
    csv_path = os.path.join(os.path.dirname(__file__), 'stock_sample.csv')
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            length = float(row['length'])
            diameter = float(row['diameter'])
            return length, diameter

def draw_simple_stock_2d(length: float, diameter: float, center=App.Vector(0, 0, 0)):
    radius = diameter / 2
    circle_edge = Part.makeCircle(radius, center)
    circle_wire = Part.Wire([circle_edge])
    circle_face = Part.Face(circle_wire)
    return circle_face

def extrude_stock_3d(circle: Part.Shape, length: float) -> Part.Shape:
    vec = Vector(0, 0, length)
    return circle.extrude(vec)

def calculate_uniform_scale(length_mm, diameter_mm, page_width=180, page_height=257, buffer=10):
    max_width = page_width - 2 * buffer
    max_height = page_height - 2 * buffer
    scale_x = max_width / diameter_mm
    scale_y = max_height / length_mm
    return min(scale_x, scale_y)

def create_drawing_page(doc: App.Document, stock_obj: App.DocumentObject,
                        length: float, diameter: float,
                        title: str = "Rudder Stock Drawing"):

    page = doc.addObject('TechDraw::DrawPage', 'StockDrawing')
    template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    template_path = "/Applications/FreeCAD.app/Contents/Resources/share/Mod/TechDraw/Templates/A4_Portrait_blank.svg"
    template.Template = template_path
    page.Template = template

    scale = calculate_uniform_scale(length, diameter)

    side_view = doc.addObject('TechDraw::DrawViewPart', 'SideView')
    side_view.Source = [stock_obj]
    side_view.Direction = (0, 1, 0)  # Front view
    side_view.ScaleType = "Custom"
    side_view.Scale = scale
    side_view.X = 90
    side_view.Y = 128
    page.addView(side_view)

    doc.recompute()
    Gui.activeDocument().setEdit(page.Name)
    doc.recompute()
    Gui.updateGui()

    output_dir = Path.home() / "Rudder_Code" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = str(output_dir / "stock_drawing.pdf")
    TechDrawGui.exportPageAsPdf(page, pdf_path)
    print(f"✅ Drawing exported to: {pdf_path}")

    return page
