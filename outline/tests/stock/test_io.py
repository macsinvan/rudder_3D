import os
import pytest
from outline.stock.io import read_stock_csv

@pytest.fixture
def sample_csv(tmp_path):
    data = """\
Component,Style,Start,End,StartDiameter,EndDiameter
Post,Cylinder,0,300,20,20
"""
    p = tmp_path / "stock.csv"
    p.write_text(data)
    return str(p)

def test_read_stock_csv(sample_csv):
    specs = read_stock_csv(sample_csv)
    assert isinstance(specs, list)
    assert len(specs) == 1
    entry = specs[0]
    assert entry["Component"] == "Post"
    assert entry["Style"] == "Cylinder"
    assert entry["Start"] == pytest.approx(0.0)
    assert entry["End"] == pytest.approx(300.0)
    assert entry["StartDiameter"] == pytest.approx(20.0)
    assert entry["EndDiameter"] == pytest.approx(20.0)