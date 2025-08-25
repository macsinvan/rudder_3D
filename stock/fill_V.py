"""
V-Groove Filling Module
Fills V-shaped grooves in rudder stock to create smooth cutout tool

This file goes in: ~/Rudder_Code/Stock/fill_V.py
"""
import FreeCAD as App
import Part
from pathlib import Path

def fill_v_grooves(stock_obj, verbose=True):
    """
    Takes stock object with V-grooves and returns new object with grooves filled
    
    Args:
        stock_obj: FreeCAD object containing stock with V-grooves
        verbose: Print progress messages
    
    Returns:
        New FreeCAD object with V-grooves filled
    """
    if verbose:
        print("🔧 Starting V-groove filling...")
    
    try:
        # Create a copy of the stock shape
        filled_shape = stock_obj.Shape.copy()
        
        # Create the filled object in the document
        doc = stock_obj.Document
        filled_obj = doc.addObject("Part::Feature", f"{stock_obj.Name}_filled")
        filled_obj.Shape = filled_shape
        filled_obj.Label = f"{stock_obj.Label} (V-Filled)"
        
        # Find planar faces that might form V-grooves
        planar_faces = []
        for i, face in enumerate(filled_shape.Faces):
            if hasattr(face.Surface, 'TypeId'):
                if face.Surface.TypeId == 'Part::GeomPlane':
                    # V-grooves typically have smaller area
                    if face.Area < 1000:  # Adjust threshold as needed
                        planar_faces.append(face)
        
        if verbose:
            print(f"   Found {len(planar_faces)} potential V-groove faces")
        
        # Defeature the V-groove faces
        if planar_faces:
            defeatured_shape = filled_shape.defeaturing(planar_faces)
            if defeatured_shape and defeatured_shape.isValid():
                filled_obj.Shape = defeatured_shape
                if verbose:
                    print(f"✅ Defeatured {len(planar_faces)//2} V-grooves (approx)")
            else:
                if verbose:
                    print("⚠️  Defeaturing produced invalid shape")
        
        # Recompute the document
        doc.recompute()
        
        if verbose:
            print(f"📦 Created filled object: {filled_obj.Name}")
        
        return filled_obj
        
    except Exception as e:
        if verbose:
            print(f"❌ V-groove filling failed: {e}")
        raise


if __name__ == "__main__":
    # Module can be run directly for debugging if needed
    print("fill_V module - use fill_v_grooves() to fill V-grooves in stock objects")