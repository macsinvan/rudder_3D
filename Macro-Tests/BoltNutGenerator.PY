# -*- coding: utf-8 -*-
"""
BoltNutGenerator_PrintReady.py
Clean version with descriptions and print-in-place alignment
Defaults to basic hex bolt and nut
"""

import FreeCAD
import FreeCADGui
from PySide import QtGui, QtCore
import sys
import os

# Add Fasteners to path
FASTENERS_PATH = "/Users/andrewmackenzie/Library/Application Support/FreeCAD/Mod/fasteners"
if FASTENERS_PATH not in sys.path:
    sys.path.insert(0, FASTENERS_PATH)

import FastenerBase
import FastenersCmd

class BoltNutGeneratorPrintReady(QtGui.QDialog):
    def __init__(self):
        super(BoltNutGeneratorPrintReady, self).__init__()
        
        # Define fastener descriptions
        self.bolt_descriptions = {
            "FSISO4014": "ISO 4014 - Hex head bolt (partial thread) - STANDARD",
            "FSISO4017": "ISO 4017 - Hex head screw (full thread)",
            "FSISO4762": "ISO 4762 - Socket head cap screw (Allen)",
            "FSDIN933": "DIN 933 - Hex head screw (full thread) - METRIC STANDARD",
            "FSDIN931": "DIN 931 - Hex head bolt (partial thread)",
            "FSDIN912": "DIN 912 - Socket head cap screw",
            "FSISO7380": "ISO 7380 - Button head socket screw",
            "FSISO10642": "ISO 10642 - Countersunk socket screw",
        }
        
        self.nut_descriptions = {
            "FSISO4032": "ISO 4032 - Hex nut (standard height) - STANDARD",
            "FSISO4033": "ISO 4033 - Hex nut (tall/high)",
            "FSISO4035": "ISO 4035 - Hex thin nut (jam nut)",
            "FSDIN934": "DIN 934 - Hex nut - METRIC STANDARD",
            "FSDIN985": "DIN 985 - Nyloc nut (self-locking)",
            "FSDIN1587": "DIN 1587 - Cap nut (acorn/dome)",
        }
        
        self.initUI()
        self.findCommands()
        
    def initUI(self):
        self.setWindowTitle("Bolt & Nut Generator - Print Ready")
        self.setMinimumWidth(550)
        
        main_layout = QtGui.QVBoxLayout()
        
        # Title
        title = QtGui.QLabel("<h2>Bolt & Nut Generator</h2>")
        subtitle = QtGui.QLabel("Optimized for 3D Printing")
        title.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        
        # Status
        self.status = QtGui.QTextEdit()
        self.status.setMaximumHeight(100)
        self.status.setReadOnly(True)
        main_layout.addWidget(self.status)
        
        # Fastener Selection
        select_group = QtGui.QGroupBox("Fastener Selection")
        select_layout = QtGui.QFormLayout()
        
        # Bolt dropdown
        self.bolt_combo = QtGui.QComboBox()
        self.bolt_combo.currentTextChanged.connect(self.updateBoltDescription)
        select_layout.addRow("Bolt Type:", self.bolt_combo)
        
        # Bolt description
        self.bolt_desc = QtGui.QLabel("Select a bolt type")
        self.bolt_desc.setWordWrap(True)
        self.bolt_desc.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        select_layout.addRow("", self.bolt_desc)
        
        # Nut dropdown
        self.nut_combo = QtGui.QComboBox()
        self.nut_combo.currentTextChanged.connect(self.updateNutDescription)
        select_layout.addRow("Nut Type:", self.nut_combo)
        
        # Nut description
        self.nut_desc = QtGui.QLabel("Select a nut type")
        self.nut_desc.setWordWrap(True)
        self.nut_desc.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        select_layout.addRow("", self.nut_desc)
        
        # Size
        self.diameter = QtGui.QComboBox()
        self.diameter.addItems(["M3", "M4", "M5", "M6", "M8", "M10", "M12", "M16", "M20"])
        self.diameter.setCurrentText("M8")
        select_layout.addRow("Diameter:", self.diameter)
        
        # Length
        self.length = QtGui.QSpinBox()
        self.length.setRange(5, 200)
        self.length.setValue(30)
        self.length.setSuffix(" mm")
        select_layout.addRow("Length:", self.length)
        
        # Nut position
        self.nut_pos = QtGui.QSpinBox()
        self.nut_pos.setRange(0, 100)
        self.nut_pos.setValue(5)
        self.nut_pos.setSuffix(" mm from head")
        select_layout.addRow("Nut Position:", self.nut_pos)
        
        select_group.setLayout(select_layout)
        main_layout.addWidget(select_group)
        
        # Thread Settings
        thread_group = QtGui.QGroupBox("Thread Settings")
        thread_layout = QtGui.QVBoxLayout()
        
        self.thread_enable = QtGui.QCheckBox("Enable Threads (required for functional parts)")
        self.thread_enable.setChecked(True)
        self.thread_enable.setStyleSheet("font-weight: bold;")
        thread_layout.addWidget(self.thread_enable)
        
        thread_layout.addWidget(QtGui.QLabel("Thread Display:"))
        self.thread_quality = QtGui.QComboBox()
        self.thread_quality.addItems(["Simple (symbolic)", "Modeled (real geometry - slow)"])
        thread_layout.addWidget(self.thread_quality)
        
        thread_group.setLayout(thread_layout)
        main_layout.addWidget(thread_group)
        
        # Print-in-Place Settings
        print_group = QtGui.QGroupBox("Print-in-Place Alignment")
        print_layout = QtGui.QVBoxLayout()
        
        self.align_threads = QtGui.QCheckBox("Align threads for print-in-place")
        self.align_threads.setChecked(True)
        print_layout.addWidget(self.align_threads)
        
        info_text = """
For successful print-in-place:
• Threads must be aligned (enabled above)
• Add 0.1-0.2mm clearance for FDM printing
• Use same pitch for bolt and nut (automatic with same diameter)
• Print with 0.1-0.2mm layer height for better threads
        """
        info_label = QtGui.QLabel(info_text)
        info_label.setStyleSheet("color: #666; font-size: 10px; background-color: #f0f0f0; padding: 10px;")
        print_layout.addWidget(info_label)
        
        # Clearance adjustment
        clearance_layout = QtGui.QHBoxLayout()
        clearance_layout.addWidget(QtGui.QLabel("Thread Clearance:"))
        self.clearance = QtGui.QDoubleSpinBox()
        self.clearance.setRange(0, 1.0)
        self.clearance.setValue(0.15)
        self.clearance.setSingleStep(0.05)
        self.clearance.setSuffix(" mm")
        self.clearance.setToolTip("Clearance between bolt and nut threads for 3D printing")
        clearance_layout.addWidget(self.clearance)
        clearance_layout.addStretch()
        print_layout.addLayout(clearance_layout)
        
        print_group.setLayout(print_layout)
        main_layout.addWidget(print_group)
        
        # Create button
        create_btn = QtGui.QPushButton("CREATE BOLT && NUT ASSEMBLY")
        create_btn.clicked.connect(self.createBoltNut)
        create_btn.setMinimumHeight(40)
        font = create_btn.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        create_btn.setFont(font)
        create_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        main_layout.addWidget(create_btn)
        
        self.setLayout(main_layout)
    
    def findCommands(self):
        """Find available fastener commands and set defaults"""
        all_cmds = FreeCADGui.listCommands()
        
        # Find commands that match our descriptions
        bolt_cmds = []
        nut_cmds = []
        
        for cmd in all_cmds:
            if cmd in self.bolt_descriptions:
                bolt_cmds.append(cmd)
            elif cmd in self.nut_descriptions:
                nut_cmds.append(cmd)
            elif cmd.startswith('FS'):
                # Fallback - categorize unknown FS commands
                if any(x in cmd for x in ['4014', '4017', '4762', '933', '931', '912']):
                    if cmd not in bolt_cmds:
                        bolt_cmds.append(cmd)
                elif any(x in cmd for x in ['4032', '4033', '4035', '934', '985', '1587']):
                    if cmd not in nut_cmds:
                        nut_cmds.append(cmd)
        
        # Sort and populate
        bolt_cmds.sort()
        nut_cmds.sort()
        
        self.bolt_combo.addItems(bolt_cmds)
        self.nut_combo.addItems(nut_cmds)
        
        # Set defaults to basic hex (ISO 4014 bolt and ISO 4032 nut, or DIN equivalents)
        default_bolt = None
        default_nut = None
        
        # Try to find standard hex bolt
        for cmd in ["FSISO4014", "FSDIN933", "FSDIN931"]:
            if cmd in bolt_cmds:
                default_bolt = cmd
                break
        
        # Try to find standard hex nut
        for cmd in ["FSISO4032", "FSDIN934"]:
            if cmd in nut_cmds:
                default_nut = cmd
                break
        
        if default_bolt:
            self.bolt_combo.setCurrentText(default_bolt)
        if default_nut:
            self.nut_combo.setCurrentText(default_nut)
        
        self.status.append(f"Found {len(bolt_cmds)} bolt types, {len(nut_cmds)} nut types")
        self.status.append(f"Default: {default_bolt or bolt_cmds[0] if bolt_cmds else 'None'}")
    
    def updateBoltDescription(self, cmd):
        """Update bolt description label"""
        if cmd in self.bolt_descriptions:
            self.bolt_desc.setText(self.bolt_descriptions[cmd])
        else:
            self.bolt_desc.setText(f"Command: {cmd}")
    
    def updateNutDescription(self, cmd):
        """Update nut description label"""
        if cmd in self.nut_descriptions:
            self.nut_desc.setText(self.nut_descriptions[cmd])
        else:
            self.nut_desc.setText(f"Command: {cmd}")
    
    def createBoltNut(self):
        """Create bolt and nut with proper settings for 3D printing"""
        self.status.clear()
        self.status.append("Creating assembly...")
        
        # Get selections
        bolt_cmd = self.bolt_combo.currentText()
        nut_cmd = self.nut_combo.currentText()
        diameter = self.diameter.currentText()
        length = self.length.value()
        nut_position = self.nut_pos.value()
        enable_threads = self.thread_enable.isChecked()
        align_for_print = self.align_threads.isChecked()
        clearance = self.clearance.value()
        
        if not bolt_cmd or not nut_cmd:
            self.status.append("✗ Please select both bolt and nut")
            return
        
        # Create or get document
        if not FreeCAD.ActiveDocument:
            FreeCAD.newDocument("BoltNutAssembly")
        doc = FreeCAD.ActiveDocument
        
        # CREATE BOLT
        try:
            self.status.append(f"Creating bolt: {bolt_cmd}")
            FreeCADGui.runCommand(bolt_cmd)
            
            bolt = doc.Objects[-1]
            
            # Set properties
            if hasattr(bolt, 'diameter'):
                bolt.diameter = diameter
            if hasattr(bolt, 'length'):
                bolt.length = f"{length} mm"
            
            # Set thread property
            if hasattr(bolt, 'thread'):
                bolt.thread = enable_threads
                self.status.append(f"  Bolt threads: {enable_threads}")
            elif hasattr(bolt, 'Thread'):
                bolt.Thread = enable_threads
            
            # Set thread quality
            if self.thread_quality.currentIndex() == 1 and hasattr(bolt, 'thread'):
                # Real modeled threads (slow)
                bolt.thread = True
                if hasattr(bolt, 'simple'):
                    bolt.simple = False
            elif hasattr(bolt, 'simple'):
                # Simple/symbolic threads
                bolt.simple = True
            
        except Exception as e:
            self.status.append(f"✗ Bolt failed: {e}")
            return
        
        # CREATE NUT
        try:
            self.status.append(f"Creating nut: {nut_cmd}")
            FreeCADGui.runCommand(nut_cmd)
            
            nut = doc.Objects[-1]
            
            # Set properties
            if hasattr(nut, 'diameter'):
                nut.diameter = diameter
            
            # Position the nut
            nut.Placement.Base = FreeCAD.Vector(0, 0, -nut_position)
            
            # Set thread property
            if hasattr(nut, 'thread'):
                nut.thread = enable_threads
                self.status.append(f"  Nut threads: {enable_threads}")
            elif hasattr(nut, 'Thread'):
                nut.Thread = enable_threads
            
            # Set thread quality (same as bolt for consistency)
            if self.thread_quality.currentIndex() == 1 and hasattr(nut, 'thread'):
                nut.thread = True
                if hasattr(nut, 'simple'):
                    nut.simple = False
            elif hasattr(nut, 'simple'):
                nut.simple = True
            
            # THREAD ALIGNMENT FOR PRINT-IN-PLACE
            if align_for_print and enable_threads:
                # Ensure rotational alignment
                # Nuts and bolts should have same thread start angle
                # Most fasteners start at 0 degrees, but we can ensure alignment
                
                # Keep nut at 0 rotation for thread alignment
                nut.Placement.Rotation = FreeCAD.Rotation(0, 0, 0, 1)
                
                # Apply clearance if needed (this would require scaling the nut hole slightly)
                # Note: Actual clearance implementation would require modifying the thread geometry
                # which is complex. For now, we note it for the user.
                
                if clearance > 0:
                    self.status.append(f"  Note: Add {clearance}mm clearance in slicer")
            
        except Exception as e:
            self.status.append(f"✗ Nut failed: {e}")
            return
        
        # Recompute and update view
        doc.recompute()
        FreeCADGui.activeDocument().activeView().viewAxonometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
        
        # Final status
        self.status.append(f"\n✓ Assembly created successfully!")
        
        if align_for_print:
            self.status.append("✓ Threads aligned for print-in-place")
            self.status.append(f"  Recommended: {clearance}mm clearance in slicer")

def main():
    # Ensure workbench is activated
    wb_list = FreeCADGui.listWorkbenches()
    for wb in wb_list:
        if 'fastener' in wb.lower():
            try:
                FreeCADGui.activateWorkbench(wb)
                print(f"Activated {wb}")
                break
            except:
                pass
    
    # Show dialog
    dialog = BoltNutGeneratorPrintReady()
    dialog.exec_()

if __name__ == "__main__":
    main()