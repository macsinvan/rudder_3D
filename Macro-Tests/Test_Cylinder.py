# FreeCAD Macro for Configurable Test Cylinder with Cylindrical Indent
# Version: 3.0 - UI Configurable with Cylindrical Indent
# Compatible with: FreeCAD 1.0+
# Description: Creates parametric cylinders with configurable cylindrical indents for 3D printing and foam filling tests

import FreeCAD
import FreeCADGui
import Part
import Mesh
import os
from FreeCAD import Base

# Import PySide2 for UI (FreeCAD 1.0 compatible)
try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
                                   QLabel, QDoubleSpinBox, QCheckBox, QPushButton,
                                   QGroupBox, QMessageBox, QSpinBox)
    from PySide2.QtCore import Qt
    PYSIDE_AVAILABLE = True
except ImportError:
    try:
        from PySide import QtGui, QtCore
        from PySide.QtGui import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                                  QLabel, QDoubleSpinBox, QCheckBox, QPushButton,
                                  QGroupBox, QMessageBox, QSpinBox)
        from PySide.QtCore import Qt
        PYSIDE_AVAILABLE = True
    except ImportError:
        PYSIDE_AVAILABLE = False
        FreeCAD.Console.PrintError("PySide not available. Running with default parameters.\n")

# ==============================================================================
# UI CONFIGURATION DIALOG
# ==============================================================================

class TestCylinderConfigDialog(QDialog):
    """Configuration dialog for test cylinder parameters"""
    
    def __init__(self):
        super(TestCylinderConfigDialog, self).__init__()
        self.setWindowTitle("Test Cylinder Configuration")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setModal(True)
        self.resize(400, 500)
        
        # Store parameters
        self.parameters = {}
        self.accepted = False
        
        self.setup_ui()
        self.load_defaults()
        self.connect_signals()
    
    def setup_ui(self):
        """Create the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Cylinder Dimensions Group
        cylinder_group = QGroupBox("Cylinder Dimensions")
        cylinder_layout = QGridLayout(cylinder_group)
        
        # Cylinder diameter
        cylinder_layout.addWidget(QLabel("Diameter (mm):"), 0, 0)
        self.cylinder_diameter = QDoubleSpinBox()
        self.cylinder_diameter.setRange(10.0, 200.0)
        self.cylinder_diameter.setSingleStep(1.0)
        self.cylinder_diameter.setDecimals(1)
        cylinder_layout.addWidget(self.cylinder_diameter, 0, 1)
        
        # Cylinder height
        cylinder_layout.addWidget(QLabel("Height (mm):"), 1, 0)
        self.cylinder_height = QDoubleSpinBox()
        self.cylinder_height.setRange(5.0, 200.0)
        self.cylinder_height.setSingleStep(1.0)
        self.cylinder_height.setDecimals(1)
        cylinder_layout.addWidget(self.cylinder_height, 1, 1)
        
        main_layout.addWidget(cylinder_group)
        
        # Cylindrical Indent Group
        indent_group = QGroupBox("Cylindrical Indent")
        indent_layout = QGridLayout(indent_group)
        
        # Enable indent
        self.enable_indent = QCheckBox("Create cylindrical indent on top surface")
        self.enable_indent.setChecked(True)
        indent_layout.addWidget(self.enable_indent, 0, 0, 1, 2)
        
        # Indent diameter
        indent_layout.addWidget(QLabel("Indent Diameter (mm):"), 1, 0)
        self.indent_diameter = QDoubleSpinBox()
        self.indent_diameter.setRange(5.0, 190.0)
        self.indent_diameter.setSingleStep(1.0)
        self.indent_diameter.setDecimals(1)
        indent_layout.addWidget(self.indent_diameter, 1, 1)
        
        # Indent depth
        indent_layout.addWidget(QLabel("Indent Depth (mm):"), 2, 0)
        self.indent_depth = QDoubleSpinBox()
        self.indent_depth.setRange(0.5, 50.0)
        self.indent_depth.setSingleStep(0.5)
        self.indent_depth.setDecimals(1)
        indent_layout.addWidget(self.indent_depth, 2, 1)
        
        main_layout.addWidget(indent_group)
        
        # STL Export Group
        export_group = QGroupBox("STL Export Settings")
        export_layout = QGridLayout(export_group)
        
        # Auto export
        self.auto_export = QCheckBox("Automatically export to STL after creation")
        self.auto_export.setChecked(True)
        export_layout.addWidget(self.auto_export, 0, 0, 1, 2)
        
        # Mesh tolerance
        export_layout.addWidget(QLabel("Mesh Tolerance (mm):"), 1, 0)
        self.mesh_tolerance = QDoubleSpinBox()
        self.mesh_tolerance.setRange(0.01, 1.0)
        self.mesh_tolerance.setSingleStep(0.01)
        self.mesh_tolerance.setDecimals(2)
        export_layout.addWidget(self.mesh_tolerance, 1, 1)
        
        main_layout.addWidget(export_group)
        
        # Preview Information
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        preview_layout.addWidget(self.preview_label)
        
        main_layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_button = QPushButton("Create Cylinder")
        self.create_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.create_button)
        
        main_layout.addLayout(button_layout)
    
    def load_defaults(self):
        """Load default parameter values"""
        self.cylinder_diameter.setValue(50.0)
        self.cylinder_height.setValue(32.0)
        self.indent_diameter.setValue(40.0)
        self.indent_depth.setValue(3.0)
        self.mesh_tolerance.setValue(0.1)
        
        self.update_preview()
    
    def connect_signals(self):
        """Connect UI signals to update functions"""
        # Connect all parameter changes to preview update
        self.cylinder_diameter.valueChanged.connect(self.update_preview)
        self.cylinder_height.valueChanged.connect(self.update_preview)
        self.enable_indent.toggled.connect(self.on_indent_enabled)
        self.indent_diameter.valueChanged.connect(self.update_preview)
        self.indent_depth.valueChanged.connect(self.update_preview)
        
        # Buttons
        self.create_button.clicked.connect(self.accept_dialog)
        self.cancel_button.clicked.connect(self.reject)
    
    def on_indent_enabled(self, enabled):
        """Handle indent enable/disable"""
        self.indent_diameter.setEnabled(enabled)
        self.indent_depth.setEnabled(enabled)
        self.update_preview()
    
    def update_preview(self):
        """Update the preview information"""
        # Get current values
        cyl_dia = self.cylinder_diameter.value()
        cyl_height = self.cylinder_height.value()
        indent_enabled = self.enable_indent.isChecked()
        indent_dia = self.indent_diameter.value()
        indent_depth = self.indent_depth.value()
        
        # Calculate volume
        cyl_radius = cyl_dia / 2.0
        cylinder_volume = 3.14159 * cyl_radius * cyl_radius * cyl_height
        
        # Calculate indent volume if enabled
        indent_volume = 0
        if indent_enabled:
            indent_radius = indent_dia / 2.0
            # Volume of cylinder: V = π * r² * h
            indent_volume = 3.14159 * indent_radius * indent_radius * indent_depth
        
        net_volume = (cylinder_volume - indent_volume) / 1000.0  # Convert to cm³
        
        # Validation checks
        warnings = []
        if indent_enabled:
            if indent_dia >= cyl_dia:
                warnings.append("⚠️ Indent diameter should be smaller than cylinder diameter")
            if indent_depth >= cyl_height:
                warnings.append("⚠️ Indent depth should be less than cylinder height")
        
        # Build preview text
        preview_text = f"""<b>Cylinder Specifications:</b>
• Dimensions: {cyl_dia}mm diameter × {cyl_height}mm height
• Base Volume: {cylinder_volume/1000:.1f} cm³

"""
        
        if indent_enabled:
            preview_text += f"""<b>Cylindrical Indent:</b>
• Indent: {indent_dia}mm diameter × {indent_depth}mm deep
• Removed Volume: {indent_volume/1000:.1f} cm³
• Net Volume: {net_volume:.1f} cm³

"""
        else:
            preview_text += f"<b>No Indent</b> - Net Volume: {net_volume:.1f} cm³\n\n"
        
        if warnings:
            preview_text += "<b>⚠️ Warnings:</b>\n"
            for warning in warnings:
                preview_text += f"• {warning}\n"
        else:
            preview_text += "<b>✅ Configuration Valid</b>"
        
        self.preview_label.setText(preview_text)
        
        # Enable/disable create button based on validation
        self.create_button.setEnabled(len(warnings) == 0)
    
    def accept_dialog(self):
        """Accept dialog and store parameters"""
        self.parameters = {
            'cylinder_diameter': self.cylinder_diameter.value(),
            'cylinder_height': self.cylinder_height.value(),
            'enable_indent': self.enable_indent.isChecked(),
            'indent_diameter': self.indent_diameter.value(),
            'indent_depth': self.indent_depth.value(),
            'auto_export': self.auto_export.isChecked(),
            'mesh_tolerance': self.mesh_tolerance.value()
        }
        self.accepted = True
        self.accept()

# ==============================================================================
# CYLINDER CREATION FUNCTIONS
# ==============================================================================

def create_configured_cylinder(params):
    """Create a test cylinder with specified parameters"""
    
    # Clear console
    FreeCAD.Console.PrintMessage("\n" + "="*60 + "\n")
    FreeCAD.Console.PrintMessage("Creating Configured Test Cylinder...\n")
    FreeCAD.Console.PrintMessage("="*60 + "\n")
    
    # Create a new document if none exists
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument("ConfigurableTestCylinder")
    
    doc = FreeCAD.ActiveDocument
    
    # Extract parameters
    cyl_diameter = params['cylinder_diameter']
    cyl_height = params['cylinder_height']
    enable_indent = params['enable_indent']
    indent_diameter = params['indent_diameter']
    indent_depth = params['indent_depth']
    
    cyl_radius = cyl_diameter / 2.0
    
    FreeCAD.Console.PrintMessage(f"Cylinder: {cyl_diameter}mm dia × {cyl_height}mm height\n")
    
    # Create main cylinder
    main_cylinder = Part.makeCylinder(
        cyl_radius,
        cyl_height,
        Base.Vector(0, 0, 0),
        Base.Vector(0, 0, 1)
    )
    
    # Create cylindrical indent if enabled
    final_shape = main_cylinder
    
    if enable_indent:
        FreeCAD.Console.PrintMessage(f"Adding cylindrical indent: {indent_diameter}mm dia × {indent_depth}mm deep\n")
        
        indent_radius = indent_diameter / 2.0
        
        # Create cylinder for the indent
        # Position cylinder at top surface, cutting down by the specified depth
        indent_cylinder = Part.makeCylinder(
            indent_radius,
            indent_depth,
            Base.Vector(0, 0, cyl_height - indent_depth),
            Base.Vector(0, 0, 1)
        )
        
        # Cut the cylinder from the main cylinder
        final_shape = main_cylinder.cut(indent_cylinder)
        FreeCAD.Console.PrintMessage("Cylindrical indent created successfully\n")
    
    # Create the FreeCAD object
    cylinder_name = "TestCylinder_Config"
    if enable_indent:
        cylinder_name += f"_Indent{int(indent_diameter)}x{indent_depth}"
    
    cylinder_obj = doc.addObject("Part::Feature", cylinder_name)
    cylinder_obj.Shape = final_shape
    
    # Add custom properties for parametric control
    cylinder_obj.addProperty("App::PropertyLength", "Diameter", "Dimensions", "Cylinder diameter")
    cylinder_obj.Diameter = cyl_diameter
    
    cylinder_obj.addProperty("App::PropertyLength", "Height", "Dimensions", "Cylinder height")
    cylinder_obj.Height = cyl_height
    
    if enable_indent:
        cylinder_obj.addProperty("App::PropertyLength", "IndentDiameter", "Indent", "Cylindrical indent diameter")
        cylinder_obj.IndentDiameter = indent_diameter
        
        cylinder_obj.addProperty("App::PropertyLength", "IndentDepth", "Indent", "Cylindrical indent depth")
        cylinder_obj.IndentDepth = indent_depth
    
    # Calculate volumes
    total_volume = final_shape.Volume / 1000  # Convert to cm³
    
    # Recompute and fit view
    doc.recompute()
    
    # Try to fit view if GUI is available
    try:
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
        FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
    except:
        pass  # GUI commands not available in console mode
    
    # Print summary
    FreeCAD.Console.PrintMessage("\n" + "="*60 + "\n")
    FreeCAD.Console.PrintMessage("CYLINDER CREATED SUCCESSFULLY!\n")
    FreeCAD.Console.PrintMessage(f"Dimensions: {cyl_diameter}mm dia × {cyl_height}mm height\n")
    
    if enable_indent:
        FreeCAD.Console.PrintMessage(f"Cylindrical Indent: {indent_diameter}mm dia × {indent_depth}mm deep\n")
    
    FreeCAD.Console.PrintMessage(f"Final Volume: {total_volume:.1f} cm³\n")
    FreeCAD.Console.PrintMessage("="*60 + "\n")
    
    return cylinder_obj

# ==============================================================================
# STL EXPORT FUNCTION
# ==============================================================================

def export_cylinder_to_stl(obj, params):
    """Export the configured cylinder to STL file"""
    
    # Generate filename based on configuration
    cyl_dia = int(params['cylinder_diameter'])
    cyl_height = int(params['cylinder_height'])
    
    if params['enable_indent']:
        indent_dia = int(params['indent_diameter'])
        indent_depth = params['indent_depth']
        filename = f"TestCylinder_D{cyl_dia}_H{cyl_height}_Indent{indent_dia}x{indent_depth}.stl"
    else:
        filename = f"TestCylinder_D{cyl_dia}_H{cyl_height}_Solid.stl"
    
    # Get Downloads folder path
    downloads_path = os.path.expanduser("~/Downloads")
    full_path = os.path.join(downloads_path, filename)
    
    try:
        # Create mesh with specified tolerance
        mesh_tolerance = params['mesh_tolerance']
        mesh_obj = Mesh.Mesh(obj.Shape.tessellate(mesh_tolerance))
        
        # Export to STL
        mesh_obj.write(full_path)
        
        FreeCAD.Console.PrintMessage(f"\n" + "="*60 + "\n")
        FreeCAD.Console.PrintMessage("STL EXPORT SUCCESSFUL!\n")
        FreeCAD.Console.PrintMessage(f"File: {filename}\n")
        FreeCAD.Console.PrintMessage(f"Location: {full_path}\n")
        
        # Check file size
        if os.path.exists(full_path):
            file_size = os.path.getsize(full_path) / 1024
            FreeCAD.Console.PrintMessage(f"File size: {file_size:.1f} KB\n")
        
        print_slicer_recommendations(params)
        
        return full_path
    
    except Exception as e:
        FreeCAD.Console.PrintError(f"Error exporting STL: {str(e)}\n")
        FreeCAD.Console.PrintMessage("Try File → Export and select STL format manually\n")
        return None

def print_slicer_recommendations(params):
    """Print recommended slicer settings"""
    FreeCAD.Console.PrintMessage("\n" + "-"*60 + "\n")
    FreeCAD.Console.PrintMessage("RECOMMENDED BAMBU STUDIO SETTINGS:\n\n")
    
    if params['enable_indent']:
        FreeCAD.Console.PrintMessage("For Foam Filling via Cylindrical Indent:\n")
        FreeCAD.Console.PrintMessage("  • Infill Pattern: GYROID (optimal for foam distribution)\n")
        FreeCAD.Console.PrintMessage("  • Infill Density: 5-15% (allows foam flow)\n")
        FreeCAD.Console.PrintMessage("  • Wall Loops: 2-3\n")
        FreeCAD.Console.PrintMessage("  • Top/Bottom Layers: 3-4\n")
        FreeCAD.Console.PrintMessage("  • Layer Height: 0.2-0.3mm\n")
        FreeCAD.Console.PrintMessage("  • Support: None needed\n")
        
        FreeCAD.Console.PrintMessage("\nFoam Injection Process:\n")
        FreeCAD.Console.PrintMessage(f"  1. Print orientation: Indent facing UP\n")
        FreeCAD.Console.PrintMessage(f"  2. Cylindrical indent ({params['indent_diameter']}mm × {params['indent_depth']}mm) ready for foam\n")
        FreeCAD.Console.PrintMessage("  3. Inject marine expanding foam into cylindrical indent\n")
        FreeCAD.Console.PrintMessage("  4. Foam will flow through gyroid channels\n")
        FreeCAD.Console.PrintMessage("  5. Fill to ~75% capacity (foam expands 2-3x)\n")
        FreeCAD.Console.PrintMessage("  6. Allow 24 hours to fully cure\n")
    else:
        FreeCAD.Console.PrintMessage("For Solid Test Cylinder:\n")
        FreeCAD.Console.PrintMessage("  • Infill Pattern: CUBIC or GRID\n")
        FreeCAD.Console.PrintMessage("  • Infill Density: 15-25%\n")
        FreeCAD.Console.PrintMessage("  • Wall Loops: 3-4\n")
        FreeCAD.Console.PrintMessage("  • Top/Bottom Layers: 4-5\n")
        FreeCAD.Console.PrintMessage("  • Layer Height: 0.2mm\n")
    
    FreeCAD.Console.PrintMessage("\nWhy Gyroid Infill is Best for Foam:\n")
    FreeCAD.Console.PrintMessage("  • Continuous 3D interconnected channels\n")
    FreeCAD.Console.PrintMessage("  • No dead ends - complete foam distribution\n")
    FreeCAD.Console.PrintMessage("  • Strong isotropic mechanical properties\n")
    FreeCAD.Console.PrintMessage("  • Excellent for liquid/foam flow dynamics\n")
    FreeCAD.Console.PrintMessage("="*60 + "\n")

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def run_configurable_cylinder_macro():
    """Main function to run the configurable cylinder macro"""
    
    FreeCAD.Console.PrintMessage("="*60 + "\n")
    FreeCAD.Console.PrintMessage("CONFIGURABLE TEST CYLINDER MACRO v3.0\n")
    FreeCAD.Console.PrintMessage("Compatible with FreeCAD 1.0+\n")
    FreeCAD.Console.PrintMessage("="*60 + "\n")
    
    if PYSIDE_AVAILABLE:
        # Show configuration dialog
        dialog = TestCylinderConfigDialog()
        dialog.exec_()
        
        if dialog.accepted:
            params = dialog.parameters
            
            # Create the cylinder
            cylinder_obj = create_configured_cylinder(params)
            
            # Export to STL if requested
            if params['auto_export']:
                stl_path = export_cylinder_to_stl(cylinder_obj, params)
                if stl_path:
                    FreeCAD.Console.PrintMessage("\n✅ Ready for 3D printing!\n")
                    FreeCAD.Console.PrintMessage("Import the STL into Bambu Studio and use recommended settings.\n")
            else:
                FreeCAD.Console.PrintMessage("\nManual STL export available:\n")
                FreeCAD.Console.PrintMessage("File → Export → Select STL format\n")
            
            FreeCAD.Console.PrintMessage("\n🎯 Cylinder creation completed successfully!\n")
        else:
            FreeCAD.Console.PrintMessage("Cylinder creation cancelled by user.\n")
    
    else:
        # Fallback: Create with default parameters if PySide not available
        FreeCAD.Console.PrintWarning("PySide not available. Creating with default parameters.\n")
        
        default_params = {
            'cylinder_diameter': 50.0,
            'cylinder_height': 32.0,
            'enable_indent': True,
            'indent_diameter': 40.0,
            'indent_depth': 3.0,
            'auto_export': True,
            'mesh_tolerance': 0.1
        }
        
        cylinder_obj = create_configured_cylinder(default_params)
        stl_path = export_cylinder_to_stl(cylinder_obj, default_params)
        
        if stl_path:
            FreeCAD.Console.PrintMessage("\n✅ Default cylinder created and exported!\n")

# ==============================================================================
# RUN THE MACRO
# ==============================================================================

# Execute the configurable cylinder macro
run_configurable_cylinder_macro()