"""
Build Display Macro - GUI Logic Only
Lightweight wrapper that handles only FreeCAD GUI display and interaction
All computation logic delegated to stock.stock_builder_core module

This file goes in: FreeCAD Macros folder
Main code is in: ~/Rudder_Code/stock/stock_builder_core.py
"""
import sys
import os
from pathlib import Path

# Add project root for module imports
project = Path.home() / "Rudder_Code"
if project.exists():
    sys.path.insert(0, str(project))

# Import the headless core module from Stock folder
try:
    from stock.stock_builder_core import StockBuilderCore
except ImportError:
    print("❌ Cannot import stock.stock_builder_core module")
    print("Make sure stock_builder_core.py is in ~/Rudder_Code/stock/")
    sys.exit(1)

# Import STEP save functionality
try:
    from helpers.step_save_load import save_step
except ImportError:
    print("❌ Cannot import STEP helper")
    print("Make sure step_save_load.py is in ~/Rudder_Code/helpers/")
    sys.exit(1)

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except ImportError:
    print("❌ FreeCAD not available - this display macro requires FreeCAD GUI")
    sys.exit(1)


class StockDisplayManager:
    """Handles only GUI display and interaction logic"""
    
    def __init__(self):
        self.core = StockBuilderCore(verbose=True)
        
    def setup_workbench(self):
        """Setup the appropriate workbench for 3D operations"""
        workbenches = ["PartWorkbench", "PartDesignWorkbench", "DraftWorkbench"]
        
        for wb in workbenches:
            try:
                Gui.activateWorkbench(wb)
                print(f"🔧 Activated workbench: {wb}")
                return True
            except:
                continue
        
        print("⚠️  Warning: Could not activate preferred workbench")
        return False
    
    def update_gui_view(self, doc):
        """Update GUI view with proper error handling"""
        try:
            if not (hasattr(Gui, 'activeDocument') and Gui.activeDocument()):
                print("⚠️  No active GUI document")
                return False
            
            # Force document recomputation
            doc.recompute()
            
            # Fit view to content
            try:
                Gui.SendMsgToActiveView("ViewFit")
            except:
                try:
                    Gui.activeDocument().activeView().fitAll()
                except:
                    print("⚠️  Could not fit view")
            
            # Set axonometric view for better 3D visualization
            try:
                Gui.activeDocument().activeView().viewAxonometric()
            except:
                try:
                    # Alternative view setting
                    Gui.activeDocument().activeView().viewIsometric()
                except:
                    print("⚠️  Could not set 3D view")
            
            # Set a nice background
            try:
                view = Gui.activeDocument().activeView()
                if hasattr(view, 'setBackgroundColor'):
                    view.setBackgroundColor(0.8, 0.8, 0.9)  # Light blue-gray
            except:
                pass
            
            print("🖥️  GUI view updated successfully")
            return True
            
        except Exception as e:
            print(f"⚠️  GUI update error: {e}")
            return False
    
    def display_object_properties(self, stock_obj):
        """Display object properties in the GUI"""
        try:
            if not stock_obj:
                return
            
            print(f"\n📦 Object Properties:")
            print(f"   Name: {stock_obj.Name}")
            print(f"   Type: {type(stock_obj).__name__}")
            
            if hasattr(stock_obj, 'Shape') and stock_obj.Shape:
                shape = stock_obj.Shape
                print(f"   Volume: {shape.Volume:.2f} mm³")
                print(f"   Surface Area: {shape.Area:.2f} mm²")
                
                # Get bounding box
                bbox = shape.BoundBox
                print(f"   Dimensions: {bbox.XLength:.1f} × {bbox.YLength:.1f} × {bbox.ZLength:.1f} mm")
                
                # Center the object if it's way off origin
                if abs(bbox.Center.x) > 1000 or abs(bbox.Center.y) > 1000:
                    print("   (Object appears to be far from origin)")
            
            # Select the object for easy identification
            try:
                Gui.Selection.clearSelection()
                Gui.Selection.addSelection(stock_obj)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️  Could not display properties: {e}")
    
    def setup_lighting_and_materials(self):
        """Enhance the visual appearance"""
        try:
            # Enable better lighting
            view = Gui.activeDocument().activeView()
            
            # Set render mode for better visualization
            render_modes = ["FlatLines", "Shaded", "Wireframe"]
            for mode in render_modes:
                try:
                    view.setRenderType(mode)
                    if mode == "FlatLines":  # Preferred mode
                        break
                except:
                    continue
            
            # Enable shadows if available
            try:
                view.setShadowsEnabled(True)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️  Could not enhance visual appearance: {e}")
    
    def export_stock_stl(self, stock_obj, boat_name="MackenSea"):
        """Export stock as STL for 3D printing"""
        try:
            # Set up output paths
            output_dir = project / "boats" / boat_name / "output" / "stock"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            stock_stl_file = output_dir / f"{boat_name}_Stock.stl"
            
            # Export stock as STL for 3D printing
            print(f"\n📤 Exporting stock as STL (for 3D printing)...")
            import Mesh
            Mesh.export([stock_obj], str(stock_stl_file))
            print(f"   Saved to: {stock_stl_file}")
            
            return True
                
        except Exception as e:
            print(f"❌ Export failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_with_gui(self, csv_path=None, boat_name="MackenSea", **kwargs):
        """Main execution with full GUI integration"""
        print("🔧 Starting Stock 3D Display Macro...")
        
        # Setup workbench first
        self.setup_workbench()
        
        try:
            # Use core module for all computation
            doc = self.core.create_document(clear_existing=True)
            
            if not doc:
                print("❌ Failed to create document")
                return False
            
            # Build geometry using headless core
            print("🏗️  Building geometry (delegated to core module)...")
            stock_obj = self.core.build_stock_geometry(doc, csv_path, **kwargs)
            
            if not stock_obj:
                print("❌ No stock object created")
                return False
            
            # Export stock STL
            export_success = self.export_stock_stl(stock_obj, boat_name)
            
            # Handle GUI-specific updates
            print("🖥️  Updating GUI display...")
            self.update_gui_view(doc)
            self.display_object_properties(stock_obj)
            self.setup_lighting_and_materials()
            
            # Show build summary
            summary = self.core.get_build_summary()
            print(f"\n✅ Display macro completed!")
            print(f"⏱️  Build time: {summary['stats'].get('build_time', 0):.2f} seconds")
            
            if export_success:
                print("📦 Stock STL exported successfully for 3D printing!")
            
            return True
            
        except Exception as e:
            print(f"❌ Display macro failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def run():
    """Main entry point for the macro"""
    try:
        display_manager = StockDisplayManager()
        return display_manager.run_with_gui()
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return False


def run_with_custom_csv(csv_path):
    """Run with custom CSV file path"""
    try:
        display_manager = StockDisplayManager()
        return display_manager.run_with_gui(csv_path=csv_path)
    except Exception as e:
        print(f"💥 Fatal error with custom CSV: {e}")
        return False


# Auto-run when executed as macro
if __name__ == "__main__":
    success = run()
    if success:
        print("🎉 Macro completed successfully!")
    else:
        print("💥 Macro completed with errors")
else:
    # Also run when imported (for macro compatibility)
    run()