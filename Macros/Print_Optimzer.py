"""
Print_Optimizer.py - Bambu Labs HD2 Two-Operation Grid Cutting Utility for FreeCAD

Filename: Print_Optimizer.py

1. Cut Z slices from tip to root using MAX bed size + remainder
2. Cut each Z slice along X if needed using MAX bed size + remainder

Usage:
    from Print_Optimizer import cut_rudder_for_hd2
    
    # Opens file selection dialog, returns tuple: (stl_files_list, cutting_plan_dict)
    
    # Just get cutting plan without saving STL files (default):
    stl_files, cutting_plan = cut_rudder_for_hd2()  # save_cuts=False by default
    
    # Save both STL files and cutting plan:
    stl_files, cutting_plan = cut_rudder_for_hd2(save_cuts=True)
    
    # Access cutting positions:
    z_cut_positions = cutting_plan["cutting_plan"]["z_cuts"]  # List of Z positions
    x_cut_positions = cutting_plan["cutting_plan"]["x_cuts"]  # List of X positions
    
    # All files (STL + JSON) are saved to same directory as selected STEP file
"""

import FreeCAD
import Part
import Mesh
from pathlib import Path
import math
import os
import json

# Bambu Labs HD2 specifications (single head)
HD2_BUILD_X = 325  # mm
HD2_BUILD_Y = 320  # mm  
HD2_BUILD_Z = 325  # mm
SAFETY_MARGIN = 15  # mm
EFFECTIVE_X = HD2_BUILD_X - SAFETY_MARGIN  # 310mm
EFFECTIVE_Y = HD2_BUILD_Y - SAFETY_MARGIN  # 305mm
EFFECTIVE_Z = HD2_BUILD_Z - SAFETY_MARGIN  # 310mm

class BambuHD2TwoOpCutter:
    """Two-operation cutting: Z cuts first, then X cuts per Z slice geometry"""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        print(f"HD2 Output directory: {self.output_dir}")
        self.z_slices = []
        self.final_pieces = []
        self.z_cut_positions = []  # Track Z cuts for JSON export
        self.x_cut_positions = []  # Track X cuts for JSON export
    
    def operation_1_z_cuts(self, shape):
        """
        Operation 1: Cut into MAX bed height chunks from tip upward
        """
        bbox = shape.BoundBox
        
        print(f"\n=== OPERATION 1: Z CUTS (MAX CHUNKS) ===")
        print(f"Rudder height: {bbox.ZLength:.1f}mm")
        print(f"Max Z chunk: {EFFECTIVE_Z}mm")
        
        # Calculate using MAX chunks + remainder
        full_z_chunks = int(bbox.ZLength // EFFECTIVE_Z)
        remainder_z = bbox.ZLength % EFFECTIVE_Z
        z_pieces_needed = full_z_chunks + (1 if remainder_z > 0 else 0)
        
        print(f"Full Z chunks: {full_z_chunks} × {EFFECTIVE_Z}mm = {full_z_chunks * EFFECTIVE_Z:.1f}mm")
        if remainder_z > 0:
            print(f"Remainder chunk: 1 × {remainder_z:.1f}mm")
        print(f"Total Z pieces: {z_pieces_needed}")
        
        # Create Z slices using MAX bed height
        z_slices = []
        z_cut_positions = []
        
        for i in range(z_pieces_needed):
            z_bottom = bbox.ZMin + i * EFFECTIVE_Z
            
            if i < full_z_chunks:
                # Full size chunk
                z_top = z_bottom + EFFECTIVE_Z
                chunk_height = EFFECTIVE_Z
            else:
                # Remainder chunk
                z_top = bbox.ZMax
                chunk_height = remainder_z
            
            # Track Z cut position (not at ends)
            if i > 0:  # Skip first boundary
                z_cut_positions.append(z_bottom)
            
            # Create cutting box
            cutting_box = Part.makeBox(
                bbox.XLength + 100,
                bbox.YLength + 100,
                chunk_height + 10,
                FreeCAD.Vector(bbox.XMin - 50, bbox.YMin - 50, z_bottom - 5)
            )
            
            # Cut Z slice
            try:
                z_slice = shape.common(cutting_box)
                if z_slice and z_slice.Volume > 0.1:
                    slice_bbox = z_slice.BoundBox
                    z_slice_info = {
                        'shape': z_slice,
                        'z_index': i + 1,
                        'z_range': (z_bottom, z_top),
                        'bbox': slice_bbox,
                        'chunk_height': chunk_height
                    }
                    z_slices.append(z_slice_info)
                    
                    print(f"  Z{i+1:02d}: {chunk_height:.1f}H × {slice_bbox.XLength:.1f}W × {slice_bbox.YLength:.1f}D mm")
                    
                    # UI visualization
                    doc = FreeCAD.ActiveDocument
                    z_obj = doc.addObject("Part::Feature", f"Z_Slice_{i+1:02d}")
                    z_obj.Shape = z_slice
                    z_obj.ViewObject.ShapeColor = (0.2, 0.8, 0.2)  # Green
                    z_obj.ViewObject.Transparency = 60
                    
            except Exception as e:
                print(f"  ❌ Z slice {i+1} failed: {e}")
        
        self.z_slices = z_slices
        self.z_cut_positions = z_cut_positions
        print(f"✅ Created {len(z_slices)} Z slices")
        return z_slices
    
    def operation_2_x_cuts(self, z_slices):
        """
        Operation 2: Single X cut strategy based on widest Z slice
        """
        print(f"\n=== OPERATION 2: SINGLE X CUT STRATEGY ===")
        print(f"Max X chunk: {EFFECTIVE_X}mm")
        
        # First pass: Find the widest Z slice
        widest_slice = None
        max_width = 0
        
        for z_slice_info in z_slices:
            slice_width = z_slice_info['bbox'].XLength
            if slice_width > max_width:
                max_width = slice_width
                widest_slice = z_slice_info
        
        print(f"Widest Z slice: Z{widest_slice['z_index']:02d} at {max_width:.1f}mm")
        
        # Calculate single X cut position based on widest slice
        global_x_cut = None
        if max_width > EFFECTIVE_X:
            # Calculate X cut for widest slice (310mm from leading edge)
            widest_bbox = widest_slice['bbox']
            global_x_cut = widest_bbox.XMax - EFFECTIVE_X
            print(f"Single X cut position: {global_x_cut:.1f}mm (310mm from leading edge)")
        else:
            print("No X cuts needed - all slices fit within 310mm width")
        
        # Second pass: Apply single X cut to all slices
        all_final_pieces = []
        
        for z_slice_info in z_slices:
            z_slice = z_slice_info['shape']
            z_idx = z_slice_info['z_index']
            slice_bbox = z_slice_info['bbox']
            
            print(f"\n  Z slice {z_idx} geometry: {slice_bbox.XLength:.1f}W × {slice_bbox.YLength:.1f}D mm")
            
            # Check if needs X cutting
            if slice_bbox.XLength <= EFFECTIVE_X or global_x_cut is None:
                # Single piece
                piece_info = {
                    'shape': z_slice,
                    'z_index': z_idx,
                    'x_index': 1,
                    'name': f"Z{z_idx:02d}_X01",
                    'dimensions': (slice_bbox.XLength, slice_bbox.YLength, z_slice_info['chunk_height'])
                }
                all_final_pieces.append(piece_info)
                print(f"    ✅ Single piece: Z{z_idx:02d}_X01")
                
                # UI visualization
                doc = FreeCAD.ActiveDocument
                piece_obj = doc.addObject("Part::Feature", f"Final_Z{z_idx:02d}_X01")
                piece_obj.Shape = z_slice
                piece_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red
                piece_obj.ViewObject.Transparency = 40
                
            else:
                # Apply global X cut to this slice
                print(f"    Applying global X cut at {global_x_cut:.1f}mm")
                
                # Track X cut position (only once)
                if z_idx == widest_slice['z_index']:
                    self.x_cut_positions.append(global_x_cut)
                
                # Leading edge piece (X max side)
                try:
                    x1_box = Part.makeBox(
                        slice_bbox.XMax - global_x_cut + 10,
                        slice_bbox.YLength + 100,
                        slice_bbox.ZLength + 100,
                        FreeCAD.Vector(global_x_cut - 5, slice_bbox.YMin - 50, slice_bbox.ZMin - 50)
                    )
                    
                    x1_piece = z_slice.common(x1_box)
                    if x1_piece and x1_piece.Volume > 0.1:
                        x1_bbox = x1_piece.BoundBox
                        piece_info = {
                            'shape': x1_piece,
                            'z_index': z_idx,
                            'x_index': 1,
                            'name': f"Z{z_idx:02d}_X01",
                            'dimensions': (x1_bbox.XLength, x1_bbox.YLength, x1_bbox.ZLength)
                        }
                        all_final_pieces.append(piece_info)
                        print(f"      ✅ Z{z_idx:02d}_X01: {x1_bbox.XLength:.1f}W mm (leading edge)")
                        
                        # UI visualization
                        doc = FreeCAD.ActiveDocument
                        piece_obj = doc.addObject("Part::Feature", f"Final_Z{z_idx:02d}_X01")
                        piece_obj.Shape = x1_piece
                        piece_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red
                        piece_obj.ViewObject.Transparency = 40
                        
                except Exception as e:
                    print(f"      ❌ X01 piece failed: {e}")
                
                # Trailing edge piece (X min side)
                try:
                    x2_box = Part.makeBox(
                        global_x_cut - slice_bbox.XMin + 10,
                        slice_bbox.YLength + 100,
                        slice_bbox.ZLength + 100,
                        FreeCAD.Vector(slice_bbox.XMin - 5, slice_bbox.YMin - 50, slice_bbox.ZMin - 50)
                    )
                    
                    x2_piece = z_slice.common(x2_box)
                    if x2_piece and x2_piece.Volume > 0.1:
                        x2_bbox = x2_piece.BoundBox
                        piece_info = {
                            'shape': x2_piece,
                            'z_index': z_idx,
                            'x_index': 2,
                            'name': f"Z{z_idx:02d}_X02",
                            'dimensions': (x2_bbox.XLength, x2_bbox.YLength, x2_bbox.ZLength)
                        }
                        all_final_pieces.append(piece_info)
                        print(f"      ✅ Z{z_idx:02d}_X02: {x2_bbox.XLength:.1f}W mm (trailing edge)")
                        
                        # UI visualization
                        doc = FreeCAD.ActiveDocument
                        piece_obj = doc.addObject("Part::Feature", f"Final_Z{z_idx:02d}_X02")
                        piece_obj.Shape = x2_piece
                        piece_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red
                        piece_obj.ViewObject.Transparency = 40
                        
                except Exception as e:
                    print(f"      ❌ X02 piece failed: {e}")
        
        self.final_pieces = all_final_pieces
        print(f"\n✅ Operation 2 complete: {len(all_final_pieces)} final pieces")
        if global_x_cut:
            print(f"Single X cut used: {global_x_cut:.1f}mm")
        return all_final_pieces
    
    def export_final_pieces(self, pieces, part_name):
        """Export all final pieces as STL with dimensions"""
        print(f"\n=== EXPORTING STL FILES ===")
        exported_files = []
        
        for piece_info in pieces:
            piece_name = f"{part_name}_{piece_info['name']}"
            stl_path = self.output_dir / f"{piece_name}.stl"
            
            if self._export_shape_to_stl(piece_info['shape'], stl_path):
                exported_files.append(stl_path)
                dims = piece_info['dimensions']
                print(f"✅ {piece_name}.stl - {dims[0]:.1f}W × {dims[1]:.1f}D × {dims[2]:.1f}H mm")
        
        return exported_files
    
    def export_cutting_plan_json(self, part_name):
        """
        Export cutting plan as JSON file
        
        Args:
            part_name: Base name for JSON file
            
        Returns:
            Path to exported JSON file
        """
        cutting_plan = {
            "cutting_plan": {
                "z_cuts": self.z_cut_positions,
                "x_cuts": self.x_cut_positions
            }
        }
        
        json_path = self.output_dir / f"{part_name}_cutting_plan.json"
        
        try:
            with open(json_path, 'w') as f:
                json.dump(cutting_plan, f, indent=2)
            
            print(f"📄 Cutting plan: {json_path.name}")
            print(f"   Z cuts: {len(self.z_cut_positions)} positions")
            print(f"   X cuts: {len(self.x_cut_positions)} positions")
            return json_path
            
        except Exception as e:
            print(f"❌ JSON export failed: {e}")
            return None
    
    def _export_shape_to_stl(self, shape, file_path):
        """Export shape to STL"""
        try:
            mesh = Mesh.Mesh()
            mesh.addFacets(shape.tessellate(0.1))
            mesh.write(str(file_path))
            return True
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False

def cut_rudder_for_hd2():
    """
    Two-operation cutting with file selection: Z cuts first, then X cuts per Z slice geometry
    
    User selects STEP file via dialog, all outputs saved to same directory as selected file.
    
    Returns:
        tuple: (stl_files_list, cutting_plan_dict)
        - stl_files_list: List of exported STL file paths
        - cutting_plan_dict: JSON structure with z_cuts and x_cuts positions
    """
    
    # File selection dialog
    try:
        import PySide2.QtWidgets as QtWidgets
        file_dialog = QtWidgets.QFileDialog()
        step_file, _ = file_dialog.getOpenFileName(
            None,
            "Select STEP file to cut for HD2",
            os.path.expanduser("~/Rudder_Code/boats"),
            "STEP files (*.step *.STEP)"
        )
        
        if not step_file:
            print("❌ No file selected")
            return [], {}
            
    except Exception as e:
        print(f"❌ File dialog failed: {e}")
        print("Using default file...")
        # Fallback to default
        boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/MackenSea")
        step_file = str(Path(boat_folder) / "output" / "demo" / "MackenSea_Port_Half.step")
    
    step_file_path = Path(step_file)
    output_dir = step_file_path.parent  # Same directory as selected file
    
    print(f"📁 Loading: {step_file_path.name}")
    print(f"📁 Output to: {output_dir}")
    
    # Create document
    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument("HD2_MaxChunk_Cutting")
    
    try:
        # Import STEP
        import Import
        Import.insert(str(step_file), doc.Name)
        doc.recompute()
        
        if len(doc.Objects) == 0:
            print("❌ No objects imported")
            return [], {}
        
        original_obj = doc.Objects[-1]
        if not hasattr(original_obj, 'Shape'):
            print("❌ No Shape found")
            return [], {}
        
        print(f"✅ Loaded: {original_obj.Label}")
        original_obj.ViewObject.Transparency = 80
        
        # Initialize cutter with selected file's directory
        cutter = BambuHD2TwoOpCutter(output_dir)
        
        # Operation 1: Z cuts using MAX chunks
        z_slices = cutter.operation_1_z_cuts(original_obj.Shape)
        
        if not z_slices:
            print("❌ No Z slices created")
            return [], {}
        
        # Operation 2: X cuts per Z slice using MAX chunks
        final_pieces = cutter.operation_2_x_cuts(z_slices)
        
        if not final_pieces:
            print("❌ No final pieces created")
            return [], {}
        
        # Export STL files
        part_name = step_file_path.stem  # Filename without extension
        exported_files = cutter.export_final_pieces(final_pieces, part_name)
        
        # Export cutting plan as JSON
        json_file = cutter.export_cutting_plan_json(part_name)
        
        # Create return structure
        cutting_plan = {
            "cutting_plan": {
                "z_cuts": cutter.z_cut_positions,
                "x_cuts": cutter.x_cut_positions
            }
        }
        
        doc.recompute()
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
        
        return exported_files, cutting_plan
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return [], {}

# Run the cutting
if __name__ == "__main__":
    print("=== Bambu HD2 MAX CHUNK Cutting ===")
    print("Z cuts: 310mm max + remainder")
    print("X cuts: 310mm max + remainder per Z slice")
    
    result = cut_rudder_for_hd2()
    
    if result:
        stl_files, cutting_plan = result
        print(f"\n🎉 SUCCESS: {len(stl_files)} STL files exported")
        print(f"Z cuts: {cutting_plan['cutting_plan']['z_cuts']}")
        print(f"X cuts: {cutting_plan['cutting_plan']['x_cuts']}")
    else:
        print("❌ Export failed")