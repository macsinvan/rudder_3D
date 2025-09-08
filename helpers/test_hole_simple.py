import sys
import FreeCAD
import Part

# Test without importing hole_array_helper first
print("FreeCAD imported successfully")
print(f"FreeCAD version: {FreeCAD.Version()}")

# Create a simple box to test Part module
box = Part.makeBox(10, 10, 10)
print(f"Test box volume: {box.Volume}")

# Now try importing the helper
try:
    import hole_array_helper
    print("hole_array_helper imported successfully")
except Exception as e:
    print(f"Error importing hole_array_helper: {e}")
    sys.exit(1)

# Try calling the function if import worked
try:
    shape, info = hole_array_helper.create_circular_perforation_pattern(
        length=50,
        width=50,
        thickness=6,
        hole_diameter=10,
        spacing=15
    )
    print(f"Function called successfully")
    print(f"Holes created: {info.get('total_holes', 'unknown')}")
except Exception as e:
    print(f"Error calling function: {e}")
