"""
Build Stock Cutout - FreeCAD UI Macro
Import stock STEP file and prepare for cutout tool generation

This file goes in: FreeCAD Macros folder
Core logic is in: ~/Rudder_Code/Cutout/cutout_builder_core.py
"""
import sys
import os
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui

# Add project root for imports
project_root = Path.home() / "Rudder_Code"
if project_root.exists():
    sys.path.insert(0, str(project_root))
else:
    print(f"❌ Project directory not found: {project_root}")
    sys.exit(1)

# Try multiple import approaches
try:
    from Cutout.cutout_builder_core import CutoutBuilderCore
except ImportError:
    try:
        # Try direct file import if package import fails
        cutout_core_path = project_root / "Cutout" / "cutout_builder_core.py"
        if cutout_core_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("cutout_builder_core", cutout_core_path)
            cutout_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cutout_module)
            CutoutBuilderCore = cutout_module.CutoutBuilderCore
        else:
            raise ImportError(f"cutout_builder_core.py not found at {cutout_core_path}")
    except ImportError as e:
        print(f"❌ Cannot import cutout builder core: {e}")
        print("Make sure cutout_builder_core.py is in ~/Rudder_Code/Cutout/")
        print("Also run: mkdir -p ~/Rudder_Code/Cutout && touch ~/Rudder_Code/Cutout/__init__.py")
        sys.exit(1)

def main():
    """Main macro execution"""
    print("🔧 Starting Stock Cutout Builder...")
    
    # Set boat name and build file paths
    boat_name = "MackenSea"
    stock_dir = project_root / "boats" / boat_name / "output" / "stock"
    input_file = stock_dir / f"{boat_name}_Stock.step"
    output_file = stock_dir / f"{boat_name}_Cutout.step"
    
    # Check input file exists
    if not input_file.exists():
        print(f"❌ Stock file not found: {input_file}")
        return
    
    try:
        # Use STEP helper directly
        from helpers.step_save_load import load_step, save_step
        
        # Import
        print(f"📥 Importing: {input_file}")
        doc, imported_objects = load_step(str(input_file))
        
        # Rename to "stock" (only Label can be changed)
        stock_obj = imported_objects[0]
        stock_obj.Label = "Stock"
        
        # Recompute and fit view
        doc.recompute()
        Gui.SendMsgToActiveView("ViewFit")
        
        print(f"✅ Stock loaded as: {stock_obj.Name}")
        print("🎯 Ready for cutout preparation")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()