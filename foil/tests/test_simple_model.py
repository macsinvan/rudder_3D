import pytest
from rudderlib_foil.simple_model import create_test_box

def test_create_test_box_volume():
    L, W, H = 10.0, 5.0, 2.0
    box = create_test_box(L, W, H)
    assert pytest.approx(box.Volume, rel=1e-6) == L * W * H

def test_create_test_box_bounds():
    L, W, H = 3.0, 4.0, 5.0
    box = create_test_box(L, W, H)
    bb = box.BoundBox
    assert bb.XLength == pytest.approx(L)
    assert bb.YLength == pytest.approx(W)
    assert bb.ZLength == pytest.approx(H)
