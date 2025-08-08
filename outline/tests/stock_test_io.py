# outline/tests/stock/test_io.py
import textwrap
from outline.stock.io import parse_stock_csv, summarize

def test_parse_stock_csv(tmp_path):
    csv_text = textwrap.dedent("""\
        meta,boat_name,MackenSea
        meta,version,1.1.0

        post,type,start,end,diameter_start,label
        post,cylinder,0,20,44,Rudder Sleeve

        post,type,start,end,diameter_start,diameter_end,label
        post,taper,20,604,44,20,Rudder Taper

        tine,wedge,start,width,length,plate_thickness,angle,label
        tine,wedge,119,40,90,5,90,Support 1
    """)
    p = tmp_path / "sample.csv"
    p.write_text(csv_text)

    parsed = parse_stock_csv(str(p))

    # meta
    assert parsed["meta"] == {"boat_name": "MackenSea", "version": "1.1.0"}

    # post components
    post = parsed["sections"]["post"]
    assert len(post) == 2
    cyl = post[0]
    taper = post[1]

    assert cyl["shape"] == "cylinder"
    assert cyl["start"] == 0.0 and cyl["end"] == 20.0
    assert cyl["diameter_start"] == 44.0
    assert cyl["diameter_end"] is None
    assert cyl["label"] == "Rudder Sleeve"

    assert taper["shape"] == "taper"
    assert taper["start"] == 20.0 and taper["end"] == 604.0
    assert taper["diameter_start"] == 44.0
    assert taper["diameter_end"] == 20.0
    assert taper["label"] == "Rudder Taper"

    # tines
    tines = parsed["sections"]["tine"]
    assert len(tines) == 1
    t = tines[0]
    assert t["shape"] == "wedge"
    assert t["start"] == 119.0
    assert t["width"] == 40.0
    assert t["length"] == 90.0
    assert t["plate_thickness"] == 5.0
    assert t["angle"] == 90.0
    assert t["label"] == "Support 1"

    # summary string sanity
    s = summarize(parsed)
    assert "MackenSea" in s and "v1.1.0" in s
    assert "Cylinder 'Rudder Sleeve'" in s
    assert "Taper 'Rudder Taper'" in s
    assert "Tine 'Support 1'" in s