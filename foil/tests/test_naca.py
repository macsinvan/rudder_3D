import pytest
from rudderlib_foil.naca import naca4_thickness, naca4_coordinates

def test_naca_thickness_ends():
    chord, t = 10.0, 12.0
    # Leading and trailing edges should be zero thickness
    assert naca4_thickness(0.0, chord, t) == pytest.approx(0.0)
    assert naca4_thickness(chord, chord, t) == pytest.approx(0.0)

def test_naca_max_thickness_mid():
    chord, t = 10.0, 12.0
    # Use the analytical formula for mid-chord thickness
    expected = 5 * (t/100.0) * chord * (
        0.2969 * (0.5)**0.5
        - 0.1260 * 0.5
        - 0.3516 * 0.5**2
        + 0.2843 * 0.5**3
        - 0.1015 * 0.5**4
    )
    actual = naca4_thickness(chord/2, chord, t)
    assert actual == pytest.approx(expected, rel=1e-6)

def test_naca_coordinates_count_and_shape():
    num_pts = 10
    chord = 5.0
    pts = naca4_coordinates(chord, 10.0, num_pts=num_pts)
    # Should yield (num_pts+1)*2 points
    assert len(pts) == (num_pts + 1) * 2
    # Endpoints zero
    assert pts[0][1] == pytest.approx(0.0)
    assert pts[-1][1] == pytest.approx(0.0)
    # A mid-upper point should be positive, mid-lower negative
    upper_mid_y = pts[num_pts//2][1]
    lower_mid_y = pts[-(num_pts//2 + 1)][1]
    assert upper_mid_y > 0
    assert lower_mid_y < 0