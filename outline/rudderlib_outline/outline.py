"""
Load and scale a 2D profile from CSV.
"""
import csv
from typing import List, Tuple

def read_outline_csv(path: str) -> List[Tuple[float, float]]:
    """
    Read X,Y point pairs from a CSV file.
    """
    pts: List[Tuple[float, float]] = []
    with open(path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            x, y = float(row[0]), float(row[1])
            pts.append((x, y))
    return pts

def scale_outline(pts: List[Tuple[float, float]], factor: float) -> List[Tuple[float, float]]:
    """
    Uniformly scale each (x,y) by factor.
    """
    return [(x * factor, y * factor) for x, y in pts]
