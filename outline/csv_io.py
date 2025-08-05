# File: outline/io.py
"""
CSV import and 2D coordinate transformation for rudder outline.
"""
import csv
from typing import List, Tuple


def read_transform_csv(path: str) -> List[Tuple[float, float]]:
    """
    Read X,Y from CSV, skip comments and header, transform to (x,z)
    where x=CSV_x, z=-CSV_y.

    :param path: CSV file path
    :return: list of (x, z) tuples
    """
    pts: List[Tuple[float, float]] = []
    reading = False
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            if row[0].strip().upper() == 'X' and row[1].strip().upper() == 'Y':
                reading = True
                continue
            if reading:
                try:
                    x_csv = float(row[0])
                    y_csv = float(row[1])
                    pts.append((x_csv, -y_csv))
                except ValueError:
                    # skip invalid rows
                    continue
    return pts
