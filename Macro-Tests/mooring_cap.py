"""
FreeCAD Script: Mooring Line Cap with Compression Ring
- Sphere with conical cutout
- Split compression ring with ratchet teeth and internal ridges
- Ring sized to fit cutout with clearance
- Interactive UI for line diameter selection and STL export
"""

import FreeCAD as App
import Part
import Mesh
import math
import os

# Try to import Qt (works in FreeCAD GUI)
try:
    from PySide import QtGui, QtCore
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

# ============================================================================
# UI DIALOG
# ============================================================================

class CapDesignDialog(QtGui.QDialog):
    """Dialog for cap design parameters"""
    
    def __init__(self):
        super(CapDesignDialog, self).__init__()
        self.setWindowTitle("Mooring Line Cap - Design Parameters")
        self.setModal(True)
        
        # Line diameter selection
        diameter_label = QtGui.QLabel("Line Diameter (mm):")
        self.diameter_combo = QtGui.QComboBox()
        self.diameter_combo.addItems(["6", "8", "10", "12", "14", "16", "18", "20"])
        self.diameter_combo.setCurrentIndex(3)  # Default to 12mm
        
        # Export STL checkbox
        self.export_checkbox = QtGui.QCheckBox("Export STL files")
        self.export_checkbox.setChecked(True)  # Default checked
        
        # Buttons
        button_box = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Layout
        layout = QtGui.QVBoxLayout()
        
        diameter_layout = QtGui.QHBoxLayout()
        diameter_layout.addWidget(diameter_label)
        diameter_layout.addWidget(self.diameter_combo)
        
        layout.addLayout(diameter_layout)
        layout.addWidget(self.export_checkbox)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_parameters(self):
        """Return selected parameters"""
        return {
            'line_diameter': float(self.diameter_combo.currentText()),
            'export_stl': self.export_checkbox.isChecked()
        }


def show_dialog():
    """Show dialog and return parameters, or None if cancelled"""
    if not HAS_GUI:
        # No GUI available, use defaults
        return {'line_diameter': 12.0, 'export_stl': False}
    
    dialog = CapDesignDialog()
    if dialog.exec_() == QtGui.QDialog.Accepted:
        return dialog.get_parameters()
    return None


# ============================================================================
# DESIGN PARAMETERS
# ============================================================================

# Fixed design ratios
SPHERE_RATIO = 2.5
TAPER_ANGLE = 3.5
GAP_WIDTH = 2.0
WALL_THICKNESS = 3.0

# Internal ridges (grip rope)
RIDGE_HEIGHT = 1.0
RIDGE_SPACING = 3.0
RIDGE_WIDTH = 0.5

# External ratchet teeth (one-way lock)
RATCHET_TOOTH_HEIGHT = 0.5
RATCHET_TOOTH_SPACING = 2.0
RATCHET_TOOTH_WIDTH = 0.5

# Clearances
CUTOUT_CLEARANCE = 1.0
LINE_LENGTH = 100.0  # Visualization only


def calculate_dimensions(line_dia):
    """Calculate all dimensions from line diameter"""
    
    # Sphere
    sphere_outer_dia = line_dia * SPHERE_RATIO
    sphere_radius = sphere_outer_dia / 2.0
    
    # Ring dimensions
    ferrule_length = sphere_radius
    taper_rad = math.radians(TAPER_ANGLE)
    radius_increase = ferrule_length * math.tan(taper_rad)
    
    ring_inner_dia = line_dia
    ring_head_outer_dia = ring_inner_dia + (2 * WALL_THICKNESS) - 1.0  # Reduced by 1mm
    ring_base_outer_dia = ring_head_outer_dia + (2 * radius_increase)
    
    ring_head_with_teeth = ring_head_outer_dia + (2 * RATCHET_TOOTH_HEIGHT)
    ring_base_with_teeth = ring_base_outer_dia + (2 * RATCHET_TOOTH_HEIGHT)
    
    # Cutout dimensions
    z_exit = math.sqrt(sphere_radius**2 - (line_dia/2.0)**2)
    diameter_at_exit = line_dia
    
    entry_dia = ring_head_with_teeth + CUTOUT_CLEARANCE
    z_entry = -math.sqrt(sphere_radius**2 - (entry_dia/2.0)**2)
    diameter_at_entry = entry_dia
    
    z_sphere_bottom = -sphere_radius
    
    # Linear interpolation for cone extension
    radius_at_exit = diameter_at_exit / 2.0
    radius_at_entry = diameter_at_entry / 2.0
    radius_at_sphere_bottom = radius_at_exit + (radius_at_entry - radius_at_exit) * \
                             (z_sphere_bottom - z_exit) / (z_entry - z_exit)
    z_sphere_entry_diameter = 2 * radius_at_sphere_bottom
    
    cone_height = z_exit - z_sphere_bottom
    
    # Ring positioning
    ring_head_z = z_entry
    ring_base_z = ring_head_z - ferrule_length
    
    return {
        'line_dia': line_dia,
        'sphere_outer_dia': sphere_outer_dia,
        'sphere_radius': sphere_radius,
        'ferrule_length': ferrule_length,
        'radius_increase': radius_increase,
        'ring_inner_dia': ring_inner_dia,
        'ring_head_outer_dia': ring_head_outer_dia,
        'ring_base_outer_dia': ring_base_outer_dia,
        'ring_head_with_teeth': ring_head_with_teeth,
        'ring_base_with_teeth': ring_base_with_teeth,
        'z_exit': z_exit,
        'diameter_at_exit': diameter_at_exit,
        'z_entry': z_entry,
        'diameter_at_entry': diameter_at_entry,
        'z_sphere_bottom': z_sphere_bottom,
        'radius_at_exit': radius_at_exit,
        'radius_at_entry': radius_at_entry,
        'radius_at_sphere_bottom': radius_at_sphere_bottom,
        'z_sphere_entry_diameter': z_sphere_entry_diameter,
        'cone_height': cone_height,
        'ring_head_z': ring_head_z,
        'ring_base_z': ring_base_z
    }


# ============================================================================
# GEOMETRY CREATION
# ============================================================================

def create_line(dims):
    """Mooring line cylinder"""
    doc = App.ActiveDocument
    
    line = Part.makeCylinder(
        dims['line_dia'] / 2.0,
        LINE_LENGTH,
        App.Vector(0, 0, -LINE_LENGTH/2),
        App.Vector(0, 0, 1)
    )
    
    line_obj = doc.addObject("Part::Feature", "Line")
    line_obj.Shape = line
    line_obj.ViewObject.ShapeColor = (0.6, 0.4, 0.2)
    
    return line_obj


def create_ratchet_tooth_ring(z_position, outer_radius):
    """Single ratchet tooth ring - asymmetric sawtooth for one-way locking"""
    peak_offset = RATCHET_TOOTH_WIDTH * 0.7
    
    base_top = App.Vector(outer_radius, 0, z_position)
    peak = App.Vector(outer_radius + RATCHET_TOOTH_HEIGHT, 0, z_position - peak_offset)
    base_bottom = App.Vector(outer_radius, 0, z_position - RATCHET_TOOTH_WIDTH)
    
    edge1 = Part.LineSegment(base_top, peak).toShape()
    edge2 = Part.LineSegment(peak, base_bottom).toShape()
    edge3 = Part.LineSegment(base_bottom, base_top).toShape()
    
    wire = Part.Wire([edge1, edge2, edge3])
    face = Part.Face(wire)
    
    return face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)


def create_sphere_with_cone(dims):
    """Sphere with conical cutout and ratchet grooves"""
    doc = App.ActiveDocument
    
    solid_sphere = Part.makeSphere(dims['sphere_radius'])
    
    # Top cylinder hole
    top_hole = Part.makeCylinder(
        dims['line_dia'] / 2.0,
        dims['sphere_radius'] - dims['z_exit'] + 5,
        App.Vector(0, 0, dims['z_exit']),
        App.Vector(0, 0, 1)
    )
    
    # Conical cutout
    cone_cutout = Part.makeCone(
        dims['diameter_at_exit'] / 2.0,
        dims['z_sphere_entry_diameter'] / 2.0,
        dims['cone_height'],
        App.Vector(0, 0, dims['z_exit']),
        App.Vector(0, 0, -1)
    )
    
    # Add ratchet grooves
    num_teeth = int(dims['cone_height'] / RATCHET_TOOTH_SPACING)
    ratchet_grooves = None
    
    for i in range(num_teeth):
        z_pos = dims['z_exit'] - (i * RATCHET_TOOTH_SPACING) - RATCHET_TOOTH_WIDTH/2
        
        if z_pos > dims['z_sphere_bottom']:
            t = (dims['z_exit'] - z_pos) / dims['cone_height']
            cutout_radius = dims['radius_at_exit'] + t * (dims['radius_at_sphere_bottom'] - dims['radius_at_exit'])
            groove = create_ratchet_tooth_ring(z_pos, cutout_radius)
            
            ratchet_grooves = groove if ratchet_grooves is None else ratchet_grooves.fuse(groove)
    
    if ratchet_grooves:
        cone_cutout = cone_cutout.fuse(ratchet_grooves)
    
    # Create visible cutter (hidden)
    cone_obj = doc.addObject("Part::Feature", "Cone_Cutter")
    cone_obj.Shape = cone_cutout
    cone_obj.ViewObject.ShapeColor = (0.0, 1.0, 0.0)
    cone_obj.ViewObject.Transparency = 60
    cone_obj.ViewObject.Visibility = False  # Hide cutter
    
    # Cut sphere
    sphere_cut = solid_sphere.cut(top_hole).cut(cone_cutout)
    
    sphere_obj = doc.addObject("Part::Feature", "Sphere")
    sphere_obj.Shape = sphere_cut
    sphere_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
    sphere_obj.ViewObject.Transparency = 30
    
    return sphere_obj, cone_obj


def create_ridge_ring(z_position, dims):
    """Single internal ridge ring for rope grip"""
    outer_radius = dims['ring_inner_dia'] / 2.0
    inner_radius = outer_radius - RIDGE_HEIGHT
    
    base_top = App.Vector(outer_radius, 0, z_position + RIDGE_WIDTH/2)
    peak = App.Vector(inner_radius, 0, z_position)
    base_bottom = App.Vector(outer_radius, 0, z_position - RIDGE_WIDTH/2)
    
    edge1 = Part.LineSegment(base_top, peak).toShape()
    edge2 = Part.LineSegment(peak, base_bottom).toShape()
    edge3 = Part.LineSegment(base_bottom, base_top).toShape()
    
    wire = Part.Wire([edge1, edge2, edge3])
    face = Part.Face(wire)
    
    return face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360)


def create_compression_ring(dims):
    """Compression ring with internal ridges, external ratchet teeth, and split"""
    doc = App.ActiveDocument
    
    # Base tapered ring
    ring_cone = Part.makeCone(
        dims['ring_head_outer_dia'] / 2.0,
        dims['ring_base_outer_dia'] / 2.0,
        dims['ferrule_length'],
        App.Vector(0, 0, dims['ring_head_z']),
        App.Vector(0, 0, -1)
    )
    
    # Hollow for line
    line_hole = Part.makeCylinder(
        dims['ring_inner_dia'] / 2.0,
        dims['ferrule_length'] + 2,
        App.Vector(0, 0, dims['ring_head_z'] + 1),
        App.Vector(0, 0, -1)
    )
    
    hollow_ring = ring_cone.cut(line_hole)
    
    # Add internal ridges
    num_ridges = int(dims['ferrule_length'] / RIDGE_SPACING)
    ridges_combined = None
    
    for i in range(num_ridges):
        z_pos = dims['ring_head_z'] - (i * RIDGE_SPACING) - RIDGE_SPACING/2
        if z_pos > dims['ring_base_z']:
            ridge = create_ridge_ring(z_pos, dims)
            ridges_combined = ridge if ridges_combined is None else ridges_combined.fuse(ridge)
    
    if ridges_combined:
        hollow_ring = hollow_ring.fuse(ridges_combined)
    
    # Add external ratchet teeth
    num_teeth = int(dims['ferrule_length'] / RATCHET_TOOTH_SPACING)
    ratchet_teeth = None
    
    for i in range(num_teeth):
        z_pos = dims['ring_head_z'] - (i * RATCHET_TOOTH_SPACING) - RATCHET_TOOTH_WIDTH/2
        if z_pos > dims['ring_base_z']:
            t = abs(z_pos - dims['ring_head_z']) / dims['ferrule_length']
            ring_radius = (dims['ring_head_outer_dia']/2.0) + t * (dims['ring_base_outer_dia']/2.0 - dims['ring_head_outer_dia']/2.0)
            tooth = create_ratchet_tooth_ring(z_pos, ring_radius)
            ratchet_teeth = tooth if ratchet_teeth is None else ratchet_teeth.fuse(tooth)
    
    if ratchet_teeth:
        hollow_ring = hollow_ring.fuse(ratchet_teeth)
    
    # Create split
    plate_size = dims['ring_base_with_teeth'] + 10
    cutting_plate = Part.makeBox(
        plate_size,
        GAP_WIDTH,
        dims['ferrule_length'] + 2
    )
    cutting_plate.translate(App.Vector(
        -plate_size/2,
        -GAP_WIDTH/2,
        dims['ring_head_z'] - dims['ferrule_length'] - 1
    ))
    
    # Visible split plate (hidden)
    plate_obj = doc.addObject("Part::Feature", "SplitPlate_Cutter")
    plate_obj.Shape = cutting_plate
    plate_obj.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
    plate_obj.ViewObject.Transparency = 60
    plate_obj.ViewObject.Visibility = False  # Hide cutter
    
    # Apply split
    split_ring = hollow_ring.cut(cutting_plate)
    
    ring_obj = doc.addObject("Part::Feature", "CompressionRing")
    ring_obj.Shape = split_ring
    ring_obj.ViewObject.ShapeColor = (0.9, 0.9, 0.9)
    ring_obj.ViewObject.Transparency = 20
    
    return ring_obj, plate_obj


# ============================================================================
# STL EXPORT
# ============================================================================

def export_stl(sphere_obj, ring_obj, line_dia):
    """Export parts to STL files in user's Downloads folder"""
    # Get user's Downloads folder
    downloads_dir = os.path.expanduser("~/Downloads")
    
    # Ensure directory exists
    os.makedirs(downloads_dir, exist_ok=True)
    
    # Generate filenames
    sphere_filename = os.path.join(downloads_dir, f"cap_sphere_{line_dia}mm.stl")
    ring_filename = os.path.join(downloads_dir, f"cap_ring_{line_dia}mm.stl")
    
    print(f"\nExporting STL files to Downloads folder...")
    
    # Export sphere
    mesh_sphere = Mesh.Mesh()
    mesh_sphere.addFacets(sphere_obj.Shape.tessellate(0.1))
    mesh_sphere.write(sphere_filename)
    print(f"  Sphere: {sphere_filename}")
    
    # Export ring
    mesh_ring = Mesh.Mesh()
    mesh_ring.addFacets(ring_obj.Shape.tessellate(0.1))
    mesh_ring.write(ring_filename)
    print(f"  Ring: {ring_filename}")
    
    print("STL export complete!")


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Show dialog
    params = show_dialog()
    if params is None:
        print("Design cancelled by user")
        return
    
    line_dia = params['line_diameter']
    export_stl_files = params['export_stl']
    
    print("=" * 70)
    print("MOORING LINE CAP - Parametric Design")
    print("=" * 70)
    print(f"\nLine Diameter: {line_dia}mm")
    print(f"Export STL: {export_stl_files}")
    
    # Calculate dimensions
    dims = calculate_dimensions(line_dia)
    
    print(f"\nCalculated Dimensions:")
    print(f"  Sphere: {dims['sphere_outer_dia']:.1f}mm diameter")
    print(f"  Ring HEAD: {dims['ring_head_outer_dia']}mm outer ({dims['ring_head_with_teeth']:.1f}mm with teeth)")
    print(f"  Ring BASE: {dims['ring_base_outer_dia']:.2f}mm outer ({dims['ring_base_with_teeth']:.2f}mm with teeth)")
    print(f"  Ring length: {dims['ferrule_length']:.1f}mm")
    
    # Create document
    doc = App.ActiveDocument
    if not doc:
        doc = App.newDocument("MooringCap")
    
    # Create geometry
    print("\nCreating geometry...")
    create_line(dims)
    sphere_obj, cone_obj = create_sphere_with_cone(dims)
    ring_obj, plate_obj = create_compression_ring(dims)
    
    # Recompute
    doc.recompute()
    
    # Fit view
    if App.GuiUp:
        import FreeCADGui
        FreeCADGui.SendMsgToActiveView("ViewFit")
    
    print("Design complete!")
    
    # Export if requested
    if export_stl_files:
        export_stl(sphere_obj, ring_obj, line_dia)


if __name__ == '__main__':
    main()