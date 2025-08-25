"""
Import/Export Helper Module
Reusable file I/O operations for FreeCAD documents and objects
Located in: ~/Rudder_Code/stock/import_export.py
"""
import os
from pathlib import Path
import json
import time

class ImportExportHelper:
    """Helper class for FreeCAD file operations"""
    
    def __init__(self, boat_name=None, project_path=None, verbose=True):
        self.boat_name = boat_name or "MackenSea"
        self.project_path = Path(project_path) if project_path else Path.home() / "Rudder_Code"
        self.verbose = verbose
        self.last_operation = {}
        
    def log(self, message):
        """Conditional logging"""
        if self.verbose:
            print(message)
    
    def find_stock_files(self, pattern=None):
        """Find stock files for specific boat"""
        if not pattern:
            # boats/{boat_name}/output/stock/{boat_name}Stock.step
            stock_file = self.project_path / "boats" / self.boat_name / "output" / "stock" / f"{self.boat_name}Stock.step"
            return [stock_file] if stock_file.exists() else []
        
        # Fallback pattern search if needed
        stock_files = []
        search_path = self.project_path / "boats" / self.boat_name / "output" / "stock"
        
        if search_path.exists():
            files = list(search_path.glob(pattern))
            stock_files.extend(files)
        
        return stock_files
    
    def import_freecad_document(self, filepath=None, doc_name=None):
        """Import STEP file with error handling"""
        start_time = time.time()
        
        try:
            import FreeCAD as App
            import Import
            
            # Auto-find stock STEP file if not specified
            if not filepath:
                stock_files = self.find_stock_files()
                if not stock_files:
                    raise FileNotFoundError(f"No stock files found for boat: {self.boat_name}")
                filepath = stock_files[0]
                self.log(f"📁 Auto-selected file: {filepath.name}")
            
            filepath = Path(filepath)
            if not filepath.exists():
                raise FileNotFoundError(f"File not found: {filepath}")
            
            self.log(f"📥 Importing STEP: {filepath}")
            
            # Create new document
            if not doc_name:
                doc_name = f"Imported_{self.boat_name}_Stock"
            
            doc = App.newDocument(doc_name)
            
            # Import the STEP file
            Import.insert(str(filepath), doc.Name)
            
            # Collect import statistics
            self.last_operation = {
                'operation': 'import_step',
                'filepath': str(filepath),
                'doc_name': doc.Name,
                'boat_name': self.boat_name,
                'object_count': len(doc.Objects),
                'file_size': filepath.stat().st_size,
                'import_time': time.time() - start_time,
                'success': True
            }
            
            self.log(f"✅ Imported STEP document: {doc.Name}")
            self.log(f"📦 Objects imported: {len(doc.Objects)}")
            
            return doc
            
        except ImportError:
            # Mock import for headless mode
            return self._mock_import(filepath, doc_name)
        except Exception as e:
            self.last_operation = {
                'operation': 'import_step',
                'error': str(e),
                'import_time': time.time() - start_time,
                'success': False
            }
            self.log(f"❌ STEP import failed: {e}")
            raise
    
    def export_freecad_document(self, doc, filepath=None, name_prefix="stock_mold"):
        """Export FreeCAD document with error handling"""
        start_time = time.time()
        
        try:
            import FreeCAD as App
            
            # Generate output filepath if not provided
            if not filepath:
                # boats/{boat_name}/output/stock/{boat_name}Stock_Mold.FCStd
                output_dir = self.project_path / "boats" / self.boat_name / "output" / "stock"
                filename = f"{self.boat_name}Stock_Mold.FCStd"
                filepath = output_dir / filename
            
            filepath = Path(filepath)
            
            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            self.log(f"💾 Exporting to: {filepath}")
            
            # Save the document
            doc.saveAs(str(filepath))
            
            # Collect export statistics
            self.last_operation = {
                'operation': 'export',
                'filepath': str(filepath),
                'doc_name': doc.Name,
                'boat_name': self.boat_name,
                'object_count': len(doc.Objects),
                'file_size': filepath.stat().st_size if filepath.exists() else 0,
                'export_time': time.time() - start_time,
                'success': True
            }
            
            self.log(f"✅ Exported as: {filepath.name}")
            return str(filepath)
            
        except ImportError:
            # Mock export for headless mode
            return self._mock_export(doc, filepath, name_prefix)
        except Exception as e:
            self.last_operation = {
                'operation': 'export',
                'error': str(e),
                'export_time': time.time() - start_time,
                'success': False
            }
            self.log(f"❌ Export failed: {e}")
            raise
    
    def list_document_objects(self, doc):
        """List all objects in a document with details"""
        objects_info = []
        
        try:
            for obj in doc.Objects:
                obj_info = {
                    'name': obj.Name,
                    'type': type(obj).__name__,
                    'label': getattr(obj, 'Label', 'N/A')
                }
                
                # Try to get shape information
                if hasattr(obj, 'Shape') and obj.Shape:
                    try:
                        obj_info.update({
                            'volume': obj.Shape.Volume,
                            'surface_area': obj.Shape.Area,
                            'has_geometry': True
                        })
                    except:
                        obj_info['has_geometry'] = False
                
                objects_info.append(obj_info)
            
            return objects_info
            
        except Exception as e:
            self.log(f"⚠️  Could not list objects: {e}")
            return []
    
    def _mock_import(self, filepath, doc_name):
        """Mock import for headless mode"""
        self.log(f"🎭 Mock importing: {filepath}")
        
        # Create mock document
        mock_doc = MockDocument(doc_name or "MockImport")
        mock_doc.filepath = str(filepath) if filepath else "mock_file.FCStd"
        
        self.last_operation = {
            'operation': 'mock_import',
            'filepath': str(filepath) if filepath else "mock_file.FCStd",
            'doc_name': mock_doc.Name,
            'object_count': 1,
            'success': True,
            'mode': 'headless'
        }
        
        return mock_doc
    
    def _mock_export(self, doc, filepath, name_prefix):
        """Mock export for headless mode"""
        if not filepath:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filepath = self.project_path / f"{name_prefix}_{timestamp}.json"
        
        # Export document info as JSON
        export_data = {
            'document_name': doc.Name,
            'timestamp': time.time(),
            'mode': 'headless_mock',
            'objects': getattr(doc, 'Objects', [])
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.last_operation = {
            'operation': 'mock_export',
            'filepath': str(filepath),
            'success': True,
            'mode': 'headless'
        }
        
        self.log(f"🎭 Mock exported to: {filepath}")
        return str(filepath)
    
    def get_operation_summary(self):
        """Get summary of last operation"""
        return self.last_operation.copy()


class MockDocument:
    """Mock FreeCAD document for headless operation"""
    def __init__(self, name):
        self.Name = name
        self.Objects = [MockStockObject("MockStock")]
        self.filepath = None
    
    def saveAs(self, filepath):
        self.filepath = filepath


class MockStockObject:
    """Mock stock object"""
    def __init__(self, name):
        self.Name = name
        self.Label = name
        self.Shape = MockShape()


class MockShape:
    """Mock shape with basic properties"""
    Volume = 1000000.0
    Area = 50000.0


def main():
    """Test the import/export helper"""
    print("🧪 Testing Import/Export Helper")
    
    helper = ImportExportHelper()
    
    # Find available stock files
    stock_files = helper.find_stock_files()
    print(f"📁 Found {len(stock_files)} stock files:")
    for f in stock_files[:3]:  # Show first 3
        print(f"   {f.name}")
    
    try:
        # Test import
        if stock_files:
            doc = helper.import_freecad_document(stock_files[0])
            
            # List objects
            objects = helper.list_document_objects(doc)
            print(f"📦 Objects in document:")
            for obj in objects:
                print(f"   {obj['name']}: {obj['type']}")
            
            # Test export
            output_file = helper.export_freecad_document(doc, name_prefix="test_export")
            print(f"💾 Exported to: {output_file}")
        else:
            print("⚠️  No stock files found for testing")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Show operation summary
    summary = helper.get_operation_summary()
    print(f"\n📊 Last operation summary:")
    for key, value in summary.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    main()