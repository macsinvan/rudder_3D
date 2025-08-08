# outline/stock/io.py
import csv
from typing import List, Dict, Any
# stock/io.py
import csv

def read_stock_csv_sectioned(path: str):
    """
    Section-aware reader used by stock2d/build code.
    Returns (rows, meta) where:
      - rows: list of dicts for each data line, respecting per-section headers
      - meta: dict of meta fields from 'meta,...' lines
    Behavior matches the inline parser we had in stock2d.py.
    """
    rows = []
    meta = {}
    current_header = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, skipinitialspace=True)
        for row in reader:
            # skip blank/comment
            if not row or all(not c.strip() for c in row) or row[0].strip().startswith("#"):
                continue

            # meta lines
            if row[0].strip().lower() == "meta":
                if len(row) >= 3:
                    meta[row[1].strip().lower()] = row[2].strip()
                continue

            # header lines (work for post/tine sections)
            lowered = [c.strip().lower() for c in row]
            if "start" in lowered:
                current_header = lowered
                continue

            if not current_header:
                # no header context yet; skip like before
                continue

            # map row -> dict using the current header
            row_dict = {k: v.strip() for k, v in zip(current_header, row)}

            # Keep prior behavior: infer 'wedge' type from header name if no explicit 'type'
            shape_type = row_dict.get("type", "").strip().lower()
            if not shape_type and "wedge" in current_header:
                row_dict["type"] = "wedge"

            rows.append(row_dict)

    return rows, meta
def read_stock_csv(path: str) -> List[Dict[str, Any]]:
    """
    Read rudder-stock spec CSV into a list of dicts.
    Expects header: Component,Style,Start,End,StartDiameter,EndDiameter
    """
    specs: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            comp = row.get("Component", "").strip()
            if not comp or comp.startswith("#"):
                continue
            specs.append({
                "Component": comp,
                "Style":     row.get("Style", "").strip(),
                "Start":     float(row.get("Start", 0.0)),
                "End":       float(row.get("End", 0.0)),
                "StartDiameter": float(row.get("StartDiameter", 0.0)),
                "EndDiameter":   float(row.get("EndDiameter", 0.0)),
            })
    return specs