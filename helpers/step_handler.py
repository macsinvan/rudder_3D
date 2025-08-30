"""
STEP File Handler
Generic import/export functionality for STEP files in FreeCAD
Place in: ~/Rudder_Code/helpers/step_handler.py
"""
from pathlib import Path
import FreeCAD as App
import Part


class StepHandler:
    """Handle STEP file import/export operations"""
    
    def __init__(self, default_output_dir=None, verbose=True):
        """
        Initialize STEP handler
        
        Args:
            default_output_dir: Default directory for exports (optional)
            verbose: Whether to print status messages
        """
        self.default_output_dir = Path(default_output_dir) if default_output_dir else None
        self.verbose = verbose
    
    def log(self, message):
        """Print message if verbose mode is on"""
        if self.verbose:
            print(message)
    
    def ensure_merged_solid(self, obj):
        """
        Ensure the object is a single merged solid before export
        
        Args:
            obj: FreeCAD object with Shape property
            
        Returns:
            Object with merged shape if multiple solids were found
        """
        if hasattr(obj, 'Shape') and hasattr(obj.Shape, 'Solids'):
            if len(obj.Shape.Solids) > 1:
                self.log(f"⚠️ Multiple solids detected ({len(obj.Shape.Solids)}), merging...")
                # Fuse all solids into one
                merged = obj.Shape.Solids[0]
                for solid in obj.Shape.Solids[1:]:
                    merged = merged.fuse(solid)
                obj.Shape = merged
                self.log("✅ Merged into single solid")
        return obj
    
    def export_step(self, obj, filepath=None, filename=None, output_dir=None, ensure_merged=True):
        """
        Export FreeCAD object to STEP file
        
        Args:
            obj: FreeCAD object or list of objects to export
            filepath: Complete path to output file (overrides filename and output_dir)
            filename: Name of output file (used with output_dir)
            output_dir: Directory for output (uses default if not specified)
            ensure_merged: Whether to merge multiple solids before export
            
        Returns:
            Path to exported file as string
        """
        # Handle complete filepath
        if filepath:
            output_path = Path(filepath)
        else:
            # Build path from components
            if not filename:
                filename = "export.step"
            if not filename.endswith('.step'):
                filename += '.step'
            
            if output_dir:
                output_path = Path(output_dir) / filename
            elif self.default_output_dir:
                output_path = self.default_output_dir / filename
            else:
                output_path = Path.cwd() / filename
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare objects for export
        if not isinstance(obj, list):
            objects = [obj]
        else:
            objects = obj
        
        # Optionally merge solids
        if ensure_merged:
            objects = [self.ensure_merged_solid(o) for o in objects]
        
        # Export
        try:
            Part.export(objects, str(output_path))
            self.log(f"📤 Exported STEP: {output_path}")
            return str(output_path)
        except Exception as e:
            self.log(f"❌ Export failed: {e}")
            raise
    
    def import_step(self, filepath, doc=None, doc_name=None, object_name=None):
        """
        Import STEP file into FreeCAD document
        
        Args:
            filepath: Path to STEP file to import
            doc: Existing FreeCAD document (optional)
            doc_name: Name for new document if doc not provided
            object_name: Name for imported object (default: "ImportedSTEP")
            
        Returns:
            Tuple of (document, imported_object)
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"STEP file not found: {filepath}")
        
        # Get or create document
        if doc is None:
            if not doc_name:
                doc_name = f"Import_{filepath.stem}"
            
            if doc_name in App.listDocuments():
                doc = App.getDocument(doc_name)
            else:
                doc = App.newDocument(doc_name)
                self.log(f"📄 Created document: {doc_name}")
        
        # Import the STEP file
        try:
            shape = Part.read(str(filepath))
            
            # Create object with imported shape
            if not object_name:
                object_name = filepath.stem
            
            imported_obj = doc.addObject("Part::Feature", object_name)
            imported_obj.Shape = shape
            imported_obj.Label = object_name
            
            self.log(f"📥 Imported STEP: {filepath.name} as {object_name}")
            
            # Recompute document
            doc.recompute()
            
            return doc, imported_obj
            
        except Exception as e:
            self.log(f"❌ Import failed: {e}")
            raise
    
    def export_multiple_steps(self, objects_dict, output_dir=None, ensure_merged=True):
        """
        Export multiple objects to separate STEP files
        
        Args:
            objects_dict: Dictionary of {filename: object} pairs
            output_dir: Directory for all exports
            ensure_merged: Whether to merge solids before export
            
        Returns:
            Dictionary of {filename: exported_path} pairs
        """
        results = {}
        
        for filename, obj in objects_dict.items():
            try:
                path = self.export_step(obj, filename=filename, 
                                       output_dir=output_dir, 
                                       ensure_merged=ensure_merged)
                results[filename] = path
            except Exception as e:
                self.log(f"⚠️ Failed to export {filename}: {e}")
                results[filename] = None
        
        return results
    
    def import_and_merge_steps(self, filepaths, doc=None, doc_name="MergedImport"):
        """
        Import multiple STEP files and optionally merge them
        
        Args:
            filepaths: List of STEP file paths
            doc: Existing document or None to create new
            doc_name: Name for new document if needed
            
        Returns:
            Tuple of (document, list_of_imported_objects)
        """
        imported_objects = []
        
        for i, filepath in enumerate(filepaths):
            # Import each file
            if i == 0:
                doc, obj = self.import_step(filepath, doc=doc, doc_name=doc_name)
            else:
                _, obj = self.import_step(filepath, doc=doc)
            
            imported_objects.append(obj)
        
        self.log(f"📦 Imported {len(imported_objects)} STEP files")
        return doc, imported_objects
    
    def copy_step_with_modifications(self, input_path, output_path, 
                                    modification_func=None, **kwargs):
        """
        Import a STEP file, optionally modify it, and export to new location
        
        Args:
            input_path: Path to input STEP file
            output_path: Path for output STEP file
            modification_func: Optional function to modify the object
                              Should accept (object, document) and return modified object
            **kwargs: Additional arguments passed to modification_func
            
        Returns:
            Path to exported file
        """
        # Import
        doc, obj = self.import_step(input_path, doc_name="TempModification")
        
        # Modify if function provided
        if modification_func:
            obj = modification_func(obj, doc, **kwargs)
            self.log("🔧 Applied modifications")
        
        # Export
        result = self.export_step(obj, filepath=output_path)
        
        # Clean up temporary document
        App.closeDocument(doc.Name)
        
        return result


# Convenience functions for direct use
def export_to_step(obj, filepath, ensure_merged=True):
    """Quick export function"""
    handler = StepHandler(verbose=False)
    return handler.export_step(obj, filepath=filepath, ensure_merged=ensure_merged)


def import_from_step(filepath, doc=None):
    """Quick import function"""
    handler = StepHandler(verbose=False)
    return handler.import_step(filepath, doc=doc)


def main():
    """Test the STEP handler"""
    import sys
    
    handler = StepHandler(verbose=True)
    
    # Test with a sample file if provided
    if len(sys.argv) > 1:
        step_file = sys.argv[1]
        try:
            doc, obj = handler.import_step(step_file)
            print(f"✅ Successfully imported: {obj.Label}")
            
            # Test export
            output = handler.export_step(obj, filename="test_export.step")
            print(f"✅ Successfully exported to: {output}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return 1
    else:
        print("STEP Handler ready for use")
        print("Usage: python step_handler.py <step_file>")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())