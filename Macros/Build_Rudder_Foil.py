# Macros/foil_3D_macro.py
"""
Foil 3D Macro - Complete GUI Integration
Builds 3D NACA foil from outline profiles with proper FreeCAD GUI setup
"""
import sys, os

# Add project root so Python finds our modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)
sys.path.insert(0, os.path.join(project, "foil"))

import FreeCAD as App
import FreeCADGui as Gui
import foil.foil_3D as foil_3D

def run():
    """Run the complete foil 3D building workflow with GUI"""
    print("🛥️ Starting Foil 3D Macro...")
    
    # Activate Part workbench for proper geometry display
    Gui.activateWorkbench("PartWorkbench")
    
    # Create or reuse document
    doc_name = "Foil_3D_Build"
    if doc_name in App.listDocuments():
        print(f"📄 Reusing existing document: {doc_name}")
        doc = App.getDocument(doc_name)
        # Clear existing objects for clean rebuild
        for obj in doc.Objects:
            doc.removeObject(obj.Name)
    else:
        print(f"📄 Creating new document: {doc_name}")
        doc = App.newDocument(doc_name)
    
    try:
        # Build foil geometry using boat-centric module
        foil_3D.build_foil_from_step(doc)
        
        # Ensure proper GUI update and view
        doc.recompute()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.activeDocument().activeView().viewAxonometric()
        
        print("✅ Foil 3D build complete!")
        
    except Exception as e:
        print(f"❌ Foil build failed: {e}")
        import traceback
        traceback.print_exc()

# Auto-run when executed as macro
if __name__ == "__main__":
    run()
else:
    # Also run when imported (for macro compatibility)
    run()