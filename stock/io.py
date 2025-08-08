# outline/stock/io.py
import csv
from typing import List, Dict, Any

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