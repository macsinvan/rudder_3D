"""
Stock Builder Core - Clean Architecture
Reads CSV once, builds everything from dimensions
"""
import sys
from pathlib import Path
import time

# Add venv path for reportlab access in FreeCAD
venv_path = Path.home() / "Rudder_Code" / "venv" / "lib" / "python3.9" / "site-packages"
if venv_path.exists():
    sys.path.insert(0, str(venv_path))

import FreeCAD as App
import Part
from PySide2 import QtWidgets

# Add project root
project = Path.home() / "Rudder_Code"
if project.exists():
    sys.path.insert(0, str(project))

# Import modules
from stock.wedge_cutout_calc import create_wedge_cutout_dimensions
from stock.csv_dimension_parser import CSVDimensionParser
from stock.approval_report_generator import ApprovalReportGenerator
from helpers.step_handler import StepHandler


class StockBuilderCore:
    """Core stock building functionality - coordinates the build process"""
    
    def __init__(self, project_path=None, verbose=True):
        self.project_path = Path(project_path) if project_path else project
        self.verbose = verbose
        self.build_stats = {}
        
        # Initialize handlers
        self.report_generator = ApprovalReportGenerator(self.project_path, self.verbose)
        self.step_handler = StepHandler(verbose=self.verbose)
    
    def log(self, message):
        if self.verbose:
            print(message)
    
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
        if hasattr(stock_obj, 'IntendedName') and stock_obj.IntendedName:
            return stock_obj.IntendedName
        if hasattr(stock_obj, 'Label') and stock_obj.Label:
            return stock_obj.Label
        return stock_obj.Name
    
    def _extract_boat_name(self, object_name):
        """Extract boat name from object name"""
        if "_Stock_Cutout" in object_name:
            return object_name.replace("_Stock_Cutout", "")
        elif "_Stock" in object_name:
            return object_name.replace("_Stock", "")
        elif "_RudderStock" in object_name:
            return object_name.replace("_RudderStock", "")
        return object_name
    
    def get_csv_path(self):
        """Get CSV path from user via file dialog"""
        dlg = QtWidgets.QFileDialog()
        dlg.setWindowTitle("Select Stock CSV")
        dlg.setNameFilter("CSV files (*.csv)")
        dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        
        if dlg.exec_():
            csv_path = dlg.selectedFiles()[0]
            self.log(f"📁 User selected: {csv_path}")
            return csv_path
        else:
            raise ValueError("No CSV file selected")
    
    def add_perforation_cylinders(self, cutout_obj, doc, dimensions):
        """
        Add perforation cylinders to the rudder post section of the cutout
        
        Args:
            cutout_obj: The cutout object to modify
            doc: FreeCAD document
            dimensions: Dictionary containing stock dimensions
        
        Returns:
            Modified cutout object with perforation cylinders
        """
        self.log("🔧 Adding perforation cylinders to cutout...")
        
        try:
            # Get the shape of the cutout
            if hasattr(cutout_obj, 'Shape'):
                cutout_shape = cutout_obj.Shape
            else:
                self.log("⚠️ Cutout object has no Shape attribute")
                return cutout_obj
            
            # Parameters for perforation cylinders
            cylinder_diameter = 5.0  # mm
            cylinder_radius = cylinder_diameter / 2.0
            cylinder_length = 100.0  # mm
            vertical_spacing = 15.0  # mm between centers
            
            # Get post dimensions from the dimensions dict
            # From CSV: post goes from 0 to 604mm (in Z going negative)
            post_end_z = dimensions.get('post_end_mm', 604.0)  # End of post from CSV
            
            # Starting position: 30mm down from top (top is at Z=0, so start at Z=-30)
            start_z = -30.0  # Start 30mm below top
            
            # Calculate number of cylinders that fit along the post
            # Leave some margin at the bottom
            end_z = -post_end_z + 30.0  # Stop 30mm before bottom
            usable_length = abs(start_z - end_z)
            num_cylinders = int(usable_length / vertical_spacing) + 1
            
            # Create list to hold all cylinder shapes
            cylinder_shapes = []
            
            self.log(f"   Post length: {post_end_z}mm")
            self.log(f"   Starting perforations at Z={start_z}mm")
            self.log(f"   Creating {num_cylinders} perforation levels")
            
            # Create cylinders at each vertical position
            for i in range(num_cylinders):
                z_position = start_z - (i * vertical_spacing)  # Going down (more negative)
                
                # Skip if we're getting too close to the bottom
                if z_position < end_z:
                    break
                
                # Create cylinders starting from center (0,0) going outward
                # X direction (negative only)
                cyl_x = Part.makeCylinder(
                    cylinder_radius,
                    cylinder_length,
                    App.Vector(0, 0, z_position),  # Start at center
                    App.Vector(-1, 0, 0)  # Direction: negative X
                )
                cylinder_shapes.append(cyl_x)
                
                # Y direction (positive)
                cyl_y_pos = Part.makeCylinder(
                    cylinder_radius,
                    cylinder_length,
                    App.Vector(0, 0, z_position),  # Start at center
                    App.Vector(0, 1, 0)  # Direction: positive Y
                )
                cylinder_shapes.append(cyl_y_pos)
                
                # Y direction (negative)
                cyl_y_neg = Part.makeCylinder(
                    cylinder_radius,
                    cylinder_length,
                    App.Vector(0, 0, z_position),  # Start at center
                    App.Vector(0, -1, 0)  # Direction: negative Y
                )
                cylinder_shapes.append(cyl_y_neg)
            
            self.log(f"   Created {len(cylinder_shapes)} perforation cylinders")
            
            # Combine all cylinders into one compound
            if cylinder_shapes:
                cylinders_compound = Part.makeCompound(cylinder_shapes)
                
                # Fuse the cylinders with the cutout shape
                self.log("   Fusing cylinders with cutout...")
                modified_shape = cutout_shape.fuse(cylinders_compound)
                
                # Create a new object with the modified shape
                modified_obj = doc.addObject("Part::Feature", "ModifiedCutout")
                modified_obj.Shape = modified_shape
                modified_obj.Label = cutout_obj.Label if hasattr(cutout_obj, 'Label') else "Modified_Cutout"
                
                # Copy properties from original to modified
                if hasattr(cutout_obj, 'IntendedName'):
                    try:
                        modified_obj.addProperty("App::PropertyString", "IntendedName", 
                                               "Base", "Intended object name")
                        modified_obj.IntendedName = cutout_obj.IntendedName
                    except:
                        pass
                
                # Remove original cutout object
                try:
                    doc.removeObject(cutout_obj.Name)
                except:
                    pass
                
                self.log("✅ Successfully added perforation cylinders")
                return modified_obj
            else:
                self.log("⚠️ No cylinders created")
                return cutout_obj
                
        except Exception as e:
            self.log(f"⚠️ Error adding perforation cylinders: {e}")
            return cutout_obj
    
    def build(self, doc=None, csv_path=None, cutout_tolerance_mm=None, **kwargs):
        """
        Main build method - builds stock and optionally cutout based on style
        
        Args:
            doc: FreeCAD document (creates one if not provided)
            csv_path: Path to CSV file (shows dialog if not provided)
            cutout_tolerance_mm: Tolerance for cutout in mm (overrides CSV value if provided)
            **kwargs: Additional parameters passed to stock_3D
        
        Returns:
            Dictionary with:
                - 'stock': stock object (always present)
                - 'cutout': cutout object (present only for wedge style)
                - 'boat_name': extracted boat name
                - 'style': detected style
                - 'stats': build statistics
        """
        # Create document if not provided
        if doc is None:
            doc = self.create_document()
        
        results = {
            'stock': None,
            'cutout': None,
            'boat_name': 'Unknown',
            'style': 'unknown',
            'stats': {}
        }
        
        overall_start = time.time()
        
        # Step 1: Get CSV path if not provided
        if csv_path is None:
            csv_path = self.get_csv_path()
        
        # Step 2: Read CSV once and get dimensions
        self.log("📖 Reading CSV and extracting dimensions...")
        parser = CSVDimensionParser()
        dimensions = parser.parse_csv_file(csv_path)
        
        results['boat_name'] = dimensions.get('boat_name', 'Unknown')
        results['style'] = parser.get_stock_style()
        
        # Get cutout tolerance from CSV or use provided value or default
        if cutout_tolerance_mm is None:
            cutout_tolerance_mm = dimensions.get('cutout_mm', 2.0)
        
        self.log(f"   Boat: {results['boat_name']}")
        self.log(f"   Style: {results['style']}")
        if results['style'] == 'wedge':
            self.log(f"   Cutout tolerance: {cutout_tolerance_mm}mm")
        
        # Step 3: Build stock from dimensions
        self.log("\n" + "="*60)
        self.log("PASS 1: Building Stock")
        self.log("="*60)
        
        stock_name = f"{results['boat_name']}_Stock"
        stock_obj = self._build_single_object(doc, dimensions, stock_name, **kwargs)
        results['stock'] = stock_obj
        
        # Step 4: If wedge style, modify dimensions and build cutout
        if results['style'] == 'wedge':
            self.log("\n" + "="*60)
            self.log(f"PASS 2: Building Cutout (tolerance: {cutout_tolerance_mm}mm)")
            self.log("="*60)
            
            cutout_dimensions = create_wedge_cutout_dimensions(dimensions, cutout_tolerance_mm)
            cutout_name = f"{results['boat_name']}_Stock_Cutout"
            
            # Build the basic cutout
            cutout_obj = self._build_single_object(doc, cutout_dimensions, cutout_name, 
                                                  skip_export=True, skip_report=True, **kwargs)
            
            # Add perforation cylinders to the cutout
            cutout_obj = self.add_perforation_cylinders(cutout_obj, doc, cutout_dimensions)
            
            # Now export and generate report for the modified cutout
            self.export_stock_step(cutout_obj, object_name=cutout_name)
            
            # Generate approval report for modified cutout
            boat_name = self._extract_boat_name(cutout_name)
            customer_info = {
                'customer': boat_name,
                'part_number': f"{boat_name}-RS-001",
                'revision': 'A'
            }
            
            try:
                image_path = self.report_generator.generate_approval_pdf(
                    cutout_obj, doc, customer_info, 
                    output_filename=f"{cutout_name}_Approval.png"
                )
                if image_path:
                    self.log(f"📸 Generated approval image for modified cutout")
            except Exception as e:
                self.log(f"⚠️ Image generation skipped: {e}")
            
            results['cutout'] = cutout_obj
        else:
            self.log(f"\n⏭️ Skipping cutout - stock style is '{results['style']}', not 'wedge'")
        
        # Summary
        self.log("\n" + "="*60)
        self.log("BUILD COMPLETE")
        self.log("="*60)
        self.log(f"✅ Stock: {stock_name}")
        if results['cutout']:
            cutout_name = f"{results['boat_name']}_Stock_Cutout"
            self.log(f"✅ Cutout: {cutout_name} (tolerance: {cutout_tolerance_mm}mm)")
            self.log(f"   - With perforation cylinders")
        else:
            self.log("⏭️ Cutout: Not built")
        
        # Build statistics
        results['stats'] = {
            'total_time': time.time() - overall_start,
            'boat_name': results['boat_name'],
            'style': results['style'],
            'objects_created': 2 if results['cutout'] else 1,
            'cutout_tolerance_mm': cutout_tolerance_mm if results['cutout'] else None
        }
        
        return results
    
    def _build_single_object(self, doc, dimensions, object_name, skip_export=False, skip_report=False, **kwargs):
        """
        Internal method to build a single stock object from dimensions
        """
        import stock.stock_3D as stock_3D
        
        self.log(f"🏗️ Building: {object_name}")
        start = time.time()
        
        # Always build from dimensions
        stock_obj = stock_3D.build_stock_from_dimensions(doc, dimensions, **kwargs)
        
        if stock_obj:
            # Set the object name
            try:
                stock_obj.Label = object_name
                self.log(f"   Set object label: {object_name}")
                
                if hasattr(stock_obj, 'addProperty'):
                    try:
                        stock_obj.addProperty("App::PropertyString", "IntendedName", 
                                            "Base", "Intended object name")
                        stock_obj.IntendedName = object_name
                    except:
                        pass
            except Exception as e:
                self.log(f"⚠️ Could not set object name: {e}")
            
            # Export to STEP (unless skipped for later modification)
            if not skip_export:
                self.export_stock_step(stock_obj, object_name=object_name)
            
            # Generate approval report (unless skipped for later modification)
            if not skip_report:
                boat_name = self._extract_boat_name(object_name)
                customer_info = {
                    'customer': boat_name,
                    'part_number': f"{boat_name}-RS-001",
                    'revision': 'A'
                }
                
                try:
                    image_path = self.report_generator.generate_approval_pdf(
                        stock_obj, doc, customer_info, 
                        output_filename=f"{object_name}_Approval.png"
                    )
                    if image_path:
                        self.log(f"📸 Generated approval image")
                except Exception as e:
                    self.log(f"⚠️ Image generation skipped: {e}")
            
            self.log(f"✅ Created: {object_name} ({time.time() - start:.2f}s)")
            return stock_obj
        else:
            raise Exception(f"Failed to create {object_name}")
    
    def export_stock_step(self, stock_obj, filename=None, object_name=None):
        """Export to STEP format with project-specific paths"""
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
        output_dir = self.project_path / "boats" / boat_name / "output" / subdir
        
        return self.step_handler.export_step(stock_obj, filename=filename, 
                                            output_dir=output_dir, ensure_merged=True)
    
    def save_document(self, doc, filepath=None):
        """Save FreeCAD document"""
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
    """Simple test of the builder"""
    builder = StockBuilderCore()
    
    try:
        # Use the unified build method
        results = builder.build(cutout_tolerance_mm=2.0)
        
        if results['stock']:
            print(f"\n📊 Build Summary:")
            print(f"   Boat: {results['boat_name']}")
            print(f"   Style: {results['style']}")
            print(f"   Objects created: {results['stats']['objects_created']}")
            print(f"   Total time: {results['stats']['total_time']:.2f}s")
            return True
        else:
            print("❌ No stock object created")
            return False
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)