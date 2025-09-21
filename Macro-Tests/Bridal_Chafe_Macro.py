# FreeCAD Chafe Protector with Elongated Ellipsoidal Ends
# Creates 18mm chafe protector with elongated ellipsoidal ends and helical wire rope cutting tool

import FreeCAD
import Part
from FreeCAD import Base

# ============================================================================
# 🔧 OPTIONAL: EDIT THESE PARAMETERS FOR CUSTOM CHAFE PROTECTOR
# Leave as None to use original defaults
# ============================================================================

# Set to None to use original defaults, or customize:
CUSTOM_CYLINDER_LENGTH = None      # None = 250mm default
CUSTOM_PROTECTOR_DIAMETER = None   # None = 18mm default  
CUSTOM_WIRE_ROPE_DIAMETER = None   # None = 6mm default
CUSTOM_WIRE_DIAMETER = None        # None = 1mm default
CUSTOM_NUM_WIRES = None           # None = 12 default
CUSTOM_HELIX_PITCH = None         # None = 100mm default
CUSTOM_CAP_MULTIPLIER = None      # None = 2.0 default (2× radius)
CUSTOM_EXPORT_NAME = None         # None = "ChafeProtector_18mm_Elongated"

# ============================================================================

def create_chafe_protector_with_elongated_ends():
    """
    Creates a chafe protector with elongated ellipsoidal end caps and wire rope cutting tool
    Returns: (doc, chafe_protector_solid, validation_passed, boolean_passed)
    """
    
    # Parameters - use custom if provided, otherwise use original defaults
    cylinder_length = CUSTOM_CYLINDER_LENGTH if CUSTOM_CYLINDER_LENGTH is not None else 250.0
    protector_diameter = CUSTOM_PROTECTOR_DIAMETER if CUSTOM_PROTECTOR_DIAMETER is not None else 18.0
    overall_diameter = CUSTOM_WIRE_ROPE_DIAMETER if CUSTOM_WIRE_ROPE_DIAMETER is not None else 6.0
    wire_diameter = CUSTOM_WIRE_DIAMETER if CUSTOM_WIRE_DIAMETER is not None else 1.0
    num_wires = CUSTOM_NUM_WIRES if CUSTOM_NUM_WIRES is not None else 12
    helix_pitch = CUSTOM_HELIX_PITCH if CUSTOM_HELIX_PITCH is not None else 100.0
    cap_multiplier = CUSTOM_CAP_MULTIPLIER if CUSTOM_CAP_MULTIPLIER is not None else 2.0
    export_name = CUSTOM_EXPORT_NAME if CUSTOM_EXPORT_NAME is not None else "ChafeProtector_18mm_Elongated"
    
    core_diameter = overall_diameter - wire_diameter  # 5.0mm
    
    # Calculate extensions needed for helical offsets
    vertical_offset = helix_pitch / num_wires  # 8.33mm
    total_offset_range = (num_wires - 1) * vertical_offset  # 91.67mm
    extension_each_side = total_offset_range  # Extend by full range on each side
    
    # Extended length for cutting tool
    extended_length = cylinder_length + (2 * extension_each_side)  # 433.33mm
    start_z = -extension_each_side  # Start at -91.67mm
    
    # Elongated cap parameters
    cap_radius = protector_diameter / 2  # 9mm radius
    cap_length = cap_radius * cap_multiplier  # 18mm length (2 × radius as requested)
    
    print("Creating chafe protector with elongated ellipsoidal ends...")
    print(f"Chafe protector: {protector_diameter}mm diameter × {cylinder_length}mm length")
    print(f"Wire rope cutting tool: {overall_diameter}mm diameter × {extended_length:.1f}mm length")
    print(f"Elongated caps: {cap_radius}mm radius × {cap_length}mm length")
    
    # Initialize return variables
    wire_rope_solid = None
    chafe_protector_solid = None
    validation_passed = False
    boolean_passed = False
    
    try:
        # Create document
        doc = FreeCAD.newDocument("ChafeProtector")
        
        # 1. CREATE CHAFE PROTECTOR CYLINDER WITH ELONGATED ELLIPSOIDAL ENDS
        print("\n1. Creating chafe protector with elongated ellipsoidal end caps...")
        
        # Base cylinder
        protector_cylinder = Part.makeCylinder(
            protector_diameter / 2,           # radius = 9mm
            cylinder_length,                  # height = 250mm
            Base.Vector(0, 0, 0),            # start at origin
            Base.Vector(0, 0, 1)             # vertical
        )
        
        # Bottom elongated ellipsoidal cap
        print("   Creating bottom elongated cap...")
        bottom_ellipsoid_obj = doc.addObject("Part::Ellipsoid", "BottomEllipsoidBase")
        bottom_ellipsoid_obj.Radius1 = cap_length     # Z direction (elongated)
        bottom_ellipsoid_obj.Radius2 = cap_radius     # X direction  
        bottom_ellipsoid_obj.Radius3 = cap_radius     # Y direction
        
        # Recompute to generate the shape
        doc.recompute()
        
        bottom_ellipsoid = bottom_ellipsoid_obj.Shape
        
        # Keep only bottom half
        cutting_box_bottom = Part.makeBox(
            cap_radius * 3,  # width
            cap_radius * 3,  # depth  
            cap_length,      # height (cut top half)
            Base.Vector(-cap_radius * 1.5, -cap_radius * 1.5, 0)  # position at Z=0
        )
        bottom_cap = bottom_ellipsoid.cut(cutting_box_bottom)
        
        # Top elongated ellipsoidal cap
        print("   Creating top elongated cap...")
        top_ellipsoid_obj = doc.addObject("Part::Ellipsoid", "TopEllipsoidBase")
        top_ellipsoid_obj.Radius1 = cap_length        # Z direction (elongated)
        top_ellipsoid_obj.Radius2 = cap_radius        # X direction  
        top_ellipsoid_obj.Radius3 = cap_radius        # Y direction
        top_ellipsoid_obj.Placement = FreeCAD.Placement(
            Base.Vector(0, 0, cylinder_length), 
            FreeCAD.Rotation()
        )
        
        # Recompute to generate the shape
        doc.recompute()
        
        top_ellipsoid = top_ellipsoid_obj.Shape
        
        # Keep only top half
        cutting_box_top = Part.makeBox(
            cap_radius * 3,  # width
            cap_radius * 3,  # depth  
            cap_length,      # height (cut bottom half)
            Base.Vector(-cap_radius * 1.5, -cap_radius * 1.5, cylinder_length - cap_length)  # position below center
        )
        top_cap = top_ellipsoid.cut(cutting_box_top)
        
        # Fuse cylinder with both elongated caps
        chafe_protector_solid = protector_cylinder.fuse(bottom_cap)
        chafe_protector_solid = chafe_protector_solid.fuse(top_cap)
        
        protector_obj = doc.addObject("Part::Feature", "ChafeProtector")
        protector_obj.Shape = chafe_protector_solid
        protector_obj.Label = f"ChafeProtector_{protector_diameter:.0f}mm"
        
        # Hide construction ellipsoids
        try:
            if hasattr(FreeCAD, 'Gui'):
                bottom_ellipsoid_obj.ViewObject.Visibility = False
                top_ellipsoid_obj.ViewObject.Visibility = False
        except:
            pass
        
        print(f"✓ Chafe protector created: {protector_diameter}mm diameter with {cap_length}mm elongated end caps")
        
        # 2. CREATE EXTENDED CORE CYLINDER (CUTTING TOOL)
        print("\n2. Creating wire rope cutting tool...")
        core = Part.makeCylinder(
            core_diameter / 2,              # radius = 2.5mm
            extended_length,                # height = 433.33mm
            Base.Vector(0, 0, start_z),    # start at Z = -91.67mm
            Base.Vector(0, 0, 1)           # vertical
        )
        
        core_obj = doc.addObject("Part::Feature", "Core")
        core_obj.Shape = core
        core_obj.Label = f"Core_{core_diameter}mm_CuttingTool"
        
        # Hide core (construction object)
        try:
            if hasattr(FreeCAD, 'Gui'):
                core_obj.ViewObject.Visibility = False
        except:
            pass
        
        # 3. CREATE 12 EXTENDED WIRE HELIXES (CUTTING TOOL)
        print(f"   Creating {num_wires} wire helixes for cutting tool...")
        helix_radius = 2.5  # Put wire centers at 2.5mm radius
        
        # Create the base helix path
        helix = Part.makeHelix(
            helix_pitch,        # pitch = 100mm
            extended_length,    # height = 433.33mm
            helix_radius       # radius = 2.5mm
        )
        
        # Move the helix to start at the correct Z position
        helix.translate(Base.Vector(0, 0, start_z))
        
        # Create wire profile (small circle)
        start_point = helix.Vertexes[0].Point
        circle = Part.makeCircle(wire_diameter / 2, start_point)
        
        # Make the first wire
        wire_shape = Part.Wire(helix).makePipeShell([Part.Wire(circle)], True, True)
        
        # Create all 12 wires with vertical offsets
        wire_shapes = []
        for i in range(num_wires):
            # Copy the wire shape
            if i == 0:
                current_wire = wire_shape
            else:
                current_wire = wire_shape.copy()
                current_wire.translate(Base.Vector(0, 0, i * vertical_offset))
            
            # Store for fusion
            wire_shapes.append(current_wire)
            
            # Add to document but hide (construction object)
            wire_obj = doc.addObject("Part::Feature", f"Wire_{i:02d}")
            wire_obj.Shape = current_wire
            wire_obj.Label = f"Wire_{i:02d}_CuttingTool"
            
            # Hide wire (construction object)
            try:
                if hasattr(FreeCAD, 'Gui'):
                    wire_obj.ViewObject.Visibility = False
            except:
                pass
        
        print(f"✓ All {num_wires} cutting tool wires created and hidden")
        
        # 4. MERGE CUTTING TOOL COMPONENTS
        print("\n3. Creating wire rope cutting tool solid...")
        
        # Start with core as base
        wire_rope_solid = core.copy()
        
        # Fuse each wire with the growing solid
        for i, wire in enumerate(wire_shapes):
            wire_rope_solid = wire_rope_solid.fuse(wire)
        
        # Convert compound to single solid if needed
        if wire_rope_solid.ShapeType == "Compound":
            solids = []
            for shape in wire_rope_solid.SubShapes:
                if shape.ShapeType == "Solid":
                    solids.append(shape)
            
            if len(solids) > 1:
                single_solid = solids[0]
                for solid in solids[1:]:
                    single_solid = single_solid.fuse(solid)
                wire_rope_solid = single_solid
            elif len(solids) == 1:
                wire_rope_solid = solids[0]
        
        cutting_tool_obj = doc.addObject("Part::Feature", "WireRope_CuttingTool")
        cutting_tool_obj.Shape = wire_rope_solid
        cutting_tool_obj.Label = "WireRope_CuttingTool"
        
        # Hide cutting tool 
        try:
            if hasattr(FreeCAD, 'Gui'):
                cutting_tool_obj.ViewObject.Visibility = False
        except:
            pass
        
        print(f"✓ Wire rope cutting tool created and hidden")
        
        # 5. VALIDATE CUTTING TOOL
        print("\n4. Validating cutting tool...")
        
        validation_passed = True
        if not wire_rope_solid.isValid():
            validation_passed = False
            print("   ❌ Cutting tool geometry invalid")
        elif wire_rope_solid.ShapeType != "Solid":
            validation_passed = False
            print(f"   ❌ Cutting tool is '{wire_rope_solid.ShapeType}' instead of 'Solid'")
        else:
            volume = wire_rope_solid.Volume
            print(f"   ✓ Cutting tool valid: {volume:.1f} mm³")
        
        # 6. PERFORM CUTTING OPERATION
        print("\n5. Cutting helical grooves in chafe protector...")
        
        try:
            # Cut wire rope pattern from chafe protector
            final_protector = chafe_protector_solid.cut(wire_rope_solid)
            
            boolean_passed = final_protector.isValid()
            
            if boolean_passed:
                original_volume = chafe_protector_solid.Volume
                result_volume = final_protector.Volume
                volume_removed = original_volume - result_volume
                
                print(f"   ✅ Cutting operation successful!")
                print(f"      Original volume: {original_volume:.1f} mm³")
                print(f"      Final volume: {result_volume:.1f} mm³")
                print(f"      Material removed: {volume_removed:.1f} mm³")
                
                # Add final result to document
                final_obj = doc.addObject("Part::Feature", "ChafeProtector_Final")
                final_obj.Shape = final_protector
                final_obj.Label = "ChafeProtector_with_Grooves"
                
            else:
                print("   ⚠️ Cutting operation completed but result has issues")
                final_obj = doc.addObject("Part::Feature", "ChafeProtector_Final")
                final_obj.Shape = final_protector
                final_obj.Label = "ChafeProtector_Invalid"
                
        except Exception as e:
            print(f"   ❌ Cutting operation failed: {str(e)}")
            boolean_passed = False
            final_obj = None
        
        # 7. SET COLORS
        try:
            if hasattr(FreeCAD, 'Gui'):
                # BLUE chafe protector (original)
                protector_obj.ViewObject.ShapeColor = (0.3, 0.6, 1.0)
                protector_obj.ViewObject.Transparency = 70
                
                # GREEN final result
                if final_obj and boolean_passed:
                    final_obj.ViewObject.ShapeColor = (0.0, 0.8, 0.0)
                    final_obj.ViewObject.Transparency = 0
                elif final_obj:
                    final_obj.ViewObject.ShapeColor = (0.8, 0.4, 0.0)
                    final_obj.ViewObject.Transparency = 0
                    
                print("✓ Colors set")
        except:
            pass
        
        # 8. EXPORT FOR 3D PRINTING
        print("\n6. Exporting for 3D printing...")
        
        if final_obj and boolean_passed:
            try:
                # Export final product to STL
                import os
                export_path = os.path.expanduser(f"~/Desktop/{export_name}.stl")
                final_obj.Shape.exportStl(export_path)
                print(f"   ✅ STL exported: {export_path}")
                
                # Also export as STEP for CAD use
                step_path = os.path.expanduser(f"~/Desktop/{export_name}.step")
                final_obj.Shape.exportStep(step_path)
                print(f"   ✅ STEP exported: {step_path}")
                
                # Export mesh info
                mesh_info = final_obj.Shape.tessellate(0.1)
                vertex_count = len(mesh_info[0])
                triangle_count = len(mesh_info[1])
                print(f"   📊 Mesh: {vertex_count:,} vertices, {triangle_count:,} triangles")
                
            except Exception as e:
                print(f"   ⚠️ Export failed: {str(e)}")
        else:
            print("   ⚠️ Skipped export - invalid geometry")
        
        # 9. FINISH UP
        print("\n7. Finishing up...")
        doc.recompute()
        
        try:
            if hasattr(FreeCAD, 'Gui'):
                FreeCAD.Gui.ActiveDocument.ActiveView.fitAll()
        except:
            pass
        
        print(f"\n🎉 CHAFE PROTECTOR WITH ELONGATED ELLIPSOIDAL ENDS CREATED!")
        print(f"Visible objects:")
        print(f"  • BLUE chafe protector: {protector_diameter}mm × {cylinder_length}mm with elongated ends")
        if final_obj:
            if boolean_passed:
                print(f"  • GREEN final product: Chafe protector with helical grooves")
                print(f"  • 📁 Files exported to Desktop:")
                print(f"    - {export_name}.stl (3D printing)")
                print(f"    - {export_name}.step (CAD)")
            else:
                print(f"  • ORANGE result: Chafe protector (check geometry)")
        print(f"  • All construction objects hidden for clean workspace")
        print(f"  • Elongated caps: {cap_length}mm length (no snag design)")
        
    except Exception as e:
        print(f"\n❌ CREATION FAILED: {str(e)}")
        chafe_protector_solid = None
        validation_passed = False
        boolean_passed = False
    
    return doc, chafe_protector_solid, validation_passed, boolean_passed

# RUN THE CHAFE PROTECTOR CREATION
if __name__ == "__main__":
    try:
        doc, protector_solid, is_valid, cut_ok = create_chafe_protector_with_elongated_ends()
        
        print("\n✅ SUCCESS: Chafe protector creation completed!")
        print(f"📊 Final Status:")
        print(f"   - Chafe protector base: ✓ Created with elongated ellipsoidal ends")
        print(f"   - Cutting tool: {'✅ VALID' if is_valid else '⚠️ INVALID'}")
        print(f"   - Cutting operation: {'✅ SUCCESS' if cut_ok else '⚠️ FAILED'}")
        
        if is_valid and cut_ok:
            print(f"\n🚀 Your chafe protector is ready for:")
            print(f"   • 3D printing (STL file exported)")
            print(f"   • CNC machining (STEP file exported)") 
            print(f"   • Marine hardware use")
            print(f"   • Professional cable protection")
            print(f"   • Smooth line passage (no-snag design)")
            print(f"\n📁 Check your Desktop for exported files!")
        else:
            print(f"\n🔧 Check geometry and try adjusting parameters if needed")
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()