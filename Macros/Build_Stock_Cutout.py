"""
Simple Stock Import - FreeCAD UI Macro
Calls the simple_step_tool to import and show STEP files

This file goes in: FreeCAD Macros folder
Core logic is in: ~/Rudder_Code/Cutout/simple_step_tool.py
"""
import sys
from pathlib import Path
import FreeCADGui as Gui

# Add project root for imports
project_root = Path.home() / "Rudder_Code"
sys.path.insert(0, str(project_root))

# Import and run the tool
from Cutout.cutout_builder_core import import_show_export

# Set paths
boat_name = "MackenSea"
stock_dir = project_root / "boats" / boat_name / "output" / "stock"
input_file = stock_dir / f"{boat_name}_Stock.step"

# Run import/show
doc, objects = import_show_export(str(input_file))

# Set to front view and fit
Gui.activeDocument().activeView().viewFront()
Gui.SendMsgToActiveView("ViewFit")