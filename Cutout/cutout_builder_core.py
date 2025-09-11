"""
Simple STEP Import/Show/Export Tool
Bare bones functionality - just load, display, and save STEP files

This file goes in: ~/Rudder_Code/Cutout/simple_step_tool.py
"""
import sys
from pathlib import Path

# Add project root for module imports
project = Path.home() / "Rudder_Code"
if project.exists():
    sys.path.insert(0, str(project))

# Import the STEP helper
from helpers.step_save_load import save_step, load_step

def import_show_export(input_step_path, output_step_path=None, doc_name="SimpleSTEP"):
    """
    Import a STEP file, show it, and optionally export to a new STEP file
    
    Args:
        input_step_path: Path to input STEP file
        output_step_path: Path for output STEP file (optional)
        doc_name: Name for the FreeCAD document
    
    Returns:
        doc: FreeCAD document
        objects: List of imported objects
    """
    print(f"📥 Importing: {input_step_path}")
    
    # Import STEP file using helper
    doc, objects = load_step(input_step_path, doc_name, verbose=True)
    
    print(f"✅ Imported {len(objects)} objects")
    
    # Show objects (they should be visible by default after import)
    for obj in objects:
        if hasattr(obj, 'ViewObject'):
            obj.ViewObject.Visibility = True
    
    # Export if output path provided
    if output_step_path:
        print(f"📤 Exporting to: {output_step_path}")
        save_step(doc, output_step_path, verbose=True)
        print("✅ Export complete")
    
    return doc, objects


def main():
    """
    Main function for command line usage
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple STEP import/show/export tool')
    parser.add_argument('input_file', help='Input STEP file path')
    parser.add_argument('-o', '--output', help='Output STEP file path (optional)')
    parser.add_argument('-d', '--doc', default='SimpleSTEP', help='Document name')
    
    args = parser.parse_args()
    
    # Run import/show/export
    doc, objects = import_show_export(
        args.input_file,
        args.output,
        args.doc
    )
    
    print(f"\n📊 Summary:")
    print(f"   Document: {doc.Name}")
    print(f"   Objects imported: {len(objects)}")
    if objects:
        print(f"   Object names: {[obj.Name for obj in objects]}")


# Only run main if explicitly called from command line, not when imported
# if __name__ == "__main__":
#     main()