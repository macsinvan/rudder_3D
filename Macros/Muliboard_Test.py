# Multiboard_From_Analysis.py
# Generate Multiboard tile using geometry extracted from .3mf analysis
# Based on actual measurements from 6x6 tile

import FreeCAD
import Part
import math
from FreeCAD import Base

# ==========================================
# EXTRACTED MULTIBOARD GEOMETRY
# ==========================================
class ExtractedMultiboardGeometry:
    """Actual Multiboard dimensions from .3mf analysis"""
    
    # Overall tile dimensions (measured)
    TILE_WIDTH = 150.0      # mm (6x6 MU tile)
    TILE_HEIGHT = 150.0     # mm
    TILE_THICKNESS = 6.2    # mm (actual measured, not 6.6)
    
    # Grid specifications
    GRID_SIZE = 25.0        # mm - Basic Multiboard Unit (MU)
    HALF_GRID = 12.5        # mm - Half grid
    
    # Recess depths (from Z-analysis)
    OCTAGON_RECESS_DEPTH = 2.0   # mm - Main octagonal recesses
    DEEP_RECESS_DEPTH = 3.1       # mm - Deeper features (possibly for large holes)
    
    # Hole dimensions (standard)
    SMALL_HOLE_DIA = 5.0    # mm - Small threaded holes  
    LARGE_HOLE_DIA = 8.0    # mm - Large holes
    
    # Detected spacings (from X-Y analysis)
    # 9.7mm ≈ 10mm, 3.3mm might be octagon-related
    # 6.5mm might be edge offset
    EDGE_OFFSET = 6.5       # mm - Distance from edge to first feature
    
    # Octagon dimensions (estimated)
    # If octagons are on 12.5mm grid with small gaps between
    OCTAGON_SPACING = 12.5  # mm - Center to center
    OCTAGON_SIZE = 11.5     # mm - Flat-to-flat (leaving ~1mm walls)

# ==========================================
# MULTIBOARD TILE GENERATOR V2
# ==========================================
class MultiboardGeneratorV2:
    def __init__(self):
        self.geom = ExtractedMultiboardGeometry()
        
    def create_tile(self, show_debug=True):
        """Generate Multiboard tile based on extracted geometry"""
        
        if show_debug:
            print("="*60)
            print("CREATING MULTIBOARD TILE FROM EXTRACTED GEOMETRY")
            print("="*60)
            print(f"Tile: {self.geom.TILE_WIDTH} x {self.geom.TILE_HEIGHT} x {self.geom.TILE_THICKNESS} mm")
            print(f"Octagon grid: {self.geom.OCTAGON_SPACING} mm spacing")
            print(f"Octagon size: {self.geom.OCTAGON_SIZE} mm flat-to-flat")
            print(f"Recess depth: {self.geom.OCTAGON_RECESS_DEPTH} mm")
        
        # Step 1: Create base tile
        base_tile = Part.makeBox(self.geom.TILE_WIDTH, 
                                self.geom.TILE_HEIGHT, 
                                self.geom.TILE_THICKNESS)
        
        # Step 2: Create octagonal recess pattern
        octagon_cuts = []
        hole_cuts = []
        
        # Based on the actual Multiboard pattern:
        # - Large holes (with octagonal recesses) are on a 25mm grid
        # - Small holes are positioned between them on a 12.5mm offset grid
        
        # Large holes with octagonal recesses - on 25mm grid
        large_hole_positions = []
        pos_x = 12.5  # Start at half-grid from edge
        while pos_x < self.geom.TILE_WIDTH - 12.5:
            pos_y = 12.5
            while pos_y < self.geom.TILE_HEIGHT - 12.5:
                large_hole_positions.append((pos_x, pos_y))
                pos_y += self.geom.GRID_SIZE  # 25mm spacing
            pos_x += self.geom.GRID_SIZE  # 25mm spacing
        
        # Small holes - on 12.5mm offset grid (between large holes)
        small_hole_positions = []
        
        # Small holes in between large holes horizontally
        pos_x = 12.5 + self.geom.HALF_GRID  # Offset by half grid
        while pos_x < self.geom.TILE_WIDTH - 12.5:
            pos_y = 12.5
            while pos_y < self.geom.TILE_HEIGHT - 12.5:
                small_hole_positions.append((pos_x, pos_y))
                pos_y += self.geom.GRID_SIZE
            pos_x += self.geom.GRID_SIZE
        
        # Small holes in between large holes vertically
        pos_x = 12.5
        while pos_x < self.geom.TILE_WIDTH - 12.5:
            pos_y = 12.5 + self.geom.HALF_GRID  # Offset by half grid
            while pos_y < self.geom.TILE_HEIGHT - 12.5:
                small_hole_positions.append((pos_x, pos_y))
                pos_y += self.geom.GRID_SIZE
            pos_x += self.geom.GRID_SIZE
        
        # Small holes at diagonal intersections
        pos_x = 12.5 + self.geom.HALF_GRID
        while pos_x < self.geom.TILE_WIDTH - 12.5:
            pos_y = 12.5 + self.geom.HALF_GRID
            while pos_y < self.geom.TILE_HEIGHT - 12.5:
                small_hole_positions.append((pos_x, pos_y))
                pos_y += self.geom.GRID_SIZE
            pos_x += self.geom.GRID_SIZE
        
        if show_debug:
            print(f"\nHole positions:")
            print(f"  - {len(large_hole_positions)} large holes with octagonal recesses")
            print(f"  - {len(small_hole_positions)} small holes")
        
        # Create octagonal recesses for large holes
        for x, y in large_hole_positions:
            octagon = self._create_octagon_recess(x, y, 
                                                 self.geom.OCTAGON_SIZE,
                                                 self.geom.OCTAGON_RECESS_DEPTH,
                                                 self.geom.TILE_THICKNESS)
            octagon_cuts.append(octagon)
            
            # Create large hole
            hole = Part.makeCylinder(self.geom.LARGE_HOLE_DIA/2, 
                                   self.geom.TILE_THICKNESS,
                                   Base.Vector(x, y, 0))
            hole_cuts.append(hole)
        
        # Create small holes (no octagonal recess)
        for x, y in small_hole_positions:
            hole = Part.makeCylinder(self.geom.SMALL_HOLE_DIA/2,
                                   self.geom.TILE_THICKNESS,
                                   Base.Vector(x, y, 0))
            hole_cuts.append(hole)
        
        # Step 3: Apply cuts to base tile
        result = base_tile
        
        # Cut octagonal recesses first (shallow)
        if octagon_cuts:
            if show_debug:
                print("\nCutting octagonal recesses...")
            for i, octagon in enumerate(octagon_cuts):
                if i % 20 == 0 and show_debug:
                    print(f"  Processing octagon {i+1}/{len(octagon_cuts)}")
                result = result.cut(octagon)
        
        # Cut holes (through)
        if hole_cuts:
            if show_debug:
                print("Cutting holes...")
            # Combine holes for faster boolean
            combined_holes = hole_cuts[0]
            for hole in hole_cuts[1:]:
                combined_holes = combined_holes.fuse(hole)
            result = result.cut(combined_holes)
        
        if show_debug:
            print("\nTile generation complete!")
        
        return result
    
    def _create_octagon_recess(self, center_x, center_y, flat_to_flat, depth, thickness):
        """Create an octagonal recess"""
        # Calculate radius from flat-to-flat distance
        # For regular octagon: radius = flat_to_flat / (2 * cos(22.5°))
        radius = flat_to_flat / (2 * math.cos(math.pi/8))
        
        # Create 8 vertices for octagon
        # Rotate 22.5° so flats align with X/Y axes
        vertices = []
        rotation_offset = math.pi / 8  # 22.5 degrees
        
        for i in range(8):
            angle = (i * math.pi / 4) + rotation_offset
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            # Start from top surface, go down by recess depth
            vertices.append(Base.Vector(x, y, thickness - depth))
        
        # Close the polygon
        vertices.append(vertices[0])
        
        # Create wire and face
        wire = Part.makePolygon(vertices)
        face = Part.Face(wire)
        
        # Extrude to create recess
        octagon_solid = face.extrude(Base.Vector(0, 0, depth))
        
        return octagon_solid

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    """Generate Multiboard tile using extracted geometry"""
    
    # Create new document if none exists
    if not FreeCAD.ActiveDocument:
        FreeCAD.newDocument("MultiboardFromAnalysis")
    
    doc = FreeCAD.ActiveDocument
    
    # Initialize generator
    generator = MultiboardGeneratorV2()
    
    # Create tile
    tile_shape = generator.create_tile(show_debug=True)
    
    # Create FreeCAD object
    tile_obj = doc.addObject("Part::Feature", "Multiboard_6x6_Extracted")
    tile_obj.Shape = tile_shape
    
    # Set view
    doc.recompute()
    if FreeCAD.GuiUp:
        FreeCAD.Gui.activeDocument().activeView().viewAxometric()
        FreeCAD.Gui.SendMsgToActiveView("ViewFit")
    
    print("\n" + "="*60)
    print("MULTIBOARD TILE CREATED FROM EXTRACTED GEOMETRY")
    print("="*60)
    print("Based on analysis of actual Multiboard .3mf file:")
    print("- 150mm x 150mm x 6.2mm")
    print("- Octagonal recesses on 12.5mm grid")
    print("- Small (5mm) and large (8mm) holes")
    print("- 2mm deep octagonal recesses")
    print("="*60)
    
    return tile_obj

# Run the macro
if __name__ == "__main__":
    tile = main()