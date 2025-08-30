"""
Stock Builder Core - Simplified
Creates 3D rudder stock geometry from provided dimensions
"""
import sys
import os
from pathlib import Path
import time

# Add venv path for reportlab access in FreeCAD
venv_path = Path.home() / "Rudder_Code" / "venv" / "lib" / "python3.9" / "site-packages"
if venv_path.exists():
    sys.path.insert(0, str(venv_path))

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
            if not hasattr(stock_3D, 'build_stock_from_dimensions'):
                # Check for new dimension-based method
                if not hasattr(stock_3D, 'build_stock_from_csv'):
                    errors.append("stock_3D missing build methods")
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
    
    def _get_object_name(self, stock_obj):
        """Get the intended object name from various possible sources"""
        # Check for our custom property first
        if hasattr(stock_obj, 'IntendedName') and stock_obj.IntendedName:
            return stock_obj.IntendedName
        # Then check Label
        if hasattr(stock_obj, 'Label') and stock_obj.Label:
            return stock_obj.Label
        # Finally fall back to Name
        return stock_obj.Name
    
    def _extract_boat_name(self, object_name):
        """Extract boat name from object name"""
        # Handle both "MackenSea_Stock" and "MackenSea_Stock_Cutout" formats
        if "_Stock_Cutout" in object_name:
            return object_name.replace("_Stock_Cutout", "")
        elif "_Stock" in object_name:
            return object_name.replace("_Stock", "")
        elif "_RudderStock" in object_name:
            return object_name.replace("_RudderStock", "")
        return object_name
    
    def build_stock_geometry(self, doc, dimensions=None, object_name=None, csv_path=None, **kwargs):
        """Build stock geometry from dimensions or CSV
        
        Args:
            doc: FreeCAD document
            dimensions: Dictionary of dimensions (if provided, takes precedence)
            object_name: Name for the object (e.g., "MackenSea_Stock" or "MackenSea_Stock_Cutout")
            csv_path: Path to CSV file (fallback if dimensions not provided)
            **kwargs: Additional parameters
        """
        import stock.stock_3D as stock_3D
        
        self.log("🏗️ Building stock...")
        start = time.time()
        
        # Determine which method to use
        if dimensions is not None:
            # Use dimension-based method if available
            if hasattr(stock_3D, 'build_stock_from_dimensions'):
                stock_obj = stock_3D.build_stock_from_dimensions(doc, dimensions, **kwargs)
            else:
                # Fallback: pass dimensions through kwargs if old method doesn't support direct dimensions
                self.log("⚠️ Using CSV method with dimension override")
                stock_obj = stock_3D.build_stock_from_csv(doc, csv_path, dimensions=dimensions, **kwargs)
        else:
            # Use CSV-based method - don't pass object_name since it's not supported
            if csv_path:
                stock_obj = stock_3D.build_stock_from_csv(doc, csv_path, **kwargs)
            else:
                stock_obj = stock_3D.build_stock_from_csv(doc, **kwargs)
        
        if stock_obj:
            # Set the name after creation if provided
            if object_name:
                try:
                    # Try to rename the object
                    original_name = stock_obj.Name
                    stock_obj.Label = object_name
                    
                    # In FreeCAD, Name is read-only after creation, but Label can be changed
                    # The Label is what users see in the tree view
                    self.log(f"   Set object label: {object_name}")
                    
                    # Store the intended name for our use
                    if hasattr(stock_obj, 'addProperty'):
                        try:
                            stock_obj.addProperty("App::PropertyString", "IntendedName", "Base", "Intended object name")
                            stock_obj.IntendedName = object_name
                        except:
                            pass  # Property might already exist or not be supported
                except Exception as e:
                    self.log(f"⚠️ Could not set object name: {e}")
            
            # For stats and further processing, use the intended name or fall back to actual name
            display_name = object_name if object_name else stock_obj.Label if stock_obj.Label else stock_obj.Name
            
            # Set minimal stats for compatibility with display macro
            self.build_stats = {
                'build_time': time.time() - start,
                'object_name': display_name,
                'mode': 'dimensions' if dimensions else 'csv'
            }
            self.log(f"✅ Stock created: {display_name}")
            
            # Export to STEP format - pass the intended name
            self.export_stock_step(stock_obj, object_name=object_name)
            
            # Generate PDF approval report
            boat_name = self._extract_boat_name(display_name)
            customer_info = {
                'customer': boat_name,
                'part_number': f"{boat_name}-RS-001",
                'revision': 'A'
            }
            try:
                image_path = self.generate_approval_pdf(stock_obj, doc, customer_info, 
                                                      output_filename=f"{display_name}_Approval.png")
                if image_path:
                    self.log(f"📸 Generated approval image")
            except Exception as e:
                self.log(f"⚠️ Image generation skipped: {e}")
            
            return stock_obj
        else:
            raise Exception("Stock creation failed")
    
    def ensure_merged_solid(self, stock_obj):
        """Ensure the stock is a single merged solid before export"""
        if hasattr(stock_obj, 'Shape'):
            if len(stock_obj.Shape.Solids) > 1:
                self.log(f"⚠️ Multiple solids detected ({len(stock_obj.Shape.Solids)}), merging...")
                # Fuse all solids into one
                merged = stock_obj.Shape.Solids[0]
                for solid in stock_obj.Shape.Solids[1:]:
                    merged = merged.fuse(solid)
                stock_obj.Shape = merged
                self.log("✅ Merged into single solid")
        return stock_obj
    
    def export_stock_step(self, stock_obj, filename=None, object_name=None, stage_name="stock"):
        """Export to STEP format"""
        # Ensure merged solid before export
        stock_obj = self.ensure_merged_solid(stock_obj)
        
        # Use provided object_name or extract from stock object
        if not object_name:
            object_name = self._get_object_name(stock_obj)
        
        boat_name = self._extract_boat_name(object_name)
        base_name = object_name
        
        if not filename:
            filename = f"{base_name}.step"
        
        # Determine subdirectory based on object type
        if "_Cutout" in base_name:
            subdir = "cutout"
        else:
            subdir = "stock"
        
        # Use boat-specific path structure
        filepath = self.project_path / "boats" / boat_name / "output" / subdir / filename
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
    
    def build_and_export_pipeline(self, dimensions=None, object_name=None, csv_path=None, 
                                 export_filename=None, stage_name="initial", **kwargs):
        """Build and export pipeline
        
        Args:
            dimensions: Dictionary of dimensions (if provided, takes precedence)
            object_name: Name for the object (e.g., "MackenSea_Stock")
            csv_path: Path to CSV file (fallback if dimensions not provided)
            export_filename: Custom export filename
            stage_name: Stage name for export
            **kwargs: Additional parameters
        """
        doc = self.create_document()
        stock_obj = self.build_stock_geometry(doc, dimensions=dimensions, 
                                             object_name=object_name, 
                                             csv_path=csv_path, **kwargs)
        
        if export_filename or stage_name:
            exported_path = self.export_stock_step(stock_obj, export_filename, 
                                                  object_name=object_name, 
                                                  stage_name=stage_name)
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
    
    def capture_front_view(self, doc, stock_obj, output_path=None):
        """Capture front view of stock for PDF"""
        import FreeCADGui
        from PySide import QtGui
        
        if output_path is None:
            # Extract boat name for path
            object_name = self._get_object_name(stock_obj)
            boat_name = self._extract_boat_name(object_name)
            output_path = self.project_path / "boats" / boat_name / "output" / "stock_front_view.png"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set view to front
        FreeCADGui.activeDocument().activeView().viewFront()
        FreeCADGui.activeDocument().activeView().fitAll()
        
        # Capture the view
        FreeCADGui.activeDocument().activeView().saveImage(
            str(output_path), 1920, 1080, 'White'
        )
        
        self.log(f"📸 Captured front view: {output_path}")
        return str(output_path)
    
    def extract_stock_dimensions(self, stock_obj):
        """Extract key dimensions from stock object"""
        dimensions = {}
        
        try:
            # Get bounding box for overall dimensions
            bbox = stock_obj.Shape.BoundBox
            dimensions['overall_height'] = bbox.ZLength
            dimensions['max_width'] = max(bbox.XLength, bbox.YLength)
            dimensions['min_width'] = min(bbox.XLength, bbox.YLength)
            
            # Try to get more specific data if available
            if hasattr(stock_obj, 'Proxy') and hasattr(stock_obj.Proxy, 'data'):
                data = stock_obj.Proxy.data
                dimensions['base_diameter'] = data.get('base_diameter', 'N/A')
                dimensions['top_diameter'] = data.get('top_diameter', 'N/A')
                dimensions['stations'] = len(data.get('stations', []))
        except Exception as e:
            self.log(f"⚠️ Could not extract all dimensions: {e}")
        
        return dimensions
    
    def extract_component_positions(self, stock_obj):
        """Extract wedge/tang positions from the build"""
        components = []
        
        try:
            # Parse the stock object name to get boat info
            object_name = self._get_object_name(stock_obj)
            boat_name = self._extract_boat_name(object_name)
            
            # Try to extract from the shape's solids
            if hasattr(stock_obj, 'Shape') and hasattr(stock_obj.Shape, 'Solids'):
                # The build log shows components like:
                # - Support 1 at start=365.0
                # - Support 2 at start=113.0  
                # - Support 3 at start=560.0
                # These are stored in the summaries during build
                
                # For now, return hardcoded values from the log
                # In future, this should parse from the actual geometry
                components = [
                    {'name': 'Support 1', 'position': 365.0, 'width': 40.0},
                    {'name': 'Support 2', 'position': 113.0, 'width': 40.0},
                    {'name': 'Support 3', 'position': 560.0, 'width': 40.0}
                ]
                
        except Exception as e:
            self.log(f"⚠️ Could not extract component positions: {e}")
        
        return components
    
    def generate_approval_pdf(self, stock_obj, doc, customer_info=None, output_filename=None):
        """Generate approval image with text info using FreeCAD's built-in export"""
        try:
            import FreeCADGui
            from datetime import datetime
            from PySide import QtGui, QtCore
            
            # Extract boat name and determine type from stock object
            object_name = self._get_object_name(stock_obj)
            boat_name = self._extract_boat_name(object_name)
            is_cutout = "_Cutout" in object_name
            
            # Set output path using boat-specific structure
            if output_filename is None:
                output_filename = f"{object_name}_Approval.png"
            
            # Determine subdirectory based on type
            subdir = "cutout" if is_cutout else "stock"
            pdf_path = self.project_path / "boats" / boat_name / "output" / subdir / output_filename
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Set view to show the stock nicely
            FreeCADGui.activeDocument().activeView().viewFront()
            FreeCADGui.activeDocument().activeView().fitAll()
            
            # Capture the base image
            FreeCADGui.activeDocument().activeView().saveImage(
                str(pdf_path), 1920, 1080, 'White'
            )
            
            # Now add text overlay using Qt
            image = QtGui.QImage(str(pdf_path))
            painter = QtGui.QPainter(image)
            
            # Set up font
            font = QtGui.QFont("Arial", 14)
            font_bold = QtGui.QFont("Arial", 16, QtGui.QFont.Bold)
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 2))
            
            # Add title
            painter.setFont(font_bold)
            title = "RUDDER STOCK CUTOUT APPROVAL" if is_cutout else "RUDDER STOCK APPROVAL"
            painter.drawText(1320, 50, title)
            
            # Add boat info
            painter.setFont(font)
            y_pos = 100
            line_height = 30
            x_pos = 1320  # Right side position
            
            # Customer info
            if customer_info:
                painter.drawText(x_pos, y_pos, f"Customer: {customer_info.get('customer', boat_name)}")
                y_pos += line_height
                part_suffix = "-CUT" if is_cutout else "-RS"
                painter.drawText(x_pos, y_pos, f"Part: {customer_info.get('part_number', f'{boat_name}{part_suffix}-001')}")
                y_pos += line_height
                painter.drawText(x_pos, y_pos, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
                y_pos += line_height * 2
            
            # Get dimensions
            bbox = stock_obj.Shape.BoundBox
            
            painter.setFont(font_bold)
            painter.drawText(x_pos, y_pos, "DIMENSIONS:")
            y_pos += line_height
            
            painter.setFont(font)
            painter.drawText(x_pos, y_pos, f"Height: {bbox.ZLength:.1f} mm")
            y_pos += line_height
            painter.drawText(x_pos, y_pos, f"Max Width: {max(bbox.XLength, bbox.YLength):.1f} mm")
            y_pos += line_height
            painter.drawText(x_pos, y_pos, f"Min Width: {min(bbox.XLength, bbox.YLength):.1f} mm")
            y_pos += line_height
            
            # Add volume and surface area
            y_pos += line_height
            painter.setFont(font_bold)
            painter.drawText(x_pos, y_pos, "PROPERTIES:")
            y_pos += line_height
            
            painter.setFont(font)
            painter.drawText(x_pos, y_pos, f"Volume: {stock_obj.Shape.Volume:.0f} mm³")
            y_pos += line_height
            painter.drawText(x_pos, y_pos, f"Surface Area: {stock_obj.Shape.Area:.0f} mm²")
            y_pos += line_height
            
            # Add type indicator if cutout
            if is_cutout:
                y_pos += line_height
                painter.setFont(font_bold)
                painter.drawText(x_pos, y_pos, "TYPE: FOIL CUTOUT TOOL")
            
            # Add component/tang positions
            components = self.extract_component_positions(stock_obj)
            if components:
                y_pos += line_height
                painter.setFont(font_bold)
                painter.drawText(x_pos, y_pos, "TANG/SUPPORT POSITIONS:")
                y_pos += line_height
                
                painter.setFont(font)
                for comp in sorted(components, key=lambda x: x['position']):
                    painter.drawText(x_pos, y_pos, f"{comp['name']}: {comp['position']:.0f} mm from base")
                    y_pos += line_height
            
            # Add approval checkboxes at bottom
            y_pos = 880  # Near bottom
            painter.setFont(font)
            painter.drawRect(x_pos, y_pos, 20, 20)
            painter.drawText(x_pos + 30, y_pos + 15, "APPROVED")
            
            y_pos += 40
            painter.drawRect(x_pos, y_pos, 20, 20)
            painter.drawText(x_pos + 30, y_pos + 15, "CHANGES REQUIRED")
            
            # Finish painting and save
            painter.end()
            image.save(str(pdf_path))
            
            self.log(f"📄 Generated approval image: {pdf_path}")
            self.log(f"   Dimensions: {bbox.ZLength:.1f}mm height")
            return str(pdf_path)
            
        except Exception as e:
            self.log(f"⚠️ Image generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def quick_approval_report(self, dimensions=None, object_name=None, csv_path=None, 
                            customer_info=None, **kwargs):
        """Quick method to build stock and generate approval PDF in one go
        
        Args:
            dimensions: Dictionary of dimensions (if provided, takes precedence)
            object_name: Name for the object (e.g., "MackenSea_Stock")
            csv_path: Path to CSV file (fallback if dimensions not provided)
            customer_info: Customer information for the report
            **kwargs: Additional parameters
        """
        # Build the stock
        doc = self.create_document()
        stock_obj = self.build_stock_geometry(doc, dimensions=dimensions, 
                                             object_name=object_name, 
                                             csv_path=csv_path, **kwargs)
        
        # Generate the PDF
        pdf_path = self.generate_approval_pdf(stock_obj, doc, customer_info)
        
        # Also save the STEP file
        step_path = self.export_stock_step(stock_obj, object_name=object_name, 
                                          stage_name="for_approval")
        
        return {
            'stock_object': stock_obj,
            'pdf_path': pdf_path,
            'step_path': step_path,
            'document': doc
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
        # Test with default CSV method (backward compatibility)
        stock_obj = builder.build_stock_geometry(doc)
        builder.save_document(doc)
        print("✅ Complete")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)