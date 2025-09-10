"""
STEP File Save/Load Helper Module
Reusable functions for importing and exporting STEP files in FreeCAD macros

This file goes in: ~/Rudder_Code/helpers/step_save_load.py
Usage: from helpers.step_save_load import save_step, load_step, StepHandler
"""
import sys
import os
from pathlib import Path
import time

# Add project root for imports
project_root = Path.home() / "Rudder_Code"
if project_root.exists():
    sys.path.insert(0, str(project_root))

class StepFileError(Exception):
    """Custom exception for STEP file operations"""
    pass

class StepHandler:
    """Class-based approach for managing STEP operations with state"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.last_operation = {}
    
    def log(self, message):
        if self.verbose:
            print(message)
    
    def save(self, objects, filepath):
        """Save objects to STEP file"""
        return save_step(objects, filepath, self.verbose)
    
    def load(self, filepath, doc_name=None):
        """Load STEP file into document"""
        return load_step(filepath, doc_name, self.verbose)

def save_step(objects, filepath, verbose=True):
    """
    Export FreeCAD objects to STEP format
    
    Args:
        objects: Single object or list of FreeCAD objects to export
        filepath: Full path to output file (with or without .step extension)
        verbose: Print status messages
    
    Returns:
        str: Full path to saved file
    
    Raises:
        StepFileError: If export fails
    """
    try:
        import FreeCAD as App
        import Part
        
        # Ensure we have a list
        if not isinstance(objects, list):
            objects = [objects]
        
        # Validate objects
        valid_objects = []
        for obj in objects:
            if hasattr(obj, 'Shape') and obj.Shape.isValid():
                valid_objects.append(obj)
            elif verbose:
                print(f"⚠️  Skipping invalid object: {getattr(obj, 'Name', str(obj))}")
        
        if not valid_objects:
            raise StepFileError("No valid objects to export")
        
        # Setup file path
        filepath = Path(filepath)
        
        # Ensure .step extension
        if not filepath.suffix.lower() in ['.step', '.stp']:
            filepath = filepath.with_suffix('.step')
        
        # Create directory if it doesn't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to STEP
        start_time = time.time()
        Part.export(valid_objects, str(filepath))
        export_time = time.time() - start_time
        
        # Verify file was created
        if not filepath.exists():
            raise StepFileError(f"Export appeared to succeed but file not found: {filepath}")
        
        file_size = filepath.stat().st_size
        
        if verbose:
            print(f"✅ STEP export successful:")
            print(f"   📁 File: {filepath}")
            print(f"   📊 Objects: {len(valid_objects)}")
            print(f"   📏 Size: {file_size:,} bytes")
            print(f"   ⏱️  Time: {export_time:.2f}s")
        
        return str(filepath)
        
    except ImportError:
        raise StepFileError("FreeCAD not available - cannot export STEP files")
    except Exception as e:
        raise StepFileError(f"STEP export failed: {e}")

def load_step(filepath, doc_name=None, verbose=True):
    """
    Import STEP file into FreeCAD document
    
    Args:
        filepath: Full path to STEP file
        doc_name: FreeCAD document name (created if doesn't exist)
        verbose: Print status messages
    
    Returns:
        tuple: (document, imported_objects_list)
    
    Raises:
        StepFileError: If import fails
    """
    try:
        import FreeCAD as App
        import Import
        
        # Setup file path
        filepath = Path(filepath)
        
        # Verify file exists
        if not filepath.exists():
            raise StepFileError(f"STEP file not found: {filepath}")
        
        # Create or get document
        if doc_name is None:
            doc_name = f"Import_{filepath.stem}"
        
        if doc_name in App.listDocuments():
            doc = App.getDocument(doc_name)
            if verbose:
                print(f"📄 Using existing document: {doc_name}")
        else:
            doc = App.newDocument(doc_name)
            if verbose:
                print(f"📄 Created new document: {doc_name}")
        
        # Count objects before import
        objects_before = len(doc.Objects)
        
        # Import STEP file
        start_time = time.time()
        Import.insert(str(filepath), doc_name)
        import_time = time.time() - start_time
        
        # Recompute document
        doc.recompute()
        
        # Identify imported objects
        imported_objects = doc.Objects[objects_before:]
        
        file_size = filepath.stat().st_size
        
        if verbose:
            print(f"✅ STEP import successful:")
            print(f"   📁 File: {filepath}")
            print(f"   📊 Objects imported: {len(imported_objects)}")
            print(f"   📏 File size: {file_size:,} bytes")
            print(f"   ⏱️  Time: {import_time:.2f}s")
            
            if imported_objects:
                print(f"   🏷️  Object names: {[obj.Name for obj in imported_objects]}")
        
        return doc, imported_objects
        
    except ImportError:
        raise StepFileError("FreeCAD not available - cannot import STEP files")
    except Exception as e:
        raise StepFileError(f"STEP import failed: {e}")

def batch_export_steps(object_dict, output_dir=None, verbose=True):
    """
    Export multiple objects to separate STEP files
    
    Args:
        object_dict: Dict mapping filenames to FreeCAD objects
        output_dir: Output directory
        verbose: Print status messages
    
    Returns:
        dict: Mapping filenames to full file paths
    """
    results = {}
    
    for filename, obj in object_dict.items():
        try:
            filepath = save_step(obj, filename, output_dir, verbose)
            results[filename] = filepath
        except StepFileError as e:
            if verbose:
                print(f"❌ Failed to export {filename}: {e}")
            results[filename] = None
    
    return results

def validate_step_file(filepath, verbose=True):
    """
    Validate STEP file without importing (basic checks)
    
    Args:
        filepath: Path to STEP file
        verbose: Print validation results
    
    Returns:
        dict: Validation results
    """
    filepath = Path(filepath)
    
    validation = {
        'exists': filepath.exists(),
        'size': 0,
        'has_step_header': False,
        'readable': False,
        'valid': False
    }
    
    if not validation['exists']:
        if verbose:
            print(f"❌ File does not exist: {filepath}")
        return validation
    
    try:
        validation['size'] = filepath.stat().st_size
        
        # Check basic STEP file structure
        with open(filepath, 'r', encoding='utf-8') as f:
            header = f.read(200)
            validation['has_step_header'] = header.startswith('ISO-10303')
            validation['readable'] = True
        
        validation['valid'] = validation['has_step_header'] and validation['size'] > 100
        
        if verbose:
            status = "✅ Valid" if validation['valid'] else "❌ Invalid"
            print(f"{status} STEP file: {filepath}")
            print(f"   📏 Size: {validation['size']:,} bytes")
            print(f"   📋 Has STEP header: {validation['has_step_header']}")
        
    except Exception as e:
        if verbose:
            print(f"❌ Error validating {filepath}: {e}")
    
    return validation

# Convenience functions for common patterns
def quick_save(obj, name, stage_prefix="stage"):
    """Quick save with automatic naming"""
    filename = f"{stage_prefix}_{name}_{int(time.time())}.step"
    return save_step(obj, filename)

def quick_load(filename, clean_doc=True):
    """Quick load with optional document cleanup"""
    doc, objects = load_step(filename)
    
    if clean_doc and len(objects) == 1:
        # If only one object imported, rename document to match
        doc.Label = objects[0].Name
    
    return doc, objects

# Example usage patterns
if __name__ == "__main__":
    print("🔧 STEP Save/Load Helper Module")
    print("Import this module in your macros:")
    print("from helpers.step_save_load import save_step, load_step, StepHandler")
    print("")
    print("Usage examples:")
    print("1. save_step(my_object, 'part1.step')")
    print("2. doc, objects = load_step('part1.step')")
    print("3. handler = StepHandler(); handler.save(obj, 'part.step')")