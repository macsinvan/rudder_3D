# -*- coding: utf-8 -*-
"""
TableLegLeveler_Top.py
Creates the top piece of the table leg leveler with female threads
Uses boolean cuts with a threaded rod to create the female thread
"""

import FreeCAD
import FreeCADGui
from PySide import QtGui, QtCore
import Part

class LevelerTop(QtGui.QDialog):
    def __init__(self):
        super(LevelerTop, self).__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Table Leg Leveler - Top Piece")
        self.setMinimumWidth(450)
        
        layout = QtGui.QVBoxLayout()
        
        # Title
        title = QtGui.QLabel("<h2>Leveler Top with Female Thread</h2>")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)
        
        # Parameters
        params = QtGui.QGroupBox("Dimensions (mm)")
        form = QtGui.QFormLayout()
        
        # Outer cylinder
        self.outer_d = QtGui.QDoubleSpinBox()
        self.outer_d.setRange(20, 100)
        self.outer_d.setValue(36)
        self.outer_d.setSuffix(" mm")
        form.addRow("Outer Diameter:", self.outer_d)
        
        self.height = QtGui.QDoubleSpinBox()
        self.height.setRange(20, 100)
        self.height.setValue(32)
        self.height.setSuffix(" mm")
        form.addRow("Total Height:", self.height)
        
        # Thread parameters
        self.thread_d = QtGui.QDoubleSpinBox()
        self.thread_d.setRange(10, 50)
        self.thread_d.setValue(26)
        self.thread_d.setSuffix(" mm")
        self.thread_d.setToolTip("Base thread diameter (will add clearance)")
        form.addRow("Thread Diameter:", self.thread_d)
        
        self.clearance = QtGui.QDoubleSpinBox()
        self.clearance.setRange(0, 1)
        self.clearance.setValue(0.3)
        self.clearance.setSingleStep(0.1)
        self.clearance.setSuffix(" mm")
        self.clearance.setToolTip("Clearance for smooth operation")
        form.addRow("Thread Clearance:", self.clearance)
        
        # Top indent
        self.indent_d = QtGui.QDoubleSpinBox()
        self.indent_d.setRange(10, 50)
        self.indent_d.setValue(30)
        self.indent_d.setSuffix(" mm")
        form.addRow("Indent Diameter:", self.indent_d)
        
        self.indent_depth = QtGui.QDoubleSpinBox()
        self.indent_depth.setRange(1, 10)
        self.indent_depth.setValue(2)
        self.indent_depth.setSuffix(" mm")
        form.addRow("Indent Depth:", self.indent_depth)
        
        params.setLayout(form)
        layout.addWidget(params)
        
        # Status
        self.status = QtGui.QTextEdit()
        self.status.setMaximumHeight(150)
        self.status.setReadOnly(True)
        font = QtGui.QFont("Courier", 10)
        self.status.setFont(font)
        layout.addWidget(self.status)
        
        # Create button
        create_btn = QtGui.QPushButton("CREATE TOP PIECE")
        create_btn.clicked.connect(self.createTop)
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
    
    def log(self, msg):
        self.status.append(msg)
        FreeCAD.Console.PrintMessage(msg + "\n")
        QtGui.QApplication.processEvents()
    
    def createTop(self):
        """Create top piece with female threads using boolean cuts"""
        self.status.clear()
        self.log("Creating top piece with female thread...")
        
        outer_diameter = self.outer_d.value()
        height = self.height.value()
        thread_diameter = self.thread_d.value()
        clearance = self.clearance.value()
        indent_diameter = self.indent_d.value()
        indent_depth = self.indent_depth.value()
        
        # Calculate actual cutting diameter
        cutting_diameter = thread_diameter + clearance
        
        # Create or get document
        if not FreeCAD.ActiveDocument:
            FreeCAD.newDocument("LegLevelerTop")
        doc = FreeCAD.ActiveDocument
        
        try:
            # Activate Fasteners Workbench
            self.log("Activating Fasteners Workbench...")
            FreeCADGui.activateWorkbench('FastenersWorkbench')
            
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
            
            # Set length to go through the part (leave 4mm wall at top)
            thread_length = height - 4
            if hasattr(thread_rod, 'Length'):
                thread_rod.Length = f'{thread_length} mm'
            
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
            
            # Calculate and display info
            wall_thickness = (outer_diameter - cutting_diameter) / 2
            self.log("\n" + "="*40)
            self.log("✅ TOP PIECE CREATED SUCCESSFULLY!")
            self.log(f"Outer diameter: {outer_diameter}mm")
            self.log(f"Height: {height}mm")
            self.log(f"Female thread: {cutting_diameter}mm (with {clearance}mm clearance)")
            self.log(f"Wall thickness: {wall_thickness:.1f}mm")
            self.log(f"Top indent: {indent_diameter}×{indent_depth}mm")
            self.log("="*40)
            
            # Set view
            FreeCADGui.activeDocument().activeView().viewAxonometric()
            FreeCADGui.SendMsgToActiveView("ViewFit")
            
            # Color it differently from base
            top_obj.ViewObject.ShapeColor = (0.2, 0.6, 0.8)
            
        except Exception as e:
            self.log(f"❌ Error: {e}")
            import traceback
            self.log("Details:")
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    self.log(f"  {line}")

def main():
    dialog = LevelerTop()
    dialog.exec_()

if __name__ == "__main__":
    main()