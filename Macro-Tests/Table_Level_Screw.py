# -*- coding: utf-8 -*-
"""
TableLegLeveler_Integrated.py
Integrated version combining both Top (female thread) and Bottom (male thread) pieces
Simplified input with only 3 parameters
"""

import FreeCAD
import FreeCADGui
from PySide import QtGui, QtCore
import Part
import Mesh

class IntegratedLeveler(QtGui.QDialog):
    def __init__(self):
        super(IntegratedLeveler, self).__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Table Leg Leveler - Complete System")
        self.setMinimumWidth(450)
        
        layout = QtGui.QVBoxLayout()
        
        # Title
        title = QtGui.QLabel("<h2>Table Leg Leveler - Simplified</h2>")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)
        
        # Part selection
        selection = QtGui.QGroupBox("Select Parts to Create")
        sel_layout = QtGui.QHBoxLayout()
        
        self.create_top = QtGui.QCheckBox("Top Piece (Female)")
        self.create_top.setChecked(True)
        sel_layout.addWidget(self.create_top)
        
        self.create_bottom = QtGui.QCheckBox("Bottom Piece (Male)")
        self.create_bottom.setChecked(True)
        sel_layout.addWidget(self.create_bottom)
        
        self.export_stl = QtGui.QCheckBox("Export as STL")
        self.export_stl.setChecked(False)
        sel_layout.addWidget(self.export_stl)
        
        selection.setLayout(sel_layout)
        layout.addWidget(selection)
        
        # Simplified Parameters - Only 3 inputs
        params = QtGui.QGroupBox("Dimensions (mm)")
        form = QtGui.QFormLayout()
        
        self.min_height = QtGui.QDoubleSpinBox()
        self.min_height.setRange(20, 200)
        self.min_height.setValue(40)
        self.min_height.setSuffix(" mm")
        self.min_height.setToolTip("Total height when fully collapsed")
        form.addRow("Minimum Height:", self.min_height)
        
        self.outer_d = QtGui.QDoubleSpinBox()
        self.outer_d.setRange(20, 100)
        self.outer_d.setValue(36)
        self.outer_d.setSuffix(" mm")
        self.outer_d.setToolTip("Outer diameter of top piece")
        form.addRow("Outer Diameter:", self.outer_d)
        
        self.indent_depth = QtGui.QDoubleSpinBox()
        self.indent_depth.setRange(1, 10)
        self.indent_depth.setValue(6)
        self.indent_depth.setSuffix(" mm")
        self.indent_depth.setToolTip("Depth of top indent")
        form.addRow("Indent Depth:", self.indent_depth)
        
        params.setLayout(form)
        layout.addWidget(params)
        
        # Calculated Values Display
        calc_display = QtGui.QGroupBox("Calculated Values")
        calc_layout = QtGui.QFormLayout()
        
        self.calc_info = QtGui.QLabel()
        self.calc_info.setWordWrap(True)
        calc_layout.addWidget(self.calc_info)
        calc_display.setLayout(calc_layout)
        layout.addWidget(calc_display)
        
        # Update calculations when values change
        self.min_height.valueChanged.connect(self.updateCalculations)
        self.outer_d.valueChanged.connect(self.updateCalculations)
        self.indent_depth.valueChanged.connect(self.updateCalculations)
        self.updateCalculations()
        
        # Status
        self.status = QtGui.QTextEdit()
        self.status.setMaximumHeight(150)
        self.status.setReadOnly(True)
        font = QtGui.QFont("Courier", 10)
        self.status.setFont(font)
        layout.addWidget(self.status)
        
        # Create button
        create_btn = QtGui.QPushButton("CREATE SELECTED PARTS")
        create_btn.clicked.connect(self.createParts)
        create_btn.setMinimumHeight(40)
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        layout.addWidget(create_btn)
        
        self.setLayout(layout)
    
    def updateCalculations(self):
        """Update calculated values display"""
        outer_d = self.outer_d.value()
        min_height = self.min_height.value()
        indent_depth = self.indent_depth.value()
        
        # Calculate derived values
        thread_d = outer_d - 8  # 4mm walls
        indent_d = outer_d - 4  # 2mm walls
        clearance = 0.2
        top_height = min_height - 10  # Allow some thread engagement
        thread_length = min_height - 15  # Thread length for adjustment
        
        # Display calculations
        info_text = f"""Thread Diameter: {thread_d:.1f}mm (4mm walls)
Indent Diameter: {indent_d:.1f}mm (2mm walls)
Top Piece Height: {top_height:.1f}mm
Thread Penetration: {top_height - indent_depth - 4:.1f}mm (4mm below indent)
Thread Length: {thread_length:.1f}mm
Maximum Extension: {thread_length:.1f}mm
Practical Extension: {thread_length/2:.1f}mm (50% recommended)"""
        
        self.calc_info.setText(info_text)
    
    def log(self, msg):
        self.status.append(msg)
        FreeCAD.Console.PrintMessage(msg + "\n")
        QtGui.QApplication.processEvents()
    
    def createParts(self):
        """Create selected parts"""
        self.status.clear()
        
        if not self.create_top.isChecked() and not self.create_bottom.isChecked():
            self.log("Please select at least one part to create!")
            return
        
        # Create or get document
        if not FreeCAD.ActiveDocument:
            FreeCAD.newDocument("TableLegLeveler")
        doc = FreeCAD.ActiveDocument
        
        # Activate Fasteners Workbench
        self.log("Activating Fasteners Workbench...")
        FreeCADGui.activateWorkbench('FastenersWorkbench')
        
        # Store created objects for STL export
        self.created_objects = []
        
        if self.create_bottom.isChecked():
            self.log("\n" + "="*40)
            self.log("Creating BOTTOM piece (fully threaded)...")
            bottom_obj = self.createBottomPiece(doc)
            if bottom_obj:
                self.created_objects.append(("LevelerBottom", bottom_obj))
        
        if self.create_top.isChecked():
            self.log("\n" + "="*40)
            self.log("Creating TOP piece with female thread...")
            top_obj = self.createTopPiece(doc)
            if top_obj:
                self.created_objects.append(("LevelerTop", top_obj))
        
        # Set view
        FreeCADGui.activeDocument().activeView().viewAxonometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
        
        self.log("\n" + "="*40)
        self.log("✅ ALL SELECTED PARTS CREATED SUCCESSFULLY!")
        
        # Export STL if requested
        if self.export_stl.isChecked() and self.created_objects:
            self.exportSTL()
    
    def createBottomPiece(self, doc):
        """Create bottom piece - fully threaded with coin slot"""
        # Calculate derived values
        outer_d = self.outer_d.value()
        min_height = self.min_height.value()
        
        thread_diameter = outer_d - 8  # 4mm walls
        thread_length = min_height - 15  # Full thread length
        
        try:
            # Create threaded rod (no base cylinder anymore)
            self.log(f"Creating fully threaded rod: {thread_diameter}×{thread_length}mm")
            FreeCADGui.runCommand('FSThreadedRod', 0)
            
            # Get the created object
            doc.recompute()
            
            # Find the threaded rod object
            thread_obj = None
            for obj in doc.Objects:
                if 'ThreadedRod' in obj.Name or 'Screw' in obj.Name:
                    thread_obj = obj
                    break
            
            if not thread_obj:
                thread_obj = doc.Objects[-1]
            
            # Configure the threaded rod
            thread_obj.Diameter = "Custom"
            doc.recompute()
            
            thread_obj.DiameterCustom = f'{thread_diameter} mm'
            doc.recompute()
            
            thread_obj.Thread = True
            
            # Set length
            if hasattr(thread_obj, 'Length'):
                thread_obj.Length = f'{thread_length} mm'
            
            # Position at origin
            thread_obj.Placement.Base = FreeCAD.Vector(0, 0, 0)
            doc.recompute()
            
            # Create coin slot at bottom
            self.log("Adding coin slot at bottom...")
            euro_diameter = 23.0  # Euro coin diameter in mm
            slot_thickness = 2.0  # Slot thickness
            slot_depth = 4.0  # How deep into the threaded rod
            
            # Create a disc (cylinder) for the coin slot
            slot_disc = Part.makeCylinder(
                euro_diameter/2,  # Radius of Euro coin
                slot_thickness,   # Thickness of slot
                FreeCAD.Vector(0, -slot_thickness/2, slot_depth/2),  # Position at bottom
                FreeCAD.Vector(0, 1, 0)  # Orient along Y axis (horizontal)
            )
            
            # Cut the slot from the threaded rod
            thread_shape = thread_obj.Shape
            final_shape = thread_shape.cut(slot_disc)
            
            # Create final object
            final_obj = doc.addObject("Part::Feature", "LevelerBottom")
            final_obj.Shape = final_shape
            
            # Hide original thread
            thread_obj.ViewObject.Visibility = False
            
            # Color it
            final_obj.ViewObject.ShapeColor = (0.8, 0.4, 0.2)
            
            doc.recompute()
            
            self.log(f"✅ Bottom piece created: Thread {thread_diameter}×{thread_length}mm")
            self.log(f"   with Euro coin slot (⌀{euro_diameter}mm × {slot_thickness}mm)")
            
            return final_obj
            
        except Exception as e:
            self.log(f"❌ Error creating bottom: {e}")
            import traceback
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            return None
    
    def createTopPiece(self, doc):
        """Create top piece with female thread - exact logic from original"""
        # Calculate derived values
        outer_diameter = self.outer_d.value()
        min_height = self.min_height.value()
        indent_depth = self.indent_depth.value()
        
        thread_diameter = outer_diameter - 8  # 4mm walls
        clearance = 0.2  # Fixed clearance
        indent_diameter = outer_diameter - 4  # 2mm walls
        height = min_height - 10  # Top piece height
        
        # Calculate actual cutting diameter
        cutting_diameter = thread_diameter + clearance
        
        try:
            # 1. Create main solid cylinder
            self.log(f"Creating main cylinder: {outer_diameter}×{height}mm")
            main_cylinder = Part.makeCylinder(
                outer_diameter/2,
                height,
                FreeCAD.Vector(0, 0, 0),
                FreeCAD.Vector(0, 0, 1)
            )
            
            # 2. Create indent cylinder for cutting
            self.log(f"Creating indent: {indent_diameter}×{indent_depth}mm")
            indent_cylinder = Part.makeCylinder(
                indent_diameter/2,
                indent_depth,
                FreeCAD.Vector(0, 0, height - indent_depth),
                FreeCAD.Vector(0, 0, 1)
            )
            
            # 3. Cut indent from main cylinder
            self.log("Cutting indent from top...")
            main_with_indent = main_cylinder.cut(indent_cylinder)
            
            # 4. Create threaded rod for cutting
            self.log(f"Creating threaded rod for cutting...")
            self.log(f"  Thread diameter: {cutting_diameter}mm (includes {clearance}mm clearance)")
            
            # Create FSThreadedRod
            FreeCADGui.runCommand('FSThreadedRod', 0)
            
            # Get the created rod (last object)
            doc.recompute()
            thread_rod = doc.Objects[-1]
            
            # Configure the threaded rod
            thread_rod.Diameter = "Custom"
            doc.recompute()
            thread_rod.DiameterCustom = f'{cutting_diameter} mm'
            thread_rod.Thread = True
            
            # Set length to go through the part (leave 4mm wall below indent)
            thread_length = height - indent_depth - 4
            actual_length = thread_length + 5  # Add 5mm to ensure complete threads at entry
            if hasattr(thread_rod, 'Length'):
                thread_rod.Length = f'{actual_length} mm'
            
            # Position rod to penetrate from bottom (assuming rod reference is at its top)
            thread_rod.Placement.Base = FreeCAD.Vector(0, 0, thread_length)
            doc.recompute()
            
            # Get the thread shape
            thread_shape = thread_rod.Shape
            
            # 5. Boolean cut the thread from the main cylinder
            self.log("Cutting female thread...")
            final_shape = main_with_indent.cut(thread_shape)
            
            # 6. Create the final object
            top_obj = doc.addObject("Part::Feature", "LevelerTop")
            top_obj.Shape = final_shape
            
            # Hide the cutting tool
            thread_rod.ViewObject.Visibility = False
            
            # Position it higher if bottom was created
            if self.create_bottom.isChecked():
                # Move top piece up for visualization
                thread_length_bottom = self.min_height.value() - 15
                top_obj.Placement.Base = FreeCAD.Vector(0, 0, thread_length_bottom + 10)
            
            # Color it differently from base
            top_obj.ViewObject.ShapeColor = (0.2, 0.6, 0.8)
            
            # Calculate and display info
            wall_thickness = (outer_diameter - cutting_diameter) / 2
            self.log(f"✅ Top piece created: {outer_diameter}×{height}mm")
            self.log(f"   Female thread: {cutting_diameter}mm (with {clearance}mm clearance)")
            self.log(f"   Wall thickness: {wall_thickness:.1f}mm")
            self.log(f"   Top indent: {indent_diameter}×{indent_depth}mm")
            
            return top_obj
            
        except Exception as e:
            self.log(f"❌ Error creating top: {e}")
            import traceback
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            return None
    
    def exportSTL(self):
        """Export created objects as STL files"""
        self.log("\n" + "="*40)
        self.log("Exporting STL files...")
        
        try:
            import os
            doc_path = FreeCAD.ActiveDocument.FileName
            if doc_path:
                export_dir = os.path.dirname(doc_path)
            else:
                export_dir = os.path.expanduser("~")
            
            for name, obj in self.created_objects:
                if obj and hasattr(obj, 'Shape'):
                    filename = os.path.join(export_dir, f"{name}.stl")
                    mesh = Mesh.Mesh()
                    mesh.addFacets(obj.Shape.tessellate(0.1))
                    mesh.write(filename)
                    self.log(f"✅ Exported: {filename}")
        
        except Exception as e:
            self.log(f"❌ Error exporting STL: {e}")

def main():
    dialog = IntegratedLeveler()
    dialog.exec_()

if __name__ == "__main__":
    main()
