# Test Circular Holes Pattern - FreeCAD Macro
import FreeCAD
import FreeCADGui
import Part

def create_circular_holes_test(length=100, width=80, thickness=6, hole_diameter=10, spacing=15):
    """Test function to create a plate with circular holes"""
    
    print("="*50)
    print(f"Creating test plate: {length}x{width}x{thickness}mm")
    print(f"Hole diameter: {hole_diameter}mm, Spacing: {spacing}mm")
    print("="*50)
    
    # Create base plate
    base_plate = Part.makeBox(length, width, thickness)
    
    # Calculate hole grid
    margin = spacing / 2
    nx = int((length - 2 * margin) / spacing) + 1
    ny = int((width - 2 * margin) / spacing) + 1
    
    actual_spacing_x = (length - 2 * margin) / max(1, (nx - 1)) if nx > 1 else 0
    actual_spacing_y = (width - 2 * margin) / max(1, (ny - 1)) if ny > 1 else 0
    
    print(f"Creating {nx}x{ny} grid of holes...")
    
    # Create holes
    holes = []
    hole_count = 0
    
    for i in range(nx):
        for j in range(ny):
            x = margin + i * actual_spacing_x if nx > 1 else length / 2
            y = margin + j * actual_spacing_y if ny > 1 else width / 2
            
            if (x - hole_diameter/2 > 1 and x + hole_diameter/2 < length - 1 and
                y - hole_diameter/2 > 1 and y + hole_diameter/2 < width - 1):
                
                cylinder = Part.makeCylinder(
                    hole_diameter / 2,
                    thickness + 2,
                    FreeCAD.Vector(x, y, -1),
                    FreeCAD.Vector(0, 0, 1)
                )
                holes.append(cylinder)
                hole_count += 1
    
    print(f"Created {hole_count} holes")
    
    # Boolean subtract
    if holes:
        print("Performing boolean operations...")
        
        # Fuse holes
        if len(holes) > 1:
            holes_union = holes[0]
            for hole in holes[1:]:
                holes_union = holes_union.fuse(hole)
        else:
            holes_union = holes[0]
        
        # Cut from plate
        result = base_plate.cut(holes_union)
        
        print(f"Final volume: {result.Volume:.2f} mm³")
        print(f"Original volume: {base_plate.Volume:.2f} mm³")
        print(f"Material removed: {base_plate.Volume - result.Volume:.2f} mm³")
        
        return result
    else:
        print("No holes created")
        return base_plate

# Main execution
if not FreeCAD.ActiveDocument:
    FreeCAD.newDocument("HoleTest")

# Run test
test_shape = create_circular_holes_test(
    length=100,
    width=80,
    thickness=6,
    hole_diameter=10,
    spacing=15
)

# Create FreeCAD object to display
obj = FreeCAD.ActiveDocument.addObject("Part::Feature", "TestPlateWithHoles")
obj.Shape = test_shape

# Set view
FreeCAD.ActiveDocument.recompute()
FreeCADGui.activeView().viewIsometric()
FreeCADGui.activeView().fitAll()

print("\n✅ Test complete - check the 3D view")