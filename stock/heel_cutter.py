# stock/heel_cutter.py
# Heel cutter utilities for trimming tines/arms flush to a cutting plane

from typing import List, Dict, Tuple, Optional
from FreeCAD import Vector
import Part

__all__ = [
    "add_post_half_box",
    "add_post_half_box_from_segments", 
    "apply_heel_cutter_workflow",
]


def add_post_half_box(doc,
                      z_bottom: float,
                      z_top: float,
                      r_bottom: float,   # kept for signature compatibility (unused)
                      r_top: float,      # kept for signature compatibility (unused)
                      *,
                      side: str = "negX",
                      oversize: float = 1.0,
                      plane_x: float = 0.0,
                      y_clear: Optional[float] = None,
                      x_depth: Optional[float] = None,
                      name: str = "HeelCutterHalfBox") -> Tuple[Part.Shape, object]:
    """
    Create a rectangular cutter with its inner face lying on X = plane_x.

    Args:
        doc: FreeCAD document
        z_bottom, z_top: Z extents (mm), order does not matter
        r_bottom, r_top: Ignored (kept for API compatibility)
        side: "negX" (extend to -X) or "posX" (extend to +X)
        oversize: padding (mm) applied to Z and Y spans
        plane_x: X position of the inner face (default 0.0)
        y_clear: overrides computed Y length if provided
        x_depth: explicit depth away from the plane; otherwise auto
        name: object name

    Returns:
        (Part.Shape, FreeCAD object) tuple
    """
    # Normalize Z extents
    z0 = float(min(z_bottom, z_top))
    z1 = float(max(z_bottom, z_top))
    pad = float(oversize if oversize is not None else 0.0)

    # Calculate dimensions
    z_len = (z1 - z0) + 2.0 * pad
    if z_len <= 0:
        raise ValueError("Computed z_len must be positive.")

    y_len = float(y_clear) if y_clear is not None else (40.0 + 2.0 * pad)
    x_len = float(x_depth) if x_depth is not None else (80.0 + 2.0 * pad)
    if y_len <= 0 or x_len <= 0:
        raise ValueError("Computed cutter x_len/y_len must be positive.")

    # Build box at origin
    box = Part.makeBox(x_len, y_len, z_len)

    # Position so inner face is exactly at X = plane_x
    if side == "negX":
        base_x = float(plane_x) - x_len  # X-max at plane_x
    elif side == "posX":
        base_x = float(plane_x)          # X-min at plane_x
    else:
        raise ValueError("side must be 'negX' or 'posX'")

    base = Vector(base_x, -0.5 * y_len, z0 - pad)

    # Add to document
    cutter_obj = doc.addObject("Part::Feature", name)
    cutter_obj.Shape = box
    cutter_obj.Placement.Base = base

    # Set visual appearance
    try:
        v = cutter_obj.ViewObject
        v.Transparency = 70
        v.LineColor = (0.0, 1.0, 0.0)   # green edges
        v.ShapeColor = (1.0, 1.0, 0.6)  # pale yellow
    except Exception:
        pass

    doc.recompute()
    return box, cutter_obj


def add_post_half_box_from_segments(doc,
                                    post_segments: List[Dict[str, float]],
                                    *,
                                    side: str = "negX",
                                    oversize: float = 1.0,
                                    plane_x: float = 0.0,
                                    name: str = "HeelCutterHalfBox") -> Tuple[Part.Shape, object]:
    """
    Convenience wrapper: derive Z limits from segments and build a plane-anchored box.

    Args:
        doc: FreeCAD document
        post_segments: List of segments with "z_bot", "z_top" keys
        side: "negX" or "posX" 
        oversize: padding amount
        plane_x: cutting plane X position
        name: object name

    Returns:
        (Part.Shape, FreeCAD object) tuple
    """
    if not post_segments:
        raise ValueError("No post segments available to size cutter box.")

    z_bottom = min(float(seg["z_bot"]) for seg in post_segments)
    z_top    = max(float(seg["z_top"]) for seg in post_segments)

    return add_post_half_box(doc,
                             z_bottom, z_top,
                             r_bottom=0.0, r_top=0.0,
                             side=side, oversize=oversize,
                             plane_x=plane_x,
                             name=name)


def apply_heel_cutter_workflow(doc, post_segments, summaries, compound_shapes, post_shape_indices, non_post_shape_indices):
    """
    Create smart heel cutter and apply cuts to non-post shapes only.
    Returns modified compound_shapes with heel cuts applied.

    Args:
        doc: FreeCAD document
        post_segments: List of post segments for sizing
        summaries: List to append summary info to
        compound_shapes: List of shapes to potentially cut
        post_shape_indices: Indices of shapes that are post components
        non_post_shape_indices: Indices of shapes that can be cut

    Returns:
        List of shapes with heel cuts applied
    """
    try:
        # Create the basic cutter
        _, cutter_obj = add_post_half_box_from_segments(
            doc,
            post_segments,
            side="negX",
            oversize=2.0,
            name="HeelCutterHalfBox"
        )
        
        # Separate post shapes from non-post shapes using tracked indices
        post_shapes = [compound_shapes[i] for i in post_shape_indices]
        non_post_shapes = [compound_shapes[i] for i in non_post_shape_indices]
        
        print(f"CUTTING: Found {len(post_shapes)} post shapes, {len(non_post_shapes)} non-post shapes")
        
        modified_shapes = [None] * len(compound_shapes)  # Preserve original order
        
        if post_shapes and non_post_shapes:
            # Create compound of post shapes
            post_compound = Part.makeCompound(post_shapes)
            
            # Create smart cutter by subtracting post from basic cutter
            try:
                smart_cutter = cutter_obj.Shape.cut(post_compound)
                print(f"CUTTING: Smart cutter created successfully")
                
                # Apply smart cutter to non-post shapes only
                cut_count = 0
                for i, shape_idx in enumerate(non_post_shape_indices):
                    try:
                        original_shape = compound_shapes[shape_idx]
                        cut_shape = original_shape.cut(smart_cutter)
                        modified_shapes[shape_idx] = cut_shape
                        cut_count += 1
                    except Exception as e:
                        print(f"CUTTING: Failed to cut shape {shape_idx}: {e}")
                        modified_shapes[shape_idx] = original_shape
                
                # Keep post shapes unmodified in their original positions
                for shape_idx in post_shape_indices:
                    modified_shapes[shape_idx] = compound_shapes[shape_idx]
                
                print(f"CUTTING: Successfully cut {cut_count}/{len(non_post_shapes)} non-post shapes")
                summaries.append(f"HeelCutterHalfBox z[{cutter_obj.Shape.BoundBox.ZMin:.1f},{cutter_obj.Shape.BoundBox.ZMax:.1f}] - Smart cut applied to {cut_count} shapes")
                
            except Exception as e:
                print(f"CUTTING: Smart cutting failed: {e}, using original shapes")
                modified_shapes = compound_shapes
                summaries.append(f"HeelCutterHalfBox z[{cutter_obj.Shape.BoundBox.ZMin:.1f},{cutter_obj.Shape.BoundBox.ZMax:.1f}] - Visual only")
        else:
            # No smart cutting needed
            modified_shapes = compound_shapes
            summaries.append(f"HeelCutterHalfBox z[{cutter_obj.Shape.BoundBox.ZMin:.1f},{cutter_obj.Shape.BoundBox.ZMax:.1f}] - Visual only")
            
        return modified_shapes
        
    except Exception as e:
        print(f"CUTTING: HeelCutterHalfBox skipped: {e}")
        return compound_shapes