"""
Bambu Labs HD2 Two-Operation Grid Cutting Utility for FreeCAD
1. Cut Z slices from tip to root using MAX bed size + remainder
2. Cut each Z slice along X if needed using MAX bed size + remainder
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
    
    def __init__(self, output_dir, boat_name="MackenSea"):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
            self.output_dir = Path(boat_folder) / "output" / "demo"
        
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
        Operation 2: Cut each Z slice geometry along X using MAX chunks
        """
        print(f"\n=== OPERATION 2: X CUTS PER Z SLICE ===")
        print(f"Max X chunk: {EFFECTIVE_X}mm")
        
        all_final_pieces = []
        
        for z_slice_info in z_slices:
            z_slice = z_slice_info['shape']
            z_idx = z_slice_info['z_index']
            slice_bbox = z_slice_info['bbox']
            
            print(f"\n  Z slice {z_idx} geometry: {slice_bbox.XLength:.1f}W × {slice_bbox.YLength:.1f}D mm")
            
            # Check if fits without X cutting
            if slice_bbox.XLength <= EFFECTIVE_X:
                # Single piece
                piece_info = {
                    'shape': z_slice,
                    'z_index': z_idx,
                    'x_index': 1,
                    'name': f"Z{z_idx:02d}_X01",
                    'dimensions': (slice_bbox.XLength, slice_bbox.YLength, z_slice_info['chunk_height'])
                }
                all_final_pieces.append(piece_info)
                print(f"    ✅ Fits: Z{z_idx:02d}_X01")
                
                # UI visualization
                doc = FreeCAD.ActiveDocument
                piece_obj = doc.addObject("Part::Feature", f"Final_Z{z_idx:02d}_X01")
                piece_obj.Shape = z_slice
                piece_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red
                piece_obj.ViewObject.Transparency = 40
                
            else:
                # Needs X cutting - use MAX chunks + remainder
                full_x_chunks = int(slice_bbox.XLength // EFFECTIVE_X)
                remainder_x = slice_bbox.XLength % EFFECTIVE_X
                x_pieces_needed = full_x_chunks + (1 if remainder_x > 0 else 0)
                
                print(f"    Needs X cutting:")
                print(f"      Full X chunks: {full_x_chunks} × {EFFECTIVE_X}mm = {full_x_chunks * EFFECTIVE_X:.1f}mm")
                if remainder_x > 0:
                    print(f"      Remainder: 1 × {remainder_x:.1f}mm")
                print(f"      Total X pieces: {x_pieces_needed}")
                
                # Cut along X starting from leading edge (X max) backward
                for x_i in range(x_pieces_needed):
                    
                    if x_i < full_x_chunks:
                        # Full X chunk from leading edge backward
                        x_right = slice_bbox.XMax - x_i * EFFECTIVE_X
                        x_left = x_right - EFFECTIVE_X
                        x_width = EFFECTIVE_X
                    else:
                        # Remainder X chunk at trailing edge
                        x_left = slice_bbox.XMin
                        x_right = slice_bbox.XMax - full_x_chunks * EFFECTIVE_X
                        x_width = remainder_x
                    
                    # Track X cut position (not at slice ends)
                    if x_i > 0:  # Skip first piece boundary
                        self.x_cut_positions.append(x_right)  # Position of cut
                    
                    # Create X cutting box
                    x_cutting_box = Part.makeBox(
                        x_width + 10,
                        slice_bbox.YLength + 100,
                        slice_bbox.ZLength + 100,
                        FreeCAD.Vector(x_left - 5, slice_bbox.YMin - 50, slice_bbox.ZMin - 50)
                    )
                    
                    # Cut this X piece
                    try:
                        x_piece = z_slice.common(x_cutting_box)
                        if x_piece and x_piece.Volume > 0.1:
                            x_piece_bbox = x_piece.BoundBox
                            piece_info = {
                                'shape': x_piece,
                                'z_index': z_idx,
                                'x_index': x_i + 1,
                                'name': f"Z{z_idx:02d}_X{x_i+1:02d}",
                                'dimensions': (x_piece_bbox.XLength, x_piece_bbox.YLength, x_piece_bbox.ZLength)
                            }
                            all_final_pieces.append(piece_info)
                            print(f"        ✅ Z{z_idx:02d}_X{x_i+1:02d}: {x_width:.1f}W mm")
                            
                            # UI visualization
                            doc = FreeCAD.ActiveDocument
                            piece_obj = doc.addObject("Part::Feature", f"Final_Z{z_idx:02d}_X{x_i+1:02d}")
                            piece_obj.Shape = x_piece
                            piece_obj.ViewObject.ShapeColor = (0.8, 0.2, 0.2)  # Red
                            piece_obj.ViewObject.Transparency = 40
                            
                    except Exception as e:
                        print(f"        ❌ X piece {x_i+1} failed: {e}")
        
        self.final_pieces = all_final_pieces
        print(f"\n✅ Operation 2 complete: {len(all_final_pieces)} final pieces")
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

def cut_rudder_for_hd2(boat_name="MackenSea", step_filename="MackenSea_Port_Half.step"):
    """
    Two-operation cutting: Z cuts first, then X cuts per Z slice geometry
    """
    boat_folder = os.path.expanduser(f"~/Rudder_Code/boats/{boat_name}")
    demo_folder = Path(boat_folder) / "output" / "demo"
    step_file = demo_folder / step_filename
    
    if not step_file.exists():
        print(f"❌ File not found: {step_file}")
        return []
    
    print(f"📁 Loading: {step_file}")
    
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
            return []
        
        original_obj = doc.Objects[-1]
        if not hasattr(original_obj, 'Shape'):
            print("❌ No Shape found")
            return []
        
        print(f"✅ Loaded: {original_obj.Label}")
        original_obj.ViewObject.Transparency = 80
        
        # Initialize cutter
        cutter = BambuHD2TwoOpCutter(demo_folder, boat_name)
        
        # Operation 1: Z cuts using MAX chunks
        z_slices = cutter.operation_1_z_cuts(original_obj.Shape)
        
        if not z_slices:
            print("❌ No Z slices created")
            return []
        
        # Operation 2: X cuts per Z slice using MAX chunks
        final_pieces = cutter.operation_2_x_cuts(z_slices)
        
        if not final_pieces:
            print("❌ No final pieces created")
            return []
        
        # Export STL files
        part_name = step_filename.replace('.step', '').replace('.STEP', '')
        exported_files = cutter.export_final_pieces(final_pieces, part_name)
        
        # Export cutting plan as JSON
        json_file = cutter.export_cutting_plan_json(part_name)
        
        doc.recompute()
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
        
        return exported_files
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return []

# Run the cutting
if __name__ == "__main__":
    print("=== Bambu HD2 MAX CHUNK Cutting ===")
    print("Z cuts: 310mm max + remainder")
    print("X cuts: 310mm max + remainder per Z slice")
    
    files = cut_rudder_for_hd2()
    
    if files:
        print(f"\n🎉 SUCCESS: {len(files)} STL files exported")
        for file in files:
            print(f"   📄 {file.name}")
    else:
        print("❌ Export failed")