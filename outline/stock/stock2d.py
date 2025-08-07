import csv
import os
import FreeCAD as App
import Part
import TechDraw
import TechDrawGui
from FreeCAD import Vector


def load_stock_csv():
    """
    Load stock dimensions from stock_sample.csv located in the same directory.
    Returns:
        tuple: (length, diameter)
    """
    csv_path = os.path.join(os.path.dirname(__file__), 'stock_sample.csv')
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            length = float(row['length'])
            diameter = float(row['diameter'])
            return length, diameter


def draw_simple_stock_2d(length: float, diameter: float, center=App.Vector(0, 0, 0)):
    """
    Draws a filled 2D circle representing the rudder stock.
    Args:
        length (float): (Not used in 2D, but kept for compatibility.)
        diameter (float): Diameter of the circle.
        center (Vector): Center position of the circle.
    Returns:
        Part.Shape: A filled face shape that can be extruded.
    """
    radius = diameter / 2
    circle_edge = Part.makeCircle(radius, center)
    circle_wire = Part.Wire([circle_edge])
    circle_face = Part.Face(circle_wire)
    return circle_face


def extrude_stock_3d(circle: Part.Shape, length: float) -> Part.Shape:
    """
    Extrudes the 2D circle into a 3D cylinder shape.
    """
    vec = Vector(0, 0, length)
    return circle.extrude(vec)


def create_drawing_page(doc: App.Document, stock_obj: App.DocumentObject, title: str = "Rudder Stock Drawing"):
    """
    Creates a TechDraw page with top view of the stock using a built-in template.
    Args:
        doc (App.Document): The active FreeCAD document.
        stock_obj (App.DocumentObject): The Part::Feature object to display.
        title (str): Title for the drawing page.
    Returns:
        App.DocumentObject: The created drawing page.
    """
    page = doc.addObject('TechDraw::DrawPage', 'StockDrawing')

    template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    template_path = "/Applications/FreeCAD.app/Contents/Resources/share/Mod/TechDraw/Templates/A4_Landscape_blank.svg"
    template.Template = template_path
    page.Template = template

    view = doc.addObject('TechDraw::DrawViewPart', 'TopView')
    view.Source = [stock_obj]
    view.Direction = (0, 0, 1)  # Top view
    view.Scale = 0.25
    view.X = 100
    view.Y = 100
    page.addView(view)

    doc.recompute()

    # Export to PDF (manual export method)
    pdf_path = os.path.expanduser("~/Rudder_Code/output/stock_drawing.pdf")
    TechDrawGui.exportPageAsPdf(page, pdf_path)
    print(f"✅ Drawing exported to: {pdf_path}")

    return page