"""
Stock Builder Core - Headless computation module
Pure business logic for building 3D rudder stock geometry without GUI dependencies
Can be run in headless mode, testing, or batch processing environments

This file goes in: ~/Rudder_Code/Stock/stock_builder_core.py
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
    # This file goes in: ~/Rudder_Code/Stock/stock_builder_core.py
else:
    print(f"⚠️  Warning: Project directory not found at {project}")

# Import the STEP helper
try:
    from helpers.step_save_load import save_step, load_step, StepHandler, StepFileError
except ImportError as e:
    print(f"⚠️  Warning: Could not import STEP helper: {e}")
    print("Make sure step_save_load.py is in ~/Rudder_Code/helpers/")

class StockBuilderCore:
    """Core stock building functionality without GUI dependencies"""
    
    def __init__(self, project_path=None, verbose=True):
        self.project_path = Path(project_path) if project_path else project
        self.verbose = verbose
        self.build_stats = {}
        
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
        
        # Check for stock module (now in same directory)
        try:
            import stock.stock_3D as stock_3D
            if not hasattr(stock_3D, 'build_stock_from_csv'):
                errors.append("stock_3D module missing 'build_stock_from_csv' function")
            else:
                self.log("✅ stock_3D module validated")
        except ImportError as e:
            errors.append(f"Cannot import stock_3D module: {e}")
            self.log("Make sure stock_3D.py is in ~/Rudder_Code/stock/ folder")
        
        # Check for STEP helper
        try:
            from helpers.step_save_load import save_step
            self.log("✅ STEP helper available")
        except ImportError:
            warnings.append("STEP helper not available - limited export functionality")
        
        return errors, warnings
    
    def create_document(self, doc_name="Stock_3D_Build", clear_existing=True):
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
    
    def build_stock_geometry(self, doc, csv_path=None, **kwargs):
        """Build stock geometry with comprehensive error handling"""
        build_start = time.time()
        
        try:
            # Try real FreeCAD first
            import FreeCAD as App
            import stock.stock_3D as stock_3D
            
            self.log("🏗️  Building stock geometry with FreeCAD...")
            
            # Allow custom CSV path or use module default
            if csv_path:
                stock_obj = stock_3D.build_stock_from_csv(doc, csv_path, **kwargs)
            else:
                stock_obj = stock_3D.build_stock_from_csv(doc, **kwargs)
            
            if stock_obj:
                # Collect build statistics
                self.build_stats = {
                    'object_name': stock_obj.Name,
                    'object_type': type(stock_obj).__name__,
                    'build_time': time.time() - build_start,
                    'mode': 'freecad'
                }
                
                # Try to get shape properties
                try:
                    if hasattr(stock_obj, 'Shape') and stock_obj.Shape:
                        self.build_stats.update({
                            'volume': stock_obj.Shape.Volume,
                            'surface_area': stock_obj.Shape.Area,
                            'has_geometry': True
                        })
                except:
                    self.build_stats['has_geometry'] = False
                
                self.log(f"✅ Stock object created: {stock_obj.Name}")
                return stock_obj
            else:
                raise Exception("Stock object creation returned None")
                
        except ImportError:
            # Headless simulation mode
            self.log("🔧 Running in headless simulation mode...")
            return self._simulate_build(csv_path, **kwargs)
        
        except Exception as e:
            self.log(f"❌ Build failed: {e}")
            self.build_stats = {
                'error': str(e),
                'build_time': time.time() - build_start,
                'mode': 'failed'
            }
            raise
    
    def export_stock_step(self, stock_obj, filename=None, stage_name="stock"):
        """
        Export stock object to STEP format using helper module
        
        Args:
            stock_obj: FreeCAD object to export
            filename: Optional custom filename
            stage_name: Stage identifier for auto-naming
        
        Returns:
            str: Path to exported file
        """
        if not self.step_handler:
            raise Exception("STEP helper not available - cannot export")
        
        # Auto-generate filename if not provided
        if not filename:
            timestamp = int(time.time())
            filename = f"{stage_name}_{stock_obj.Name}_{timestamp}.step"
        
        try:
            filepath = self.step_handler.save(stock_obj, filename)
            self.log(f"📤 Stock exported to: {filepath}")
            
            # Update build stats
            self.build_stats['exported_step'] = filepath
            self.build_stats['export_timestamp'] = time.time()
            
            return filepath
            
        except StepFileError as e:
            self.log(f"❌ Export failed: {e}")
            raise
    
    def import_stock_step(self, filename, doc_name=None):
        """
        Import STEP file for further processing
        
        Args:
            filename: STEP filename to import
            doc_name: Optional document name
        
        Returns:
            tuple: (document, imported_stock_object)
        """
        if not self.step_handler:
            raise Exception("STEP helper not available - cannot import")
        
        try:
            doc, imported_objects = self.step_handler.load(filename, doc_name)
            
            if not imported_objects:
                raise Exception("No objects were imported from STEP file")
            
            # Assume first object is the stock (or combine if multiple)
            stock_obj = imported_objects[0]
            
            self.log(f"📥 Stock imported: {stock_obj.Name}")
            self.log(f"📊 Total objects imported: {len(imported_objects)}")
            
            # Update build stats for imported geometry
            self.build_stats = {
                'object_name': stock_obj.Name,
                'object_type': type(stock_obj).__name__,
                'mode': 'imported',
                'imported_step': filename,
                'import_timestamp': time.time(),
                'objects_count': len(imported_objects)
            }
            
            return doc, stock_obj
            
        except StepFileError as e:
            self.log(f"❌ Import failed: {e}")
            raise
    
    def build_and_export_pipeline(self, csv_path=None, export_filename=None, stage_name="initial", **kwargs):
        """
        Complete pipeline: build geometry and export to STEP
        
        Returns:
            tuple: (stock_object, exported_filepath)
        """
        # Create document
        doc = self.create_document()
        
        # Build geometry
        stock_obj = self.build_stock_geometry(doc, csv_path, **kwargs)
        
        # Export to STEP
        if self.step_handler:
            exported_path = self.export_stock_step(stock_obj, export_filename, stage_name)
            return stock_obj, exported_path
        else:
            self.log("⚠️  STEP export skipped - helper not available")
            return stock_obj, None
    
    def import_and_process_pipeline(self, step_filename, processing_func=None, export_result=True, stage_name="processed"):
        """
        Complete pipeline: import STEP and apply processing function
        
        Args:
            step_filename: Input STEP file
            processing_func: Function to modify the imported object
            export_result: Whether to export the processed result
            stage_name: Stage name for export file naming
        
        Returns:
            tuple: (processed_object, exported_filepath_or_none)
        """
        # Import STEP file
        doc, stock_obj = self.import_stock_step(step_filename)
        
        # Apply processing if provided
        if processing_func:
            self.log(f"🔄 Applying processing function...")
            processed_obj = processing_func(stock_obj, doc)
        else:
            processed_obj = stock_obj
        
        # Export processed result
        exported_path = None
        if export_result and self.step_handler:
            exported_path = self.export_stock_step(processed_obj, stage_name=stage_name)
        
        return processed_obj, exported_path
    
    def _simulate_build(self, csv_path=None, **kwargs):
        """Simulate build process for testing/validation without FreeCAD"""
        import csv
        
        self.log("🎭 Simulating stock build process...")
        
        # Look for CSV file in expected locations
        csv_candidates = [
            csv_path,
            self.project_path / "data" / "stock_data.csv",
            self.project_path / "stock_data.csv",
            "stock_data.csv"
        ]
        
        csv_file = None
        for candidate in csv_candidates:
            if candidate and Path(candidate).exists():
                csv_file = Path(candidate)
                break
        
        if not csv_file:
            raise FileNotFoundError("No CSV file found for simulation")
        
        # Read and validate CSV structure
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.log(f"📊 CSV loaded: {len(rows)} data points from {csv_file}")
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Create mock results
        mock_result = MockStockObject(
            name="Stock_Simulation",
            csv_file=str(csv_file),
            data_points=len(rows),
            **kwargs
        )
        
        self.build_stats = {
            'object_name': mock_result.Name,
            'object_type': 'MockStockObject',
            'build_time': 0.1,
            'mode': 'simulation',
            'csv_file': str(csv_file),
            'data_points': len(rows),
            'simulated': True
        }
        
        return mock_result
    
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
                'build_stats': self.build_stats,
                'timestamp': time.time(),
                'mode': 'headless_simulation'
            }
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.log(f"💾 Results exported: {filepath}")
            return str(filepath)
    
    def get_build_summary(self):
        """Return build statistics and summary"""
        return {
            'stats': self.build_stats,
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
    """Main function for headless execution with STEP export example"""
    print("🚀 Stock Builder Core - Headless Mode")
    
    # Create builder instance
    builder = StockBuilderCore(verbose=True)
    
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
        # Example 1: Basic build and save
        print("\n📋 Example 1: Basic build and FCStd save")
        doc = builder.create_document("Stock_Example_1")
        stock_obj = builder.build_stock_geometry(doc)
        output_file = builder.save_document(doc)
        
        # Example 2: Build and export to STEP
        if builder.step_handler:
            print("\n📋 Example 2: Build and export to STEP")
            try:
                step_file = builder.export_stock_step(stock_obj, stage_name="example")
                print(f"📤 STEP exported: {step_file}")
            except Exception as e:
                print(f"⚠️  STEP export failed: {e}")
        
        # Example 3: Complete pipeline
        if builder.step_handler:
            print("\n📋 Example 3: Complete build-and-export pipeline")
            try:
                pipeline_obj, pipeline_step = builder.build_and_export_pipeline(
                    stage_name="pipeline_test"
                )
                print(f"🔄 Pipeline completed: {pipeline_step}")
            except Exception as e:
                print(f"⚠️  Pipeline failed: {e}")
        
        # Print summary
        summary = builder.get_build_summary()
        print("\n📊 Build Summary:")
        for key, value in summary['stats'].items():
            print(f"   {key}: {value}")
        
        print(f"\n✅ Headless execution completed successfully!")
        return True
        
    except Exception as e:
        print(f"💥 Headless build failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Example processing function for import pipeline
def example_processing_function(stock_obj, doc):
    """
    Example function to modify imported stock object
    This would be replaced with your actual processing logic
    """
    try:
        import FreeCAD as App
        
        # Example: Scale the object
        if hasattr(stock_obj, 'Shape'):
            print(f"🔧 Processing object: {stock_obj.Name}")
            # Add your modification logic here
            # For example: create fillets, add features, etc.
            
        return stock_obj
        
    except ImportError:
        print("🎭 Mock processing applied")
        return stock_obj


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)