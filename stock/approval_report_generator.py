"""
Approval Report Generator
Handles PDF/image generation for stock approval reports
Extracted from stock_builder_core for better separation of concerns
"""
from pathlib import Path
from datetime import datetime


class ApprovalReportGenerator:
    """Generate approval reports for stock objects"""
    
    def __init__(self, project_path=None, verbose=True):
        self.project_path = Path(project_path) if project_path else Path.home() / "Rudder_Code"
        self.verbose = verbose
    
    def log(self, message):
        if self.verbose:
            print(message)
    
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
    
    def capture_front_view(self, doc, stock_obj, output_path=None):
        """Capture front view of stock for PDF"""
        import FreeCADGui
        
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
    
    def generate_approval_pdf(self, stock_obj, doc, customer_info=None, output_filename=None):
        """Generate approval image with text info using FreeCAD's built-in export"""
        try:
            import FreeCADGui
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
    
    def quick_approval_report(self, stock_obj, doc, customer_info=None, output_filename=None):
        """Quick method to generate approval PDF
        
        Args:
            stock_obj: The stock object to generate report for
            doc: FreeCAD document
            customer_info: Customer information for the report
            output_filename: Custom output filename
            
        Returns:
            Path to generated PDF/image file
        """
        return self.generate_approval_pdf(stock_obj, doc, customer_info, output_filename)