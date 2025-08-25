"""
Stock 3D Macro - Complete GUI Integration
Builds 3D rudder stock geometry with proper FreeCAD GUI setup
"""
import sys, os

# Add project root so Python finds our modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

import FreeCAD as App
import FreeCADGui as Gui
import stock.stock_3D as stock_3D

def run():
    """Run the complete stock 3D building workflow with GUI"""
    print("🔧 Starting Stock 3D Macro...")
    
    # Activate Part workbench for proper geometry display
    Gui.activateWorkbench("PartWorkbench")
    
    # Create or reuse document
    doc_name = "Stock_3D_Build"
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
        # Build stock geometry using boat-centric module
        stock_obj = stock_3D.build_stock_from_csv(doc)
        
        # Ensure proper GUI update and view
        doc.recompute()
        Gui.SendMsgToActiveView("ViewFit")
        Gui.activeDocument().activeView().viewAxonometric()
        
        print("✅ Stock 3D build complete!")
        print(f"📦 Stock object: {stock_obj.Name}")
        
    except Exception as e:
        print(f"❌ Stock build failed: {e}")
        import traceback
        traceback.print_exc()

# Auto-run when executed as macro
if __name__ == "__main__":
    run()
else:
    # Also run when imported (for macro compatibility)
    run()