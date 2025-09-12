"""
Stock Builder Core - Clean Architecture
Reads CSV once, builds everything from dimensions
"""
import sys
from pathlib import Path
import time
import math

# Add venv path for reportlab access in FreeCAD
venv_path = Path.home() / "Rudder_Code" / "venv" / "lib" / "python3.9" / "site-packages"
if venv_path.exists():
    sys.path.insert(0, str(venv_path))

import FreeCAD as App
import Part
from FreeCAD import Vector
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
        Uses hybrid approach: fuse cylinders with post only, then combine with wedges
        Modified configuration: 4 cylinders per level (+Y, -Y, +30°, -30°), 25mm spacing
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
            vertical_spacing = 25.0  # mm between centers (changed from 15mm)
            
            # Get post dimensions from the dimensions dict
            post_end_z = dimensions.get('post_end_mm', 604.0)
            
            # Starting position: 30mm down from top
            start_z = -30.0
            
            # Calculate number of cylinders that fit along the post
            end_z = -post_end_z + 30.0
            usable_length = abs(start_z - end_z)
            num_cylinders = int(usable_length / vertical_spacing) + 1
            
            # Create list to hold all cylinder shapes
            cylinder_shapes = []
            
            self.log(f"   Post length: {post_end_z}mm")
            self.log(f"   Starting perforations at Z={start_z}mm")
            self.log(f"   Vertical spacing: {vertical_spacing}mm")
            self.log(f"   Creating {num_cylinders} perforation levels")
            
            # Create cylinders at each vertical position
            for i in range(num_cylinders):
                z_position = start_z - (i * vertical_spacing)
                
                # Skip if we're getting too close to the bottom
                if z_position < end_z:
                    break
                
                # Y direction (positive) - straight forward
                cyl_y_pos = Part.makeCylinder(
                    cylinder_radius,
                    cylinder_length,
                    App.Vector(0, 0, z_position),
                    App.Vector(0, 1, 0)  # +Y direction
                )
                cylinder_shapes.append(cyl_y_pos)
                
                # Y direction (negative) - straight back
                cyl_y_neg = Part.makeCylinder(
                    cylinder_radius,
                    cylinder_length,
                    App.Vector(0, 0, z_position),
                    App.Vector(0, -1, 0)  # -Y direction
                )
                cylinder_shapes.append(cyl_y_neg)
                
                # Angled at +30° from Y axis (toward -X)
                # Direction vector: cos(30°) in Y, -sin(30°) in X
                angle_30 = math.radians(30)
                dir_30_pos = App.Vector(-math.cos(angle_30), math.sin(angle_30), 0)
                cyl_30_pos = Part.makeCylinder(
                    cylinder_radius,
                    cylinder_length,
                    App.Vector(0, 0, z_position),
                    dir_30_pos
                )
                cylinder_shapes.append(cyl_30_pos)
                
                # Angled at -30° from Y axis (toward +X)
                # Direction vector: cos(30°) in Y, sin(30°) in X
                dir_30_neg = App.Vector(-math.cos(angle_30), -math.sin(angle_30), 0)
                cyl_30_neg = Part.makeCylinder(
                    cylinder_radius,
                    cylinder_length,
                    App.Vector(0, 0, z_position),
                    dir_30_neg
                )
                cylinder_shapes.append(cyl_30_neg)
            
            self.log(f"   Created {len(cylinder_shapes)} perforation cylinders (4 per level)")
            
            # HYBRID APPROACH: Separate post and wedge shapes
            if cylinder_shapes:
                # Step 1: Identify post vs wedge shapes by volume/characteristics
                post_shapes = []
                wedge_shapes = []
                
                # Get the solids from the cutout
                solids = cutout_shape.Solids if hasattr(cutout_shape, 'Solids') else []
                
                for i, solid in enumerate(solids):
                    # Posts are cylindrical/tapered and have much larger volume
                    bbox = solid.BoundBox
                    
                    # Check if it's centered around origin (characteristic of posts)
                    x_center = (bbox.XMin + bbox.XMax) / 2
                    y_center = (bbox.YMin + bbox.YMax) / 2
                    
                    # Posts are centered around X=0, Y=0
                    if abs(x_center) < 5 and abs(y_center) < 5:
                        post_shapes.append(solid)
                        self.log(f"   Identified shape {i} as POST (centered at origin)")
                    else:
                        wedge_shapes.append(solid)
                        self.log(f"   Identified shape {i} as WEDGE (offset from origin)")
                
                self.log(f"   Separated: {len(post_shapes)} post shapes, {len(wedge_shapes)} wedge shapes")
                
                # Step 2: Fuse cylinders with post shapes only
                if post_shapes:
                    # Combine all post shapes
                    if len(post_shapes) > 1:
                        post_compound = post_shapes[0].fuse(post_shapes[1:])
                    else:
                        post_compound = post_shapes[0]
                    
                    # Create compound of cylinders
                    cylinders_compound = Part.makeCompound(cylinder_shapes)
                    
                    # Fuse cylinders with post
                    self.log("   Fusing cylinders with post only...")
                    post_with_cylinders = post_compound.fuse(cylinders_compound)
                    
                    # Step 3: Combine modified post with wedges
                    final_shapes = [post_with_cylinders]
                    final_shapes.extend(wedge_shapes)
                    
                    # Fuse everything together for final solid
                    self.log("   Final fusion of post+cylinders with wedges...")
                    if len(final_shapes) > 1:
                        modified_shape = final_shapes[0].fuse(final_shapes[1:])
                    else:
                        modified_shape = final_shapes[0]
                else:
                    # Fallback: no posts found, use original approach
                    self.log("   WARNING: No post shapes identified, using original fusion")
                    cylinders_compound = Part.makeCompound(cylinder_shapes)
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
                
                self.log("✅ Successfully added perforation cylinders (4 directions, 25mm spacing)")
                return modified_obj
            else:
                self.log("⚠️ No cylinders created")
                return cutout_obj
                
        except Exception as e:
            self.log(f"⚠️ Error adding perforation cylinders: {e}")
            import traceback
            traceback.print_exc()
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
        
        # Step 4: If wedge style, build cutout
        if results['style'] == 'wedge':
            self.log("\n" + "="*60)
            self.log(f"PASS 2: Building Cutout (tolerance: {cutout_tolerance_mm}mm)")
            self.log("="*60)
            
            cutout_dimensions = create_wedge_cutout_dimensions(dimensions, cutout_tolerance_mm)
            cutout_name = f"{results['boat_name']}_Stock_Cutout"
            
            # Build the basic cutout WITHOUT any modifications - skip export and report for now
            cutout_obj = self._build_single_object(doc, cutout_dimensions, cutout_name, 
                                                  skip_export=True, skip_report=True, **kwargs)
            
            # Step 5: Apply ALL modifications at the very end
            self.log("\n" + "="*60)
            self.log("PASS 3: Adding Final Modifications")
            self.log("="*60)
            
            # Add perforation cylinders with hybrid approach
            cutout_obj = self.add_perforation_cylinders(cutout_obj, doc, cutout_dimensions)
            
            # Now export and generate report for the fully modified cutout
            self.log("\n" + "="*60)
            self.log("PASS 4: Export and Documentation")
            self.log("="*60)
            
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
            self.log(f"\n⭕️ Skipping cutout - stock style is '{results['style']}', not 'wedge'")
        
        # Summary
        self.log("\n" + "="*60)
        self.log("BUILD COMPLETE")
        self.log("="*60)
        self.log(f"✅ Stock: {stock_name}")
        if results['cutout']:
            cutout_name = f"{results['boat_name']}_Stock_Cutout"
            self.log(f"✅ Cutout: {cutout_name} (tolerance: {cutout_tolerance_mm}mm)")
            self.log(f"   - With perforation cylinders (4 directions, 25mm spacing)")
            self.log(f"   - With support plates (6 total)")
        else:
            self.log("⭕️ Cutout: Not built")
        
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