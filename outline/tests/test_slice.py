import pytest
from outline.geometry import slice_chords

def test_slice_chords_rectangle():
    # Rectangle corners (x,z): (0,0)->(4,0)->(4,2)->(0,2)->back to (0,0)
    pts = [(0,0),(4,0),(4,2),(0,2)]
    # Test chords at z=1 should intersect at x=0 and x=4
    chords = slice_chords(pts, [1.0])
    assert len(chords) == 1
    (p1,p2) = chords[0]
    xs = sorted([p1[0], p2[0]])
    assert xs == [0.0, 4.0]
    assert p1[1] == pytest.approx(1.0)
    assert p2[1] == pytest.approx(1.0)

def test_slice_chords_no_intersect():
    # Z-level outside the shape
    pts = [(0,0),(4,0),(4,2),(0,2)]
    chords = slice_chords(pts, [3.0])
    assert chords == []
