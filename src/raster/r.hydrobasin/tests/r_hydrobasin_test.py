"""Tests of r.hydrobasin.

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
    ("direction_format", "direction"),
    [
        ("45degree", "east_zero_45degree"),
        ("degree", "east_zero_degree"),
        ("degree", "east_30_degree"),
    ],
)
def test_no_direction(session, direction_format, direction):
    """Cells without a direction are null and cut off the cells upstream of them

    The null output for cells without a direction is the current
    implementation, not documented.
    """
    tools = Tools(session=session)
    output = f"watersheds_{direction}"
    tools.r_hydrobasin(
        direction=direction,
        format=direction_format,
        outlets="east_outlets",
        output=output,
    )
    watersheds = read_with_nulls(session, output)
    np.testing.assert_array_equal(
        watersheds, [[N] * 4 + [row] * 3 for row in range(1, 6)]
    )


@pytest.mark.parametrize(
    ("direction_format", "direction", "message"),
    [
        ("degree", "too_low_degree", "degrees cannot be < -360"),
        ("auto", "too_low_degree", "degrees cannot be < -360"),
        ("45degree", "too_low_45degree", "divided by 45 cannot be < -8"),
        ("auto", "too_low_45degree", "divided by 45 cannot be < -8"),
    ],
)
def test_out_of_range(session, direction_format, direction, message):
    """Directions outside the valid range of the format are rejected"""
    tools = Tools(session=session)
    with pytest.raises(ToolError, match=message):
        tools.r_hydrobasin(
            direction=direction,
            format=direction_format,
            outlets="east_outlets",
            output=np.array,
        )


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
