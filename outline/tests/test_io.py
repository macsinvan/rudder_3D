# File: outline/tests/test_io.py
import pytest
from outline.csv_io import read_transform_csv


def test_read_transform_csv_valid(tmp_path):
    # Skip comments, read header, and transform y to -y, skip bad rows
    csv_content = (
        "# comment\n"
        "X,Y\n"
        "0,0\n"
        "1,2\n"
        "-3,4\n"
        "bad,row\n"
        "5,6\n"
    )
    p = tmp_path / "test.csv"
    p.write_text(csv_content)
    pts = read_transform_csv(str(p))
    assert pts == [(0.0, 0.0), (1.0, -2.0), (-3.0, -4.0), (5.0, -6.0)]


def test_read_transform_csv_empty(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("")
    pts = read_transform_csv(str(p))
    assert pts == []