# FreeCAD Wire Rope Designer Macro
# Save this as WireRopeDesigner.FCMacro in your FreeCAD macro folder
# Can be run standalone with UI or imported as a module to use helper functions
#
# USAGE EXAMPLES:
# ==============
# 1. Run standalone with UI:
#    exec(open("WireRopeDesigner.FCMacro").read())
#
# 2. Import as module and use programmatically:
#    import WireRopeDesigner
#    
#    # Calculate specifications for 8mm rope
#    specs = WireRopeDesigner.calculate_wire_specs(8.0)
#    
#    # Create wire rope without UI
#    doc, rope, core, wires = WireRopeDesigner.create_wire_rope_and_core(
#        cylinder_length=250.0,
#        overall_diameter=8.0, 
#        wire_diameter=specs['wire_diameter'],
#        num_wires=13,
#        helix_pitch=specs['pitch']
#    )
#    
#    # Export to STL
#    rope.exportStl("wire_rope.stl")

import FreeCAD
import FreeCADGui
import Part
from FreeCAD import Base
import sys

# ============================================================================
# STANDARD RIGGING WIRE ROPE SYSTEM - CORE FUNCTIONALITY
# ============================================================================

# Available standard wire diameters (mm)
AVAILABLE_WIRES = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]

# Standard rope diameters available
STANDARD_ROPE_DIAMETERS = [3, 4, 5, 6, 8, 10, 12, 16, 20]

def calculate_wire_specs(rope_diameter):
    """
    Calculate all wire rope specifications from rope diameter
    Using standard rigging wire formulas for 13-wire construction
    """
    import math
    
    # Calculate ideal wire diameter: W = π × D / 12
    ideal_wire = (math.pi * rope_diameter) / 12
    
    # Round down to nearest available wire size
    wire_diameter = None
    for wire in AVAILABLE_WIRES:
        if wire <= ideal_wire:
            wire_diameter = wire
        else:
            break
    
    if wire_diameter is None:
        wire_diameter = AVAILABLE_WIRES[0]  # Fallback to smallest
    
    # Calculate spacing: (diameter × π - wire × 12) / 11
    spacing = (rope_diameter * math.pi - wire_diameter * 12) / 11
    
    # Standard rigging pitch: 7 × diameter
    pitch = 7 * rope_diameter
    
    # 13-wire construction: 1 solid core + 12 outer
    num_wires = 13
    num_outer_wires = 12
    
    # Solid core diameter for cutting tool: overall - 0.5 × wire
    core_diameter = rope_diameter - 0.5 * wire_diameter
    
    # Outer wire radius (distance from center to outer wire centers)
    outer_wire_radius = (rope_diameter - wire_diameter) / 2
    
    return {
        'rope_diameter': rope_diameter,
        'wire_diameter': wire_diameter,
        'ideal_wire': ideal_wire,
        'spacing': spacing,
        'pitch': pitch,
        'num_wires': num_wires,
        'num_outer_wires': num_outer_wires,
        'core_diameter': core_diameter,
        'outer_wire_radius': outer_wire_radius
    }

def create_wire_rope_and_core(cylinder_length=250.0, overall_diameter=8.0, wire_diameter=0.7, 
                             num_wires=13, helix_pitch=56.0, progress_callback=None):
    """
    Creates a 13-wire rigging rope: 1 solid core + 12 outer helical wires
    SIMPLIFIED VERSION: Basic fusion, no complex cutting
    """
    import math
    
    def update_progress(step, total, message):
        if progress_callback:
            progress_callback(int((step / total) * 100), message)
    
    # Calculate parameters for 13-wire construction
    core_diameter = overall_diameter - 0.5 * wire_diameter
    outer_wire_radius = (overall_diameter - wire_diameter) / 2
    num_outer_wires = 12
    
    # Calculate vertical offset
    vertical_offset = helix_pitch / num_outer_wires
    
    # Intelligent calculation of extended length
    min_for_complete_turns = 2 * helix_pitch  # At least 2 complete turns for stability
    min_for_vertical_offset = helix_pitch + (num_outer_wires - 1) * vertical_offset  # Account for all staggered wires
    min_with_safety = cylinder_length + helix_pitch  # Requested length plus one full pitch
    extended_length = max(min_for_complete_turns, min_for_vertical_offset, min_with_safety, cylinder_length * 1.5)
    
    # Calculate start position to ensure complete turns before cutting zone
    # We need at least one full pitch before z=0 to ensure all wires are fully formed
    start_z = -helix_pitch  # Start one full pitch before z=0
    
    print(f"SIMPLIFIED: Creating 13-wire rope: {overall_diameter}mm diameter")
    print(f"Solid core: {core_diameter:.1f}mm + 12 outer helical wires")
    print(f"Length: {extended_length:.1f}mm (no complex cutting)")
    
    # Create document
    doc = FreeCAD.newDocument("WireRope")
    
    # 1. CREATE SOLID CORE
    # Extend core length to account for vertical offsets of all wires
    max_vertical_offset = (num_outer_wires - 1) * vertical_offset
    core_length = extended_length + max_vertical_offset
    solid_core = Part.makeCylinder(
        core_diameter / 2,
        core_length,
        Base.Vector(0, 0, start_z),
        Base.Vector(0, 0, 1)
    )
    
    # Add core to document so it's visible
    core_obj = doc.addObject("Part::Feature", "SolidCore")
    core_obj.Shape = solid_core
    core_obj.Label = f"SolidCore_{core_diameter:.1f}mm"
    
    if hasattr(FreeCAD, 'Gui'):
        core_obj.ViewObject.ShapeColor = (0.2, 0.2, 0.8)  # Blue color
        core_obj.ViewObject.Transparency = 50  # Semi-transparent
    
    print(f"Created solid core: {core_diameter:.1f}mm diameter, Volume: {solid_core.Volume:.1f} mm³")
    
    # 2. CREATE BASE HELICAL WIRE TEMPLATE
    helix = Part.makeHelix(helix_pitch, extended_length, outer_wire_radius)
    helix.translate(Base.Vector(0, 0, start_z))
    
    start_point = helix.Vertexes[0].Point
    circle = Part.makeCircle(wire_diameter / 2, start_point)
    base_wire = Part.Wire(helix).makePipeShell([Part.Wire(circle)], True, True)
    
    # 3. CREATE 12 ROTATED AND OFFSET COPIES
    wire_shapes = []
    wire_objects = []  # Keep track of wire objects to hide them later
    
    for i in range(num_outer_wires):
        # Copy template
        wire_copy = base_wire.copy()
        
        # Rotate around Z-axis
        angle = i * 360.0 / num_outer_wires
        wire_copy.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 0, 1), math.radians(angle))
        
        # Apply vertical offset
        wire_copy.translate(Base.Vector(0, 0, i * vertical_offset))
        
        wire_shapes.append(wire_copy)
        
        # Add to document
        wire_obj = doc.addObject("Part::Feature", f"Wire_{i:02d}")
        wire_obj.Shape = wire_copy
        wire_obj.Label = f"Wire_{i:02d}_{angle:.0f}deg"
        wire_objects.append(wire_obj)  # Store reference
        
        if hasattr(FreeCAD, 'Gui'):
            wire_obj.ViewObject.ShapeColor = (1.0, 0.2, 0.2)
            wire_obj.ViewObject.Transparency = 30
    
    print(f"SIMPLIFIED: Created 1 core + {len(wire_shapes)} wires")
    
    # 4. SIMPLE FUSION
    print("SIMPLIFIED: Starting simple fusion...")
    fused_solid = solid_core.copy()
    
    for i, wire in enumerate(wire_shapes):
        print(f"Fusing wire {i+1}/{len(wire_shapes)}...")
        fused_solid = fused_solid.fuse(wire)
        print(f"Volume after wire {i+1}: {fused_solid.Volume:.1f} mm³")
        
        if fused_solid.Volume == 0:
            print(f"ERROR: Fusion failed at wire {i+1}")
            break
    
    print(f"SIMPLIFIED: Final fused volume: {fused_solid.Volume:.1f} mm³")
    
    # 5. CUTTING OPERATION - CREATE CLEAN ENDS
    print("Performing cutting operation for clean ends...")
    
    # Create cutting cylinder that represents the final desired length
    # The cutting cylinder starts at z=0 and extends for cylinder_length
    cutting_cylinder = Part.makeCylinder(
        overall_diameter,  # Large enough to encompass entire rope
        cylinder_length,
        Base.Vector(0, 0, 0),
        Base.Vector(0, 0, 1)
    )
    
    # Perform intersection to get only the rope within the desired length
    cut_rope = fused_solid.common(cutting_cylinder)
    
    print(f"Cut rope volume: {cut_rope.Volume:.1f} mm³")
    print(f"Clean cut length: {cylinder_length} mm")
    
    # Add final result (with cutting)
    final_obj = doc.addObject("Part::Feature", "WireRope_CleanCut")
    final_obj.Shape = cut_rope
    final_obj.Label = "WireRope_CleanCut"
    
    if hasattr(FreeCAD, 'Gui'):
        final_obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0)
        final_obj.ViewObject.Transparency = 0
    
    # HIDE ALL STRANDS AND CORE AT THE END
    if hasattr(FreeCAD, 'Gui'):
        # Hide the core
        core_obj.ViewObject.Visibility = False
        # Hide all wire strands
        for wire_obj in wire_objects:
            wire_obj.ViewObject.Visibility = False
    
    doc.recompute()
    
    if hasattr(FreeCAD, 'Gui'):
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
    
    print(f"COMPLETE WITH CLEAN CUTS: Volume: {cut_rope.Volume:.1f} mm³")
    
    return doc, cut_rope, solid_core, wire_shapes


# ============================================================================
# UI INTERFACE - ONLY LOADED WHEN RUN AS MAIN
# ============================================================================

def main():
    """Main function that creates and shows the UI dialog"""
    from PySide2 import QtWidgets, QtCore, QtGui
    
    class WireRopeDesignerDialog(QtWidgets.QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("🔧 Wire Rope Designer")
            self.setWindowIcon(QtGui.QIcon.fromTheme("applications-engineering"))
            self.setFixedSize(800, 700)
            self.setStyleSheet("""
                QDialog {
                    background-color: #f5f5f5;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #cccccc;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 10px 0 10px;
                    color: #2c3e50;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
                QListWidget {
                    border: 1px solid #bdc3c7;
                    border-radius: 6px;
                    background-color: white;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #ecf0f1;
                }
                QListWidget::item:selected {
                    background-color: #3498db;
                    color: white;
                }
                QSpinBox, QDoubleSpinBox {
                    border: 1px solid #bdc3c7;
                    border-radius: 4px;
                    padding: 5px;
                    background-color: white;
                }
                QLabel {
                    color: #2c3e50;
                }
            """)
            
            self.init_ui()
            self.update_calculations()
        
        def init_ui(self):
            layout = QtWidgets.QHBoxLayout(self)
            
            # Left panel - Simple inputs
            left_panel = QtWidgets.QVBoxLayout()
            
            # Header
            header = QtWidgets.QLabel("Rigging Wire Rope Designer")
            header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin: 10px;")
            header.setAlignment(QtCore.Qt.AlignCenter)
            left_panel.addWidget(header)
            
            # Input parameters group
            input_group = QtWidgets.QGroupBox("📏 Wire Rope Specification")
            input_layout = QtWidgets.QFormLayout(input_group)
            
            # Rope diameter dropdown
            self.diameter_combo = QtWidgets.QComboBox()
            for diameter in STANDARD_ROPE_DIAMETERS:
                self.diameter_combo.addItem(f"{diameter}mm", diameter)
            self.diameter_combo.setCurrentText("8mm")
            self.diameter_combo.currentTextChanged.connect(self.update_calculations)
            input_layout.addRow("Rope Diameter:", self.diameter_combo)
            
            # Length input
            self.length_spin = QtWidgets.QSpinBox()
            self.length_spin.setRange(10, 1000)
            self.length_spin.setValue(250)
            self.length_spin.setSuffix(" mm")
            input_layout.addRow("Clean Cut Length:", self.length_spin)
            
            # STL export checkbox
            self.stl_checkbox = QtWidgets.QCheckBox("Export STL file")
            self.stl_checkbox.setChecked(True)
            input_layout.addRow("", self.stl_checkbox)
            
            left_panel.addWidget(input_group)
            
            # Calculated specifications group
            calc_group = QtWidgets.QGroupBox("🔢 Calculated Specifications")
            calc_layout = QtWidgets.QVBoxLayout(calc_group)
            
            self.calc_display = QtWidgets.QTextEdit()
            self.calc_display.setMaximumHeight(300)
            self.calc_display.setReadOnly(True)
            calc_layout.addWidget(self.calc_display)
            
            left_panel.addWidget(calc_group)
            
            # Buttons
            button_layout = QtWidgets.QVBoxLayout()
            
            self.create_btn = QtWidgets.QPushButton("🚀 Create Wire Rope")
            self.create_btn.clicked.connect(self.create_wire_rope)
            button_layout.addWidget(self.create_btn)
            
            left_panel.addLayout(button_layout)
            left_panel.addStretch()
            
            # Right panel - Preview and info
            right_panel = QtWidgets.QVBoxLayout()
            
            # Wire rope construction diagram
            diagram_group = QtWidgets.QGroupBox("🔧 Construction Diagram")
            diagram_layout = QtWidgets.QVBoxLayout(diagram_group)
            
            self.diagram_display = QtWidgets.QTextEdit()
            self.diagram_display.setReadOnly(True)
            self.diagram_display.setMaximumHeight(200)
            diagram_layout.addWidget(self.diagram_display)
            
            right_panel.addWidget(diagram_group)
            
            # Construction information
            info_group = QtWidgets.QGroupBox("📖 Rigging Standards")
            info_layout = QtWidgets.QVBoxLayout(info_group)
            
            rigging_info = QtWidgets.QTextEdit()
            rigging_info.setReadOnly(True)
            rigging_info.setMaximumHeight(150)
            rigging_info.setHtml("""
    <b>13-Wire Cutting Tool Construction:</b><br>
    - 1 solid core + 12 outer helical wires<br>
    - Standard lay ratio: 7× diameter<br>
    - Wire diameter: π × D / 12 (rounded down)<br>
    - Solid core: Overall - 0.5 × wire diameter<br>
    - Outer wires: 30° apart around circumference<br>
    - Designed for cutting wire rope patterns<br>
    - Clean cut ends with all components complete<br>
            """)
            info_layout.addWidget(rigging_info)
            
            right_panel.addWidget(info_group)
            
            # Status and log
            status_group = QtWidgets.QGroupBox("📝 Status Log")
            status_layout = QtWidgets.QVBoxLayout(status_group)
            
            self.status_log = QtWidgets.QTextEdit()
            self.status_log.setReadOnly(True)
            self.status_log.setMaximumHeight(200)
            status_layout.addWidget(self.status_log)
            
            right_panel.addWidget(status_group)
            
            # Add panels to main layout
            layout.addLayout(left_panel, 1)
            layout.addLayout(right_panel, 1)
            
            self.last_created_rope = None
            self.update_calculations()
        
        def update_calculations(self):
            """Update all calculated specifications when rope diameter changes"""
            rope_diameter = self.diameter_combo.currentData()
            specs = calculate_wire_specs(rope_diameter)
            
            # Display calculated specifications
            calc_text = f"""
    <b>Calculated Specifications for {rope_diameter}mm Cutting Tool:</b><br>
    <br>
    <table border="1" cellpadding="4" style="border-collapse: collapse;">
    <tr><td><b>Parameter</b></td><td><b>Value</b></td><td><b>Formula/Standard</b></td></tr>
    <tr><td>Rope Diameter</td><td>{specs['rope_diameter']:.1f} mm</td><td>User selected</td></tr>
    <tr><td>Ideal Wire Diameter</td><td>{specs['ideal_wire']:.2f} mm</td><td>π × D / 12</td></tr>
    <tr><td>Actual Wire Diameter</td><td>{specs['wire_diameter']:.2f} mm</td><td>Rounded down to standard</td></tr>
    <tr><td>Wire Spacing</td><td>{specs['spacing']:.2f} mm</td><td>(D×π - wire×12) / 11</td></tr>
    <tr><td>Lay Pitch</td><td>{specs['pitch']:.0f} mm</td><td>7 × diameter (rigging std)</td></tr>
    <tr><td>Total Wires</td><td>{specs['num_wires']} (1+12)</td><td>1 solid core + 12 outer</td></tr>
    <tr><td>Outer Wire Radius</td><td>{specs['outer_wire_radius']:.1f} mm</td><td>(Overall - wire) / 2</td></tr>
    <tr><td><b>Solid Core Diameter</b></td><td><b>{specs['core_diameter']:.1f} mm</b></td><td><b>Overall - 0.5 × wire</b></td></tr>
    </table>
    <br>
    <b>Available Wire Sizes:</b> {', '.join(map(str, AVAILABLE_WIRES))} mm<br>
            """
            
            self.calc_display.setHtml(calc_text)
            
            # Update construction diagram
            self.update_diagram(specs)
            
            self.log_message(f"Updated calculations for {rope_diameter}mm 13-wire rope")
        
        def update_diagram(self, specs):
            """Update the construction diagram with current specifications"""
            diagram_text = f"""
    <b>13-Wire Cutting Tool Construction (Cross Section):</b><br>
    <br>
    <pre style="font-family: monospace; font-size: 12px;">
        12 Outer Helical Wires × {specs['wire_diameter']:.1f}mm
        
             ⚬   ⚬   ⚬
           ⚬           ⚬
         ⚬      ███      ⚬     ███ = Solid core ({specs['core_diameter']:.1f}mm)
           ⚬           ⚬     ⚬ = Outer wires (helical)
             ⚬   ⚬   ⚬
        
        Solid core: {specs['core_diameter']:.1f}mm diameter
        Outer wires: {specs['wire_diameter']:.1f}mm each  
        Outer radius: {specs['outer_wire_radius']:.1f}mm
        Wire spacing: {specs['spacing']:.2f}mm
        Angular spacing: 30° between outer wires
    </pre>
    <br>
    <b>Cutting Tool Construction:</b><br>
    - Solid core: {specs['core_diameter']:.1f}mm diameter (overall - 0.5×wire)<br>
    - 12 outer wires: {specs['pitch']:.0f}mm pitch helixes<br>
    - Each outer wire rotated 30° from previous<br>
    - Staggered start positions for clean cutting<br>
    - Designed for use as wire rope cutting pattern<br>
            """
            
            self.diagram_display.setHtml(diagram_text)
        
        def create_wire_rope(self):
            try:
                self.log_message("Starting wire rope creation...")
                
                # Disable UI during creation
                self.create_btn.setEnabled(False)
                self.create_btn.setText("Creating...")
                
                # Get parameters
                rope_diameter = self.diameter_combo.currentData()
                length = self.length_spin.value()
                
                # Calculate all specifications
                specs = calculate_wire_specs(rope_diameter)
                
                self.log_message(f"Creating {rope_diameter}mm wire rope cutting tool")
                self.log_message(f"Wire diameter: {specs['wire_diameter']}mm (from {specs['ideal_wire']:.2f}mm ideal)")
                self.log_message(f"Solid core: {specs['core_diameter']:.1f}mm (overall - 0.5×wire)")
                self.log_message(f"Pitch: {specs['pitch']}mm (7× diameter standard)")
                self.log_message(f"Construction: 1 solid core + 12 outer helical wires")
                
                # Create progress dialog
                progress = QtWidgets.QProgressDialog("Creating wire rope...", "Cancel", 0, 100, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.setAutoClose(True)
                progress.setAutoReset(True)
                progress.show()
                
                def progress_callback(percent, message):
                    progress.setValue(percent)
                    progress.setLabelText(message)
                    QtWidgets.QApplication.processEvents()  # Keep UI responsive
                    if progress.wasCanceled():
                        raise Exception("Operation cancelled by user")
                
                # Create the wire rope with calculated specifications
                doc, rope_solid, core, wires = create_wire_rope_and_core(
                    cylinder_length=length,
                    overall_diameter=specs['rope_diameter'],
                    wire_diameter=specs['wire_diameter'],
                    num_wires=specs['num_wires'],
                    helix_pitch=specs['pitch'],
                    progress_callback=progress_callback
                )
                
                progress.close()
                
                self.last_created_rope = rope_solid
                
                volume = rope_solid.Volume
                self.log_message(f"✅ Wire rope created successfully!")
                self.log_message(f"Clean cut length: {length} mm")
                self.log_message(f"Volume: {volume:.1f} mm³")
                self.log_message(f"Document: {doc.Name}")
                self.log_message(f"Specifications: {rope_diameter}mm × {length}mm, 13-wire with {specs['wire_diameter']}mm wires")
                
                # Export STL if checkbox is checked
                if self.stl_checkbox.isChecked():
                    filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                        self,
                        "Export Wire Rope STL",
                        f"rigging_13wire_{rope_diameter}mm_{length}mm_{specs['wire_diameter']}mm_wire.stl",
                        "STL Files (*.stl)"
                    )
                    
                    if filename:
                        rope_solid.exportStl(filename)
                        self.log_message(f"✅ STL exported: {filename}")
                
                # CLOSE THE DIALOG AFTER SUCCESSFUL CREATION
                self.accept()
                
            except Exception as e:
                if hasattr(locals(), 'progress'):
                    progress.close()
                self.log_message(f"❌ Error creating wire rope: {str(e)}")
                # Re-enable UI on error
                self.create_btn.setEnabled(True)
                self.create_btn.setText("🚀 Create Wire Rope")
        
        def log_message(self, message):
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.status_log.append(f"[{timestamp}] {message}")
    
    # Create and show the dialog
    dialog = WireRopeDesignerDialog()
    dialog.exec_()


# Run the macro when executed directly
if __name__ == "__main__":
    main()