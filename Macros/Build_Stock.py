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

# Import the core module
try:
    from stock.stock_builder_core import StockBuilderCore
except ImportError:
    print("❌ Cannot import stock.stock_builder_core module")
    print("Make sure stock_builder_core.py is in ~/Rudder_Code/stock/")
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
    
    def display_object_properties(self, obj, obj_type="Stock"):
        """Display object properties in the GUI"""
        try:
            if not obj:
                return
            
            print(f"\n📦 {obj_type} Object Properties:")
            print(f"   Name: {obj.Name}")
            print(f"   Label: {obj.Label}")
            print(f"   Type: {type(obj).__name__}")
            
            # Check for our custom property
            if hasattr(obj, 'IntendedName') and obj.IntendedName:
                print(f"   Intended Name: {obj.IntendedName}")
            
            if hasattr(obj, 'Shape') and obj.Shape:
                shape = obj.Shape
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
                if obj_type == "Stock":
                    Gui.Selection.clearSelection()
                Gui.Selection.addSelection(obj)
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
    
    def export_stl(self, obj, object_name):
        """Export object as STL for 3D printing"""
        try:
            # Extract boat name from object name
            boat_name = object_name.split("_")[0]
            
            # Determine if this is a cutout
            is_cutout = "_Cutout" in object_name
            subdir = "cutout" if is_cutout else "stock"
            
            # Set up output paths
            output_dir = project / "boats" / boat_name / "output" / subdir
            output_dir.mkdir(parents=True, exist_ok=True)
            
            stl_filename = f"{object_name}.stl"
            stl_file = output_dir / stl_filename
            
            # Export as STL
            print(f"\n📤 Exporting {object_name} as STL...")
            import Mesh
            Mesh.export([obj], str(stl_file))
            print(f"   Saved to: {stl_file}")
            
            return True
                
        except Exception as e:
            print(f"❌ STL export failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_with_gui(self, csv_path=None, **kwargs):
        """Main execution with full GUI integration
        
        Args:
            csv_path: Path to CSV file (shows dialog if not provided)
            **kwargs: Additional parameters (e.g., cutout_tolerance_mm)
        """
        print("🔧 Starting Stock 3D Display Macro...")
        
        # Setup workbench first
        self.setup_workbench()
        
        try:
            # Create document
            doc = self.core.create_document(clear_existing=True)
            
            if not doc:
                print("❌ Failed to create document")
                return False
            
            # Use the unified build method - NO dimensions parameter!
            print("🏗️  Building geometry...")
            results = self.core.build(doc=doc, csv_path=csv_path, **kwargs)
            
            # Check what we got
            stock_obj = results.get('stock')
            cutout_obj = results.get('cutout')
            
            if not stock_obj:
                print("❌ No stock object created")
                return False
            
            # Export STL files
            print("\n📦 Exporting STL files for 3D printing...")
            stock_name = self.core._get_object_name(stock_obj)
            self.export_stl(stock_obj, stock_name)
            
            if cutout_obj:
                cutout_name = self.core._get_object_name(cutout_obj)
                self.export_stl(cutout_obj, cutout_name)
            
            # Handle GUI-specific updates
            print("\n🖥️  Updating GUI display...")
            self.update_gui_view(doc)
            
            # Display properties for both objects
            self.display_object_properties(stock_obj, "Stock")
            if cutout_obj:
                self.display_object_properties(cutout_obj, "Cutout")
            
            self.setup_lighting_and_materials()
            
            # Show build summary
            print(f"\n✅ Display macro completed!")
            print(f"📊 Build Summary:")
            print(f"   Boat: {results['boat_name']}")
            print(f"   Style: {results['style']}")
            print(f"   Objects created: {results['stats']['objects_created']}")
            print(f"   Build time: {results['stats']['total_time']:.2f} seconds")
            
            if results['style'] == 'wedge':
                print("   ✓ Stock and cutout created (wedge style)")
            else:
                print(f"   ✓ Stock only created ({results['style']} style)")
            
            return True
            
        except Exception as e:
            print(f"❌ Display macro failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def run(csv_path=None, **kwargs):
    """Main entry point for the macro
    
    Args:
        csv_path: Optional path to CSV file
        **kwargs: Additional parameters (e.g., cutout_tolerance_mm)
    """
    try:
        display_manager = StockDisplayManager()
        return display_manager.run_with_gui(csv_path=csv_path, **kwargs)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return False


def run_with_custom_csv(csv_path):
    """Run with custom CSV file path (backward compatibility)"""
    return run(csv_path=csv_path)


# Auto-run when executed as macro
if __name__ == "__main__":
    # Default: run (will show file dialog if no CSV specified)
    success = run()
    if success:
        print("🎉 Macro completed successfully!")
    else:
        print("💥 Macro completed with errors")