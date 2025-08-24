"""
Cutout Builder Core - Headless computation module
Import stock STEP files and prepare for cutout tool generation
Can be run in headless mode, testing, or batch processing environments

This file goes in: ~/Rudder_Code/Cutout/cutout_builder_core.py
Display macro is in: FreeCAD Macros folder
"""
import sys
import os
from pathlib import Path
import json
import time

# Add project root for module imports
project = Path.home() / "Rudder_Code"
if project.exists():
    sys.path.insert(0, str(project))
    # This file goes in: ~/Rudder_Code/Cutout/cutout_builder_core.py
else:
    print(f"⚠️  Warning: Project directory not found at {project}")

# Import the STEP helper
try:
    from helpers.step_save_load import save_step, load_step, StepHandler, StepFileError
except ImportError as e:
    print(f"⚠️  Warning: Could not import STEP helper: {e}")
    print("Make sure step_save_load.py is in ~/Rudder_Code/helpers/")

class CutoutBuilderCore:
    """Core cutout preparation functionality without GUI dependencies"""
    
    def __init__(self, project_path=None, verbose=True):
        self.project_path = Path(project_path) if project_path else project
        self.verbose = verbose
        self.import_stats = {}
        
    def log(self, message):
        """Conditional logging based on verbose setting"""
        if self.verbose:
            print(message)
    
    def validate_environment(self):
        """Validate that all required dependencies are available"""
        errors = []
        warnings = []
        
        # Check project directory
        if not self.project_path.exists():
            errors.append(f"Project directory not found: {self.project_path}")
        
        # Check for FreeCAD (but don't fail if not available in headless mode)
        try:
            import FreeCAD as App
            self.log(f"✅ FreeCAD available: {App.Version()}")
        except ImportError:
            warnings.append("FreeCAD not available - running in simulation mode")
        
        # Check for STEP helper
        try:
            from helpers.step_save_load import save_step
            self.log("✅ STEP helper available")
        except ImportError:
            warnings.append("STEP helper not available - limited import functionality")
        
        return errors, warnings
    
    def create_document(self, doc_name="Cutout_Preparation", clear_existing=True):
        """Create FreeCAD document or return mock for headless mode"""
        try:
            import FreeCAD as App
            
            if doc_name in App.listDocuments():
                self.log(f"📄 Reusing existing document: {doc_name}")
                doc = App.getDocument(doc_name)
                
                if clear_existing:
                    # Safe object removal
                    objects_to_remove = [obj.Name for obj in doc.Objects if not obj.InList]
                    for obj_name in objects_to_remove:
                        try:
                            doc.removeObject(obj_name)
                        except:
                            self.log(f"⚠️  Could not remove object: {obj_name}")
            else:
                self.log(f"📄 Creating new document: {doc_name}")
                doc = App.newDocument(doc_name)
            
            return doc
            
        except ImportError:
            # Return mock document for headless mode
            self.log("📄 Creating mock document (headless mode)")
            return MockDocument(doc_name)
    
    def import_stock_step(self, step_filename, doc=None):
        """Import stock STEP file and rename to 'stock'"""
        import_start = time.time()
        
        try:
            import FreeCAD as App
            
            self.log(f"📥 Importing stock from STEP: {step_filename}")
            
            # Create document if not provided
            if doc is None:
                doc = self.create_document()
            
            # Use STEP helper to load file
            doc, imported_objects = load_step(step_filename, doc.Name, verbose=self.verbose)
            
            if not imported_objects:
                raise Exception("No objects were imported from STEP file")
            
            # Get the main stock object (assume first/largest object)
            stock_obj = imported_objects[0]
            
            # Rename to "stock" for consistent naming
            if hasattr(stock_obj, 'Name'):
                stock_obj.Name = "stock"
                if hasattr(stock_obj, 'Label'):
                    stock_obj.Label = "Stock"
            
            # Collect import statistics
            self.import_stats = {
                'object_name': stock_obj.Name,
                'object_type': type(stock_obj).__name__,
                'import_time': time.time() - import_start,
                'mode': 'freecad',
                'source_file': step_filename,
                'objects_imported': len(imported_objects)
            }
            
            # Try to get shape properties
            try:
                if hasattr(stock_obj, 'Shape') and stock_obj.Shape:
                    self.import_stats.update({
                        'volume': stock_obj.Shape.Volume,
                        'surface_area': stock_obj.Shape.Area,
                        'has_geometry': True
                    })
            except:
                self.import_stats['has_geometry'] = False
            
            self.log(f"✅ Stock imported and renamed: {stock_obj.Name}")
            return doc, stock_obj
                
        except ImportError:
            # Headless simulation mode
            self.log("🔧 Running in headless simulation mode...")
            return self._simulate_import(step_filename)
        
        except Exception as e:
            self.log(f"❌ Import failed: {e}")
            self.import_stats = {
                'error': str(e),
                'import_time': time.time() - import_start,
                'mode': 'failed',
                'source_file': step_filename
            }
            raise
    
    def _simulate_import(self, step_filename):
        """Simulate import process for testing/validation without FreeCAD"""
        self.log("🎭 Simulating STEP import process...")
        
        # Check if file exists
        step_path = Path(step_filename)
        if not step_path.is_absolute():
            # Look in boats directory structure
            search_paths = [
                self.project_path / "boats" / "MackenSea" / "output" / "stock" / step_filename,
                self.project_path / step_filename,
                step_filename
            ]
            
            step_path = None
            for candidate in search_paths:
                if Path(candidate).exists():
                    step_path = Path(candidate)
                    break
            
            if not step_path:
                raise FileNotFoundError(f"STEP file not found: {step_filename}")
        
        self.log(f"📊 STEP file found: {step_path}")
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Create mock document and object
        mock_doc = MockDocument("Cutout_Simulation")
        mock_stock = MockStockObject(name="stock", source_file=str(step_path))
        
        self.import_stats = {
            'object_name': mock_stock.Name,
            'object_type': 'MockStockObject',
            'import_time': 0.1,
            'mode': 'simulation',
            'source_file': str(step_path),
            'objects_imported': 1,
            'simulated': True
        }
        
        return mock_doc, mock_stock
    
    def save_document(self, doc, filepath=None):
        """Save document or export results in headless mode"""
        try:
            import FreeCAD as App
            
            if not filepath:
                filepath = self.project_path / f"{doc.Name}.FCStd"
            
            doc.saveAs(str(filepath))
            self.log(f"💾 Document saved: {filepath}")
            return str(filepath)
            
        except ImportError:
            # Export simulation results
            if not filepath:
                filepath = self.project_path / f"{doc.Name}_results.json"
            
            results = {
                'document_name': doc.Name,
                'import_stats': self.import_stats,
                'timestamp': time.time(),
                'mode': 'headless_simulation'
            }
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.log(f"💾 Results exported: {filepath}")
            return str(filepath)
    
    def get_import_summary(self):
        """Return import statistics and summary"""
        return {
            'stats': self.import_stats,
            'project_path': str(self.project_path),
            'timestamp': time.time()
        }


class MockDocument:
    """Mock FreeCAD document for headless operation"""
    def __init__(self, name):
        self.Name = name
        self.Objects = []
    
    def recompute(self):
        pass
    
    def saveAs(self, filepath):
        # In real implementation, could export to neutral format
        pass


class MockStockObject:
    """Mock stock object for headless simulation"""
    def __init__(self, name, **kwargs):
        self.Name = name
        self.properties = kwargs
    
    @property
    def Shape(self):
        return MockShape()


class MockShape:
    """Mock shape for headless simulation"""
    Volume = 1000000.0  # mm³
    Area = 50000.0      # mm²


def main():
    """Main function for headless execution"""
    print("🚀 Cutout Builder Core - Headless Mode")
    
    # Create builder instance
    builder = CutoutBuilderCore(verbose=True)
    
    # Validate environment
    errors, warnings = builder.validate_environment()
    
    for warning in warnings:
        print(f"⚠️  {warning}")
    
    if errors:
        for error in errors:
            print(f"❌ {error}")
        print("Cannot continue due to validation errors")
        return False
    
    try:
        # Look for a STEP file to import (example)
        step_file = "stock_example.step"  # You would specify the actual file
        
        # Import stock
        doc, stock_obj = builder.import_stock_step(step_file)
        
        # Save results
        output_file = builder.save_document(doc)
        
        # Print summary
        summary = builder.get_import_summary()
        print("\n📊 Import Summary:")
        for key, value in summary['stats'].items():
            print(f"   {key}: {value}")
        
        print(f"\n✅ Headless import completed successfully!")
        print(f"📁 Output: {output_file}")
        return True
        
    except Exception as e:
        print(f"💥 Headless import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)