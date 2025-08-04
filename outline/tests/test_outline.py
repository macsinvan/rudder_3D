import pytest
from rudderlib_outline.outline import read_outline_csv, scale_outline

def test_scale_outline():
    pts = [(0, 0), (1, 1)]
    assert scale_outline(pts, 2.0) == [(0, 0), (2, 2)]

def test_read_outline_csv(tmp_path):
    data = "0,0\n1,1\n"
    p = tmp_path / "pts.csv"
    p.write_text(data)
    pts = read_outline_csv(str(p))
    assert pts == [(0.0, 0.0), (1.0, 1.0)]
