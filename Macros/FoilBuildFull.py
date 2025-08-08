import FreeCAD as App
import FreeCADGui as Gui
import outline.stock.stock2d as stock2d

doc = App.newDocument("TestStockDrawing")

# Build 3D model from CSV and get key values
part_obj, total_length, max_diameter = stock2d.build_stock_from_csv(doc)

# Use computed values to drive drawing
stock2d.create_drawing_page(doc, part_obj, total_length, max_diameter)

# Fit 3D view
Gui.activeDocument().activeView().viewAxonometric()
Gui.SendMsgToActiveView("ViewFit")