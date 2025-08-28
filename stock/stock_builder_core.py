"""
Stock Builder Core - Simplified
Creates 3D rudder stock geometry
"""
import sys
import os
from pathlib import Path
import time
import FreeCAD as App
import Part

# Add project root
project = Path.home() / "Rudder_Code"
if project.exists():
   sys.path.insert(0, str(project))

class StockBuilderCore:
   """Core stock building functionality"""
   
   def __init__(self, project_path=None, verbose=True):
       self.project_path = Path(project_path) if project_path else project
       self.verbose = verbose
       self.step_handler = None
       self.build_stats = {}  # Initialize for compatibility
       
       # Try to import STEP helper
       try:
           from helpers.step_save_load import StepHandler
           self.step_handler = StepHandler()
       except:
           pass
   
   def log(self, message):
       if self.verbose:
           print(message)
   
   def validate_environment(self):
       """Basic validation"""
       errors = []
       warnings = []
       
       if not self.project_path.exists():
           errors.append(f"Project directory not found: {self.project_path}")
       
       try:
           import stock.stock_3D as stock_3D
           if not hasattr(stock_3D, 'build_stock_from_csv'):
               errors.append("stock_3D missing build_stock_from_csv")
       except ImportError as e:
           errors.append(f"Cannot import stock_3D: {e}")
       
       if not self.step_handler:
           warnings.append("STEP helper not available")
       
       return errors, warnings
   
   def create_document(self, doc_name="Stock_3D_Build", clear_existing=True):
       """Create or reuse FreeCAD document"""
       if doc_name in App.listDocuments():
           doc = App.getDocument(doc_name)
           if clear_existing:
               for obj in doc.Objects:
                   try:
                       doc.removeObject(obj.Name)
                   except:
                       pass
       else:
           doc = App.newDocument(doc_name)
       
       self.log(f"📄 Document: {doc_name}")
       return doc
   
   def build_stock_geometry(self, doc, csv_path=None, **kwargs):
       """Build stock geometry"""
       import stock.stock_3D as stock_3D
       
       self.log("🏗️ Building stock...")
       start = time.time()
       
       if csv_path:
           stock_obj = stock_3D.build_stock_from_csv(doc, csv_path, **kwargs)
       else:
           stock_obj = stock_3D.build_stock_from_csv(doc, **kwargs)
       
       if stock_obj:
           # Set minimal stats for compatibility with display macro
           self.build_stats = {
               'build_time': time.time() - start,
               'object_name': stock_obj.Name,
               'mode': 'freecad'
           }
           self.log(f"✅ Stock created: {stock_obj.Name}")
           return stock_obj
       else:
           raise Exception("Stock creation failed")
   
   def export_stock_step(self, stock_obj, filename=None, stage_name="stock"):
       """Export to STEP format"""
       if not filename:
           filename = f"{stage_name}_{stock_obj.Name}.step"
       
       filepath = self.project_path / "output" / filename
       filepath.parent.mkdir(parents=True, exist_ok=True)
       
       Part.export([stock_obj], str(filepath))
       self.log(f"📤 Exported: {filepath}")
       return str(filepath)
   
   def import_stock_step(self, filename, doc_name=None):
       """Import STEP file"""
       if not doc_name:
           doc_name = "Imported_Stock"
       
       doc = self.create_document(doc_name)
       shape = Part.read(str(filename))
       
       stock_obj = doc.addObject("Part::Feature", "ImportedStock")
       stock_obj.Shape = shape
       
       self.log(f"📥 Imported: {stock_obj.Name}")
       return doc, stock_obj
   
   def build_and_export_pipeline(self, csv_path=None, export_filename=None, stage_name="initial", **kwargs):
       """Build and export pipeline"""
       doc = self.create_document()
       stock_obj = self.build_stock_geometry(doc, csv_path, **kwargs)
       
       if export_filename or stage_name:
           exported_path = self.export_stock_step(stock_obj, export_filename, stage_name)
           return stock_obj, exported_path
       
       return stock_obj, None
   
   def import_and_process_pipeline(self, step_filename, processing_func=None, export_result=True, stage_name="processed"):
       """Import and process pipeline"""
       doc, stock_obj = self.import_stock_step(step_filename)
       
       if processing_func:
           processed_obj = processing_func(stock_obj, doc)
       else:
           processed_obj = stock_obj
       
       if export_result:
           exported_path = self.export_stock_step(processed_obj, stage_name=stage_name)
           return processed_obj, exported_path
       
       return processed_obj, None
   
   def save_document(self, doc, filepath=None):
       """Save document"""
       if not filepath:
           filepath = self.project_path / f"{doc.Name}.FCStd"
       
       doc.saveAs(str(filepath))
       self.log(f"💾 Saved: {filepath}")
       return str(filepath)
   
   def get_build_summary(self):
       """Return summary with stats for compatibility"""
       return {
           'project_path': str(self.project_path),
           'stats': self.build_stats
       }

def main():
   """Simple test"""
   builder = StockBuilderCore()
   errors, warnings = builder.validate_environment()
   
   if errors:
       for e in errors:
           print(f"❌ {e}")
       return False
   
   try:
       doc = builder.create_document()
       stock_obj = builder.build_stock_geometry(doc)
       builder.save_document(doc)
       print("✅ Complete")
       return True
   except Exception as e:
       print(f"❌ Failed: {e}")
       return False

if __name__ == "__main__":
   sys.exit(0 if main() else 1)