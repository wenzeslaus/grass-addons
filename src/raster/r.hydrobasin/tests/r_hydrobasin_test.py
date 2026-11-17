"""Tests of r.hydrobasin.

SPDX-FileCopyrightText: 2026 Vaclav Petras
SPDX-License-Identifier: GPL-2.0-or-later
"""

from io import StringIO

import numpy as np
import pytest

import grass.script.array as garray
from grass.tools import Tools

MIRRORED_DEGREE = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="degree format directions are converted incorrectly",
)
FORMATS = [
    ("45degree", "45degree"),
    ("auto", "45degree"),
    pytest.param("degree", "degree", marks=MIRRORED_DEGREE),
    pytest.param("auto", "degree", marks=MIRRORED_DEGREE),
]
N = np.nan


def read_with_nulls(session, name):
    """Read a raster as an array with NaN for nulls"""
    return garray.array(name, null="nan", dtype=np.float64, env=session.env)


@pytest.mark.parametrize("flags", ["", "m"])
@pytest.mark.parametrize(
    ("direction_format", "suffix"),
    [*FORMATS, ("power2", "power2"), ("auto", "power2")],
)
def test_converging(session, direction_format, suffix, flags):
    """Watersheds of all eight directions are the same in each format"""
    tools = Tools(session=session)
    watersheds = tools.r_hydrobasin(
        direction=f"converging_{suffix}",
        format=direction_format,
        outlets="converging_outlets",
        flags=flags,
        output=np.array,
    )
    np.testing.assert_array_equal(watersheds, [[1, 1, 1, 2, 2, 2, 2]] * 5)


@pytest.mark.parametrize(("direction_format", "suffix"), FORMATS)
def test_east(session, direction_format, suffix):
    """Each row is a watershed when all cells point East

    Negative edge values as produced by r.watershed are accepted.
    """
    tools = Tools(session=session)
    watersheds = tools.r_hydrobasin(
        direction=f"east_{suffix}",
        format=direction_format,
        outlets="east_outlets",
        output=np.array,
    )
    np.testing.assert_array_equal(watersheds, [[row] * 7 for row in range(1, 6)])


@pytest.mark.parametrize(
    ("column", "upstream_id", "downstream_id"), [("cat", 1, 2), ("id", 10, 20)]
)
def test_nested_outlets(session, column, upstream_id, downstream_id):
    """An outlet upstream of another outlet splits its watershed"""
    tools = Tools(session=session)
    output = f"watersheds_nested_{column}"
    tools.r_hydrobasin(
        direction="east_45degree",
        format="45degree",
        outlets="nested_outlets",
        column=column,
        output=output,
    )
    watersheds = read_with_nulls(session, output)
    expected = np.full((5, 7), N)
    expected[2] = [upstream_id] * 4 + [downstream_id] * 3
    np.testing.assert_array_equal(watersheds, expected)


def test_outlets_outside_region(session):
    """Outlets outside the region are skipped with a warning

    The outlets of converging_outlets are used with the first one moved to
    the west edge, which is inside the region, and followed by outlets
    outside the region (categories 3 to 7).
    """
    tools = Tools(session=session, consistent_return_value=True)
    points = [
        "0|2.5",  # on the west edge
        "6.5|2.5",
        "3.5|5.5",  # just north
        "-0.5|2.5",  # just west
        "7|2.5",  # on the east edge
        "3.5|0",  # on the south edge
        "100.5|100.5",  # far outside
    ]
    tools.v_in_ascii(input=StringIO("\n".join(points)), output="outside_outlets")
    result = tools.r_hydrobasin(
        direction="converging_45degree",
        format="45degree",
        outlets="outside_outlets",
        output=np.array,
    )
    np.testing.assert_array_equal(result.arrays.output, [[1, 1, 1, 2, 2, 2, 2]] * 5)
    assert "Skip outlet (cat 1)" not in result.stderr
    for cat in range(3, 8):
        assert f"Skip outlet (cat {cat}) at" in result.stderr
