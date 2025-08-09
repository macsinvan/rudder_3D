# stock/geom.py
from typing import List, Dict

_EPS = 1e-9

def append_post_segment_from_row(segments: List[Dict], row: Dict) -> None:
    """
    Append a post segment (cylinder or taper) derived from a CSV row.
    Logic matches the original in stock2d.py (no behavior change).
    """
    shape_type = (row.get('type', '') or '').lower()

    if shape_type == 'cylinder':
        z0 = -float(row['start'])
        z1 = -float(row['end'])
        base_z = z0 if z0 < z1 else z1
        height = abs(z1 - z0)
        d = float(row['diameter_start'])
        r = d / 2.0
        segments.append({
            "kind": "cyl",
            "z_bot": base_z,
            "z_top": base_z + height,
            "r_bot": r,
            "r_top": r,
        })

    elif shape_type == 'taper':
        z0 = -float(row['start'])
        z1 = -float(row['end'])
        d1 = float(row['diameter_start'])  # top
        d2 = float(row['diameter_end'])    # bottom
        z_bot = z0 if z0 < z1 else z1
        z_top = z1 if z1 > z0 else z0
        segments.append({
            "kind": "taper",
            "z_bot": z_bot,
            "z_top": z_top,
            "r_bot": d2 / 2.0,
            "r_top": d1 / 2.0,
        })
    # other types (e.g., tine/plate) do not contribute segments


def radius_at(z_world: float, segments: List[Dict]) -> float:
    """
    Interpolated post radius at world Z (top≈0, down is negative).
    Matches the original computation (no behavior change).
    """
    for seg in segments:
        if seg["z_bot"] - _EPS <= z_world <= seg["z_top"] + _EPS:
            if seg["kind"] == "cyl":
                return seg["r_top"]
            span = seg["z_top"] - seg["z_bot"]
            if abs(span) < 1e-12:
                return seg["r_top"]
            t = (z_world - seg["z_bot"]) / span
            return seg["r_bot"] + t * (seg["r_top"] - seg["r_bot"])
    raise ValueError(f"No post segment covers Z={z_world:.3f} mm")