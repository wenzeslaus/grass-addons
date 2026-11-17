"""Tests of r.upflowlength.

SPDX-FileCopyrightText: 2026 Vaclav Petras
SPDX-License-Identifier: GPL-2.0-or-later
"""

import numpy as np
import pytest

import grass.script.array as garray
from grass.tools import ToolError, Tools

FORMATS = [
    ("45degree", "45degree"),
    ("auto", "45degree"),
    ("degree", "degree"),
    ("auto", "degree"),
]


def read_with_nulls(session, name):
    """Read a raster as an array with NaN for nulls

    Tools array output has 0 for nulls.
    """
    return garray.array(name, null="nan", env=session.env)


@pytest.mark.parametrize(
    ("direction_format", "suffix"),
    [
        *FORMATS,
        ("power2", "power2"),
        ("auto", "power2"),
        ("taudem", "taudem"),
    ],
)
def test_converging(session, direction_format, suffix):
    """Upstream flow length of all eight directions is the same in each format"""
    tools = Tools(session=session)
    length = tools.r_upflowlength(
        input=f"converging_{suffix}", format=direction_format, output=np.array
    )
    d = 10 * np.sqrt(2)
    expected = [
        [0, 0, 0, 0, 0, 0, 0],
        [d, d, 0, 10, 0, d, d],
        [2 * d, d, 0, 20, 30, 40, 50],
        [d, d, 0, 10, 0, d, d],
        [0, 0, 0, 0, 0, 0, 0],
    ]
    np.testing.assert_allclose(length, expected, rtol=1e-6)


@pytest.mark.parametrize(("direction_format", "suffix"), FORMATS)
def test_east(session, direction_format, suffix):
    """Upstream flow length increases eastward when all cells point East"""
    tools = Tools(session=session)
    length = tools.r_upflowlength(
        input=f"east_{suffix}", format=direction_format, output=np.array
    )
    np.testing.assert_array_equal(length, [list(range(0, 70, 10))] * 5)


@pytest.mark.parametrize(
    ("direction_format", "direction"),
    [
        ("45degree", "east_null"),
        ("45degree", "east_zero_45degree"),
        ("degree", "east_zero_degree"),
        ("degree", "east_30_degree"),
    ],
)
def test_no_direction(session, direction_format, direction):
    """Cells without a direction are null and break the flow path

    The null output for cells without a direction is the current
    implementation, not documented.
    """
    tools = Tools(session=session, overwrite=True)
    tools.r_upflowlength(input=direction, format=direction_format, output="length")
    length = read_with_nulls(session, "length")
    np.testing.assert_array_equal(length, [[0, 10, 20, np.nan, 0, 10, 20]] * 5)


@pytest.mark.parametrize(
    ("direction_format", "direction", "message"),
    [
        ("degree", "too_low_degree", "degrees cannot be < -360 or > 360"),
        ("auto", "too_low_degree", "degrees cannot be < -360 or > 360"),
        ("degree", "too_high_degree", "degrees cannot be < -360 or > 360"),
        ("45degree", "too_low_45degree", "divided by 45 cannot be < -8 or > 8"),
        ("auto", "too_low_45degree", "divided by 45 cannot be < -8 or > 8"),
        ("45degree", "too_high_45degree", "divided by 45 cannot be < -8 or > 8"),
    ],
)
def test_out_of_range(session, direction_format, direction, message):
    """Directions outside the valid range of the format are rejected"""
    tools = Tools(session=session)
    with pytest.raises(ToolError, match=message):
        tools.r_upflowlength(input=direction, format=direction_format, output=np.array)


@pytest.mark.parametrize("direction_format", ["degree", "45degree"])
def test_all_null(session, direction_format):
    """All-null directions give an all-null output

    The all-null output is the current implementation, not documented.
    """
    tools = Tools(session=session, overwrite=True)
    tools.r_upflowlength(input="all_null", format=direction_format, output="length")
    length = read_with_nulls(session, "length")
    assert np.isnan(length).all()
