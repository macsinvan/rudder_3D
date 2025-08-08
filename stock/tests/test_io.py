# stock/tests/test_io.py
from pathlib import Path
import stock.io as sio

def test_read_stock_sample_csv():
    # Use the CSV copy that lives alongside this test
    csv_path = Path(__file__).parent / "stock_sample.csv"
    assert csv_path.exists(), f"CSV not found at {csv_path}"

    # Current behavior: section-aware parser returns (rows, meta)
    rows, meta = sio.read_stock_csv_sectioned(str(csv_path))

    # Basic shape
    assert isinstance(rows, list), "rows should be a list of dicts"
    assert isinstance(meta, dict), "meta should be a dict"
    assert len(rows) >= 3, "Expected at least cylinder, taper, and one tine"

    # Meta behavior (as implemented today):
    # First meta line becomes {'boat_name': 'version'}
    # Second meta line becomes {'mackensea': '1.0.0'}
    # (Yes, this is odd, but we're testing current behavior, not redesigning it.)
    assert "boat_name" in meta and meta["boat_name"] == "version"
    assert "mackensea" in meta and meta["mackensea"] == "1.0.0"

    # Helpers to find component kinds without assuming numeric casting
    def has_type(t):
        return any(r.get("type", "").strip().lower() == t for r in rows)

    # Tine rows don’t carry 'type'—they have a 'wedge' header instead.
    def has_tine_wedge():
        return any(("wedge" in r) and (r.get("wedge", "").strip().lower() == "wedge") for r in rows)

    assert has_type("cylinder"), "Expected at least one cylinder row"
    assert has_type("taper"),    "Expected at least one taper row"
    assert has_tine_wedge(),     "Expected at least one tine wedge row"