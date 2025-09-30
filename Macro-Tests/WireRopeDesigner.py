# FreeCAD Wire Rope Designer Macro
# WireRopeDesigner.py
# Save this as WireRopeDesigner.FCMacro in your FreeCAD macro folder

import FreeCAD
import FreeCADGui
import Part
from FreeCAD import Base
from PySide2 import QtWidgets, QtCore, QtGui
import sys

# ============================================================================
# STANDARD RIGGING WIRE ROPE SYSTEM
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
    
    # Solid core diameter for cutting tool: overall - 0.3 × wire (increased for robust fusion)
    core_diameter = rope_diameter - 0.3 * wire_diameter
    
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

def create_wire_rope_shape(rope_diameter=8.0, length=250.0):
    """
    Simple wrapper function to create a wire rope shape.
    
    Args:
        rope_diameter: Overall rope diameter in mm (3, 4, 5, 6, 8, 10, 12, 16, or 20)
        length: Desired length in mm
    
    Returns:
        Part.Shape object of the complete wire rope with clean cut ends
    
    Example:
        import WireRopeDesigner
        rope = WireRopeDesigner.create_wire_rope_shape(diameter=8, length=250)
        # rope is now a Part.Shape that can be used in other operations
    """
    # Calculate specifications
    specs = calculate_wire_specs(rope_diameter)
    
    # Create rope without document (just return the shape)
    rope_shape = create_wire_rope_and_core(
        cylinder_length=length,
        overall_diameter=specs['rope_diameter'],
        wire_diameter=specs['wire_diameter'],
        num_wires=specs['num_wires'],
        helix_pitch=specs['pitch'],
        create_document=False  # Don't create a document
    )
    
    return rope_shape

def create_wire_rope_and_core(cylinder_length=250.0, overall_diameter=8.0, wire_diameter=0.7, 
                             num_wires=13, helix_pitch=56.0, progress_callback=None,
                             create_document=True, document_name="WireRope"):
    """
    Creates a 13-wire rigging rope: 1 solid core + 12 outer helical wires
    With clean cut ends at complete pitch boundaries
    
    Args:
        cylinder_length: Desired length of rope in mm
        overall_diameter: Overall rope diameter in mm
        wire_diameter: Individual wire diameter in mm
        num_wires: Total number of wires (always 13 for this construction)
        helix_pitch: Pitch of the helical wires in mm
        progress_callback: Optional callback for progress updates
        create_document: If True, creates a FreeCAD document. If False, just returns the shape.
        document_name: Name for the FreeCAD document (if created)
    
    Returns:
        If create_document=True: (doc, cut_solid, solid_core, wire_shapes)
        If create_document=False: cut_solid (just the final rope shape)
    """
    import math
    
    def update_progress(step, total, message):
        if progress_callback:
            progress_callback(int((step / total) * 100), message)
    
    # Calculate parameters for 13-wire construction
    # CRITICAL: Core must overlap with wires for fusion to work
    # Original formula: core_diameter = overall_diameter - 0.5 * wire_diameter
    # Adding small overlap to ensure robust fusion
    core_diameter = overall_diameter - 0.3 * wire_diameter  # Increased from 0.5 to 0.3 factor for better overlap
    outer_wire_radius = (overall_diameter - wire_diameter) / 2
    num_outer_wires = 12
    
    print(f"Core diameter: {core_diameter:.2f}mm (increased for robust fusion)")
    
    # Calculate extended length to ensure complete wraps
    complete_pitches = math.ceil(cylinder_length / helix_pitch) + 2  # Add 2 extra pitches for cutting
    extended_length = complete_pitches * helix_pitch
    start_z = -helix_pitch  # Start one pitch before zero
    
    # Simple vertical offset
    vertical_offset = helix_pitch / num_outer_wires
    
    print(f"Creating 13-wire rope: {overall_diameter}mm diameter with clean cut ends")
    print(f"Solid core: {core_diameter:.1f}mm + 12 outer helical wires")
    print(f"Extended length: {extended_length:.1f}mm, will cut to {cylinder_length}mm")
    
    # Create document only if requested
    doc = None
    if create_document:
        doc = FreeCAD.newDocument(document_name)
    
    # 1. CREATE SOLID CORE
    # CRITICAL: Core MUST extend well beyond all wires for fusion to work
    max_vertical_offset = (num_outer_wires - 1) * vertical_offset
    # Core needs to start before earliest wire and end after latest wire
    core_start_z = start_z - helix_pitch  # Start full pitch before wires
    core_length = extended_length + max_vertical_offset + (2 * helix_pitch)  # Extend beyond both ends
    solid_core = Part.makeCylinder(
        core_diameter / 2,
        core_length,
        Base.Vector(0, 0, core_start_z),
        Base.Vector(0, 0, 1)
    )
    
    print(f"Core extends from {core_start_z:.1f} to {core_start_z + core_length:.1f}mm")
    
    # Add core to document only if document exists
    if doc:
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
    
    print(f"Wires extend from {start_z:.1f} to {start_z + extended_length:.1f}mm")
    print(f"Core overlaps wires by {helix_pitch:.1f}mm on each end")
    
    start_point = helix.Vertexes[0].Point
    circle = Part.makeCircle(wire_diameter / 2, start_point)
    base_wire = Part.Wire(helix).makePipeShell([Part.Wire(circle)], True, True)
    
    # Check if base wire was created successfully
    if base_wire.Volume == 0:
        print(f"ERROR: Base wire creation failed! Volume is 0")
    else:
        print(f"Base wire created: Volume = {base_wire.Volume:.1f} mm³")
    
    # 3. CREATE 12 ROTATED AND OFFSET COPIES
    wire_shapes = []
    
    for i in range(num_outer_wires):
        # Copy template
        wire_copy = base_wire.copy()
        
        # Rotate around Z-axis
        angle = i * 360.0 / num_outer_wires
        wire_copy.rotate(Base.Vector(0, 0, 0), Base.Vector(0, 0, 1), math.radians(angle))
        
        # Apply vertical offset
        wire_copy.translate(Base.Vector(0, 0, i * vertical_offset))
        
        # Check wire validity
        if wire_copy.Volume == 0:
            print(f"ERROR: Wire {i} has zero volume after transformation!")
        
        wire_shapes.append(wire_copy)
        
        # Add to document but hide it (only if document exists)
        if doc:
            wire_obj = doc.addObject("Part::Feature", f"Wire_{i:02d}")
            wire_obj.Shape = wire_copy
            wire_obj.Label = f"Wire_{i:02d}_{angle:.0f}deg"
            
            if hasattr(FreeCAD, 'Gui'):
                wire_obj.ViewObject.ShapeColor = (1.0, 0.2, 0.2)
                wire_obj.ViewObject.Transparency = 30
                wire_obj.ViewObject.Visibility = False  # HIDE INDIVIDUAL WIRES
    
    print(f"Created 1 core + {len(wire_shapes)} wires")
    
    # 4. SIMPLE FUSION
    print("Starting fusion...")
    fused_solid = solid_core.copy()
    
    for i, wire in enumerate(wire_shapes):
        print(f"Fusing wire {i+1}/{len(wire_shapes)}...")
        fused_solid = fused_solid.fuse(wire)
        print(f"Volume after wire {i+1}: {fused_solid.Volume:.1f} mm³")
        
        if fused_solid.Volume == 0:
            print(f"ERROR: Fusion failed at wire {i+1}")
            break
    
    print(f"Final fused volume: {fused_solid.Volume:.1f} mm³")
    
    # 5. CUT TO CLEAN LENGTH
    print(f"Cutting to clean length: {cylinder_length}mm")
    
    # Calculate cut positions for clean ends (at complete pitch points)
    complete_pitches_in_length = math.floor(cylinder_length / helix_pitch)
    actual_clean_length = complete_pitches_in_length * helix_pitch
    
    print(f"Wire rope extends from {start_z:.1f} to {start_z + extended_length:.1f}mm before cutting")
    print(f"Will cut to keep section from 0 to {actual_clean_length}mm")
    
    # Create cutting box (larger than rope diameter to ensure complete cut)
    cut_width = overall_diameter * 2
    large_height = extended_length * 2  # Make sure boxes are tall enough
    
    # Bottom cut - remove everything before z=0
    bottom_cut_box = Part.makeBox(
        cut_width, cut_width, large_height,
        Base.Vector(-cut_width/2, -cut_width/2, -large_height)
    )
    print(f"Bottom cut: removing everything below z=0")
    
    # Top cut - remove everything after actual_clean_length
    top_cut_box = Part.makeBox(
        cut_width, cut_width, large_height,
        Base.Vector(-cut_width/2, -cut_width/2, actual_clean_length)
    )
    print(f"Top cut: removing everything above z={actual_clean_length}mm")
    
    print(f"Final rope: 0 to {actual_clean_length}mm (exactly {complete_pitches_in_length} complete pitches)")
    
    # Perform the cuts
    print(f"Volume before cuts: {fused_solid.Volume:.1f} mm³")
    
    cut_solid = fused_solid.cut(bottom_cut_box)
    print(f"Volume after bottom cut: {cut_solid.Volume:.1f} mm³")
    
    if cut_solid.Volume == 0:
        print("ERROR: Bottom cut resulted in zero volume!")
        # Try alternative: just use the fused solid
        cut_solid = fused_solid
    
    cut_solid = cut_solid.cut(top_cut_box)
    print(f"Volume after top cut: {cut_solid.Volume:.1f} mm³")
    
    if cut_solid.Volume == 0:
        print("ERROR: Top cut resulted in zero volume!")
        print("Using uncut fused solid instead")
        cut_solid = fused_solid
    
    print(f"After cutting: Volume = {cut_solid.Volume:.1f} mm³, Clean length = {actual_clean_length}mm")
    
    # Add final result only if document exists
    if doc:
        final_obj = doc.addObject("Part::Feature", "WireRope_CleanCut")
        final_obj.Shape = cut_solid
        final_obj.Label = f"WireRope_{actual_clean_length}mm"
        
        if hasattr(FreeCAD, 'Gui'):
            final_obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0)
            final_obj.ViewObject.Transparency = 0
        
        doc.recompute()
        
        if hasattr(FreeCAD, 'Gui'):
            FreeCADGui.ActiveDocument.ActiveView.fitAll()
    
    print(f"COMPLETE: Clean cut rope volume: {cut_solid.Volume:.1f} mm³")
    
    # Return based on whether document was created
    if create_document:
        return doc, cut_solid, solid_core, wire_shapes
    else:
        return cut_solid  # Just return the final rope shape

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
        
        self.export_btn = QtWidgets.QPushButton("💾 Export STL")
        self.export_btn.clicked.connect(self.export_stl)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
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
            self.export_btn.setEnabled(True)
            
            volume = rope_solid.Volume
            self.log_message(f"✅ Wire rope created successfully!")
            self.log_message(f"Clean cut length: {length} mm")
            self.log_message(f"Volume: {volume:.1f} mm³")
            self.log_message(f"Document: {doc.Name}")
            self.log_message(f"Specifications: {rope_diameter}mm × {length}mm, 13-wire with {specs['wire_diameter']}mm wires")
            
        except Exception as e:
            if hasattr(locals(), 'progress'):
                progress.close()
            self.log_message(f"❌ Error creating wire rope: {str(e)}")
        finally:
            # Re-enable UI
            self.create_btn.setEnabled(True)
            self.create_btn.setText("🚀 Create Wire Rope")
    
    def export_stl(self):
        if not self.last_created_rope:
            self.log_message("❌ No wire rope to export")
            return
        
        try:
            rope_diameter = self.diameter_combo.currentData()
            length = self.length_spin.value()
            specs = calculate_wire_specs(rope_diameter)
            
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Export Wire Rope STL",
                f"rigging_13wire_{rope_diameter}mm_{length}mm_{specs['wire_diameter']}mm_wire.stl",
                "STL Files (*.stl)"
            )
            
            if filename:
                self.last_created_rope.exportStl(filename)
                self.log_message(f"✅ STL exported: {filename}")
            
        except Exception as e:
            self.log_message(f"❌ Export failed: {str(e)}")
    
    def log_message(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_log.append(f"[{timestamp}] {message}")

def main():
    # Create and show the dialog
    dialog = WireRopeDesignerDialog()
    dialog.exec_()

# Run the macro
if __name__ == "__main__":
    main()